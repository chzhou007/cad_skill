import copy
import math
import unittest
import ezdxf

from reconstruct_wave_main_cohorts import forward_hits,qualify,reconstruct
from native_line_path_evidence import LAYERS


def candidates(angle=0,mirror=False):
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    def point(x,y):
        if mirror:x=-x
        return [c*x-s*y,s*x+c*y]
    rows=[]
    for did,offset in [('CONTROL',0),('OTHER',50)]:
        for system,xy,gap in [('supply',(offset,10),.5),('return',(offset+3,30),1.5)]:
            rows.append(dict(equipment_id=did,system=system,main_edge=system+'-MAIN',
                outward=point(0,1),gap_chord_ratio=gap,wave_chord=10,native_source_Z_delta=0,
                wave=dict(centre_to_pipe_end_xy=0,relative_pipe_frame=[[-1,0,0,0],[0,0,0,.5],[1,0,0,0]]),
                target=dict(source_handle=system+'-HANDLE',point=point(*xy))))
    policy=dict(control_equipment='CONTROL',control_main_handles={s:s+'-HANDLE' for s in ('supply','return')})
    return rows,policy


class Tests(unittest.TestCase):
    def test_batch_qualifies_both_services_in_rotated_mirrored_source_frames(self):
        for angle,mirror in [(0,False),(90,False),(180,True),(270,True)]:
            rows,policy=candidates(angle,mirror);before=copy.deepcopy(rows)
            accepted,pending=qualify(rows,policy)
            self.assertEqual(len(accepted),4);self.assertEqual(pending,[]);self.assertEqual(rows,before)

    def test_incomplete_pair_or_different_main_family_never_partially_connects(self):
        for mode in ['single','wrong_main','farther_main','source_Z_outside_control']:
            rows,policy=candidates()
            if mode=='single':rows.pop()
            elif mode=='wrong_main':rows[-1]['main_edge']='different'
            elif mode=='farther_main':rows[-1]['gap_chord_ratio']+=1
            else:rows[-1]['native_source_Z_delta']=100
            accepted,pending=qualify(rows,policy)
            self.assertEqual({r['equipment_id'] for r in accepted},{'CONTROL'});self.assertEqual(len(pending),1)

    def test_duplicate_service_does_not_replace_another_candidate(self):
        rows,policy=candidates();rows.append(copy.deepcopy(rows[-1]))
        with self.assertRaisesRegex(ValueError,'duplicate equipment service'):qualify(rows,policy)

    def test_near_wave_shape_alone_does_not_select_a_remote_main(self):
        rows,policy=candidates();rows[-1]['wave']['relative_pipe_frame'][0][0]=15
        accepted,pending=qualify(rows,policy)
        self.assertEqual(len(accepted),2);self.assertEqual(len(pending),1)

    def test_typed_forward_rays_ignore_other_service_and_reverse_direction(self):
        doc=ezdxf.new();m=doc.modelspace()
        for layer in LAYERS.values():doc.layers.new(layer)
        near=m.add_line((-5,10),(5,10),dxfattribs=dict(layer=LAYERS['supply']))
        m.add_line((-5,5),(5,5),dxfattribs=dict(layer=LAYERS['return']))
        m.add_line((-5,-10),(5,-10),dxfattribs=dict(layer=LAYERS['supply']))
        result=forward_hits(doc,[0,0],[0,1],'supply')
        self.assertEqual([r['source_handle'] for r in result],[near.dxf.handle]);self.assertEqual(result[0]['point'],[0,10])

    def test_batch_rebuild_splits_each_main_and_preserves_components_native_paths_and_equipment(self):
        doc=ezdxf.new();m=doc.modelspace();nodes=[];edges=[];proofs=[];components=[]
        def node(n,x,y,typ,system=None):return dict(node_id=n,x=x,y=y,node_type=typ,system=system,floor=1)
        def edge(e,a,b,points,handle,system):return dict(edge_id=e,start_node_id=a,end_node_id=b,system=system,path=points,
            path_points=copy.deepcopy(points),attribute_paths=[copy.deepcopy(points)],path_length=math.dist(*points),
            source_handles=[handle],equipment_names=[],equipment_counts={})
        for system,y in [('supply',0),('return',200)]:
            line=m.add_line((0,y),(1000,y));eid=system+'M'
            nodes += [node(system+'A',0,y,'tee',system),node(system+'B',1000,y,'tee',system)]
            main=edge(eid,system+'A',system+'B',[[0,y],[1000,y]],line.dxf.handle,system)
            main['physical_length']='unknown';main['equipment_names']=[system+'V'];main['equipment_counts']={'valve':1}
            main['source_expert_riser_connections']=[dict(center=[900,y],circle_handle=system+'C')]
            main['source_drafting_erratum']=dict(source_endpoints=[[5,y],[10,y]],physical_length='unknown')
            edges.append(main);components.append(dict(edge_id=eid,device_name=system+'V',equipment_type='valve',x='600',y=str(y)))
            for i,x in enumerate((250,750)):
                did='D'+str(i);terminal=system+'U'+str(i);bid=system+'B'+str(i)
                if system=='supply':nodes.append(node(did,x,-500,'equipment'))
                nodes.append(node(terminal,x,-100,'virtual_equipment',system))
                branch=m.add_line((x,-500),(x,-100));edges.append(edge(bid,did,terminal,[[x,-500],[x,-100]],branch.dxf.handle,system))
                proofs.append(dict(main_edge=eid,branch_edge=bid,terminal=terminal,equipment_id=did,system=system,
                    wave=dict(wave_handle=system+'W'+str(i)),target=dict(point=[x,y],source_handle=line.dxf.handle),
                    branch_contact=dict(source_line_handle=branch.dxf.handle)))
        graph=dict(metadata={},nodes=nodes,edges=edges);before=copy.deepcopy(graph)
        out,assigned=reconstruct(doc,graph,components,proofs,'S','G',dict(question_id='EXPLICIT'))
        self.assertEqual(graph,before);self.assertEqual(len(out['edges']),len(edges)+4)
        self.assertEqual(len(out['sourceWaveMainCohort']['records']),4)
        self.assertEqual({r['device_name'] for r in assigned},{r['device_name'] for r in components})
        self.assertEqual(len({r['edge_id'] for r in assigned}),2)
        self.assertEqual(sum(len(e.get('source_expert_riser_connections',[])) for e in out['edges']),2)
        self.assertEqual(sum(bool(e.get('source_drafting_erratum')) for e in out['edges']),2)
        for old in [e for e in graph['edges'] if 'B0' in e['edge_id'] or 'B1' in e['edge_id']]:
            new=next(e for e in out['edges'] if e['edge_id']==old['edge_id'])
            self.assertEqual(new['attribute_paths'],old['attribute_paths']);self.assertEqual(new['path_length'],old['path_length'])
            self.assertFalse(new['path_length_complete'])


if __name__=='__main__':unittest.main()
