import copy,math,unittest
import ezdxf
from calibrated_equipment_interface_ownership import equipment,native_interface,screen,apply,calibration,projected_candidates

GLYPH=[((0,0),(52.09458,114.14687)),((0,0),(114.14687,52.09458)),((34.72067,131.52078),(131.52078,34.72067)),((51.73687,148.53698),(148.53698,51.73687))]
LAYERS={'return':'空调冷冻水回水','supply':'空调冷冻水供水'}

def fixture(angle=0,mirror=False,spacing=300):
    doc=ezdxf.new();m=doc.modelspace();theta=math.radians(angle)
    def turn(x,y):
        if mirror:x=-x
        return [x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta)]
    block=doc.blocks.new('BODY');block.add_lwpolyline([(-600,1000),(600,1000),(600,1500),(-600,1500)],close=True)
    insert=m.add_blockref('BODY',(0,0),dxfattribs=dict(rotation=angle,xscale=-1 if mirror else 1))
    center=turn(0,1250);nodes=[dict(node_id='EQ',node_type='equipment',floor=1,x=center[0],y=center[1],source_handle=insert.dxf.handle,source_block='BODY',connection_status='ports_unresolved')]
    m.add_text('EQ',dxfattribs=dict(insert=turn(0,1200)));edges=[]
    def add_pair(prefix,offset=0):
        for system,x in [('return',offset-spacing/2),('supply',offset+spacing/2)]:
            p=turn(x,0);q=turn(x,-1000);circle=m.add_circle(p,80,dxfattribs=dict(layer=LAYERS[system]));glyph=[]
            for a,b in GLYPH:glyph.append(m.add_line(turn(a[0]+x,a[1]),turn(b[0]+x,b[1]),dxfattribs=dict(layer='空调立管、水平支管')))
            pipe=m.add_line(p,q,dxfattribs=dict(layer=LAYERS[system]));nid=prefix+system;end='END-'+nid
            nodes.extend([dict(node_id=nid,node_type='virtual_equipment',subtype='out_of_plane_interface',system=system,floor=1,x=p[0],y=p[1],source_handle=circle.dxf.handle,source_handles=[circle.dxf.handle]+[g.dxf.handle for g in glyph],ports=[dict(port_id=nid+'-P',system=system,x=p[0],y=p[1])]),dict(node_id=end,node_type='virtual_equipment',subtype='unresolved_source_terminal',floor=1,system=system,x=q[0],y=q[1])])
            edges.append(dict(edge_id='E-'+nid,system=system,start_node_id=nid,end_node_id=end,start_port_id=nid+'-P',path=[p,q],path_points=[p,q],attribute_paths=[[p,q]],path_length=1000,source_handles=[pipe.dxf.handle],equipment_counts={},equipment_names=[],edge_type='tee_to_virtual_equipment'))
    add_pair('I-');graph=dict(metadata=dict(source_sha256='S'),nodes=nodes,edges=edges,virtual_equipment_ports=[dict(virtual_equipment_id=n['node_id'],port_id=n['node_id']+'-P') for n in nodes if n.get('subtype')=='out_of_plane_interface'])
    model=dict(spacings=[300],maximum_gap_ratio=5.5);return doc,graph,model,add_pair

class CalibratedOwnershipTests(unittest.TestCase):
    def test_native_pairs_rotate_and_mirror_without_crossing_services(self):
        for angle in (0,90,180,270):
            for mirror in (False,True):
                doc,graph,model,_=fixture(angle,mirror);before=copy.deepcopy(graph);evidence=screen(doc,graph,model)
                self.assertEqual(len(evidence['selected']),1);self.assertEqual(graph,before)
                out,records,changes=apply(graph,evidence,model,dict(expected_equipment_bindings=1,control_graph_sha256='C'),'S','G')
                self.assertEqual(len(out['nodes']),3);self.assertEqual(len(records),2);self.assertEqual({e['system'] for e in out['edges']},{'supply','return'})
                self.assertEqual(out['virtual_equipment_ports'],[]);self.assertEqual(out['nodes'][0]['node_id'],'EQ');self.assertFalse(out['sourceLayoutEquipmentOwnership']['physical_ports_verified'])
                for old,new in zip(before['edges'],out['edges']):
                    for key in ('attribute_paths','path_points','path_length','source_handles','equipment_counts','equipment_names'):self.assertEqual(old[key],new[key])
                    self.assertFalse(new['path_length_complete']);self.assertFalse(new['source_layout_equipment_interface']['human_accepted'])
    def test_unlearned_200_spacing_stays_unbound(self):
        doc,graph,model,_=fixture(spacing=200);result=screen(doc,graph,model)
        self.assertEqual(result['selected'],[]);self.assertEqual(len(result['unbound_interfaces']),2)
    def test_near_body_alone_and_mixed_approaches_do_not_bind(self):
        doc,graph,model,_=fixture();body=equipment(doc,graph);pair=[native_interface(doc,next(n for n in graph['nodes'] if n['node_id']==e['start_node_id']),e) for e in graph['edges']]
        pair[1]['pipe']['direction']=[1,0];hits,reason=projected_candidates(pair,body,2000)
        self.assertEqual(hits,[]);self.assertIn('not_parallel',reason)
        pair[1]['pipe']['direction']=pair[0]['pipe']['direction'];pair[0]['point'][0]=650;self.assertEqual(projected_candidates(pair,body,2000)[0],[])
    def test_two_pairs_claiming_one_device_are_not_greedily_assigned(self):
        doc,graph,model,add=fixture();graph['nodes'][:]=graph['nodes'][:1];graph['edges'].clear();add('A-',-250);add('B-',250)
        result=screen(doc,graph,model);self.assertEqual(result['selected'],[]);self.assertTrue(all(r['status']=='multiple_pairs_claim_equipment_pending' for r in result['pairs']))
    def test_competing_native_pipe_contact_or_incomplete_glyph_stays_pending(self):
        for variant in ('contact','glyph'):
            doc,graph,model,_=fixture();node=next(n for n in graph['nodes'] if n.get('subtype')=='out_of_plane_interface');edge=graph['edges'][0]
            if variant=='contact':doc.modelspace().add_line((node['x']-100,node['y']),(node['x']+100,node['y']),dxfattribs=dict(layer=LAYERS[node['system']]))
            else:node['source_handles'].pop()
            with self.assertRaises(ValueError):native_interface(doc,node,edge)
            self.assertEqual(screen(doc,graph,model)['selected'],[])
    def test_wrong_existing_ownership_or_scope_count_is_not_overwritten(self):
        doc,graph,model,_=fixture();evidence=screen(doc,graph,model)
        with self.assertRaisesRegex(ValueError,'scope'):apply(graph,evidence,model,dict(expected_equipment_bindings=2,control_graph_sha256='C'),'S','G')
        graph['edges'][0]['confirmed_equipment_interface']={'old':True}
        with self.assertRaisesRegex(ValueError,'reconciliation'):apply(graph,evidence,model,dict(expected_equipment_bindings=1,control_graph_sha256='C'),'S','G')
    def test_calibration_cannot_contradict_a_user_confirmed_owner(self):
        doc,graph,model,_=fixture();block=doc.blocks.get('BODY');other=doc.modelspace().add_blockref('BODY',(3000,0));doc.modelspace().add_text('OTHER',dxfattribs=dict(insert=(3000,1200)))
        graph['nodes'].append(dict(node_id='OTHER',node_type='equipment',floor=1,x=3000,y=1250,source_handle=other.dxf.handle,source_block='BODY'))
        for edge in graph['edges']:
            original=copy.deepcopy(next(n for n in graph['nodes'] if n['node_id']==edge['start_node_id']));edge['start_node_id']='OTHER'
            edge['confirmed_equipment_interface']=dict(confirmation=dict(confirmed_by='user'),source_sha256='S',interface_side='start',original_interface=original)
        with self.assertRaisesRegex(ValueError,'contradicts'):calibration(doc,graph,dict(control_source_sha256='S',minimum_controls=1,normal_gap_margin_in_spacings=1))

if __name__=='__main__':unittest.main()
