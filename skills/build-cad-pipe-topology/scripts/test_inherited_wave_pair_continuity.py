import copy,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf
from ezdxf.math import Matrix44
from inherited_wave_pair_continuity import control_evidence,inspect_pairs,reconstruct,compute,implementation_hashes
from native_line_path_evidence import LAYERS
from wave_omission_candidates import block_fingerprint,screen
from confirm_wave_drawing_convention import STATEMENT
from confirm_crossview_paths import sha


def source(control=False,offset=2):
    doc=ezdxf.new();block=doc.blocks.new('wave');block.add_lwpolyline([(-1,-10,-.5),(0,0,.5),(1,10,0)],format='xyb');m=doc.modelspace()
    graph=dict(nodes=[],edges=[],metadata=dict(source_sha256='C' if control else 'S'));pairs=[];devices=[]
    for system,y in [('supply',0),('return',50)]:
        points=[[0,y],[100,y]];waves=[m.add_blockref('wave',(0,y)),m.add_blockref('wave',(100+offset,y))];lines=[m.add_line((-100,y),(0,y),dxfattribs=dict(layer=LAYERS[system])),m.add_line((100,y),(200,y),dxfattribs=dict(layer=LAYERS[system]))]
        for name,x in [('X',-100),('A',0),('B',100),('Y',200)]:graph['nodes'].append(dict(node_id=system+name,node_type='virtual_equipment',subtype='unresolved_source_terminal' if name in ('A','B') else 'unlocated_boundary',floor=2 if control else 3,system=system,x=x,y=y))
        edges=[]
        for i,(start,end,path) in enumerate([(system+'X',system+'A',[[-100,y],[0,y]]),(system+'B',system+'Y',[[100,y],[200,y]])]):
            eid=system+str(i);name=eid+'Valve';edge=dict(edge_id=eid,start_node_id=start,end_node_id=end,edge_type='tee_to_virtual_equipment',system=system,
                start_floor=2 if control else 3,end_floor=2 if control else 3,path=path,path_points=path,attribute_paths=[path],path_length=100.,source_handles=[lines[i].dxf.handle],equipment_counts=dict(ball_valve=1),equipment_names=[name])
            edge['start_port_id' if i==0 else 'end_port_id']=system+'PORT'+str(i)
            if i==0:edge['split_source_edge']=dict(edge_id='OLD-'+eid,source_graph_sha256='OLD',interval_native_units=[0,100])
            edges.append(edge);devices.append(dict(edge_id=eid,device_name=name,equipment_type='ball_valve',source_handle=lines[i].dxf.handle,resistance=''))
        if control:
            merged=copy.deepcopy(edges[0]);merged.update(end_node_id=system+'Y',attribute_paths=[edges[0]['path'],edges[1]['path']],path_length_complete=False,
                source_handles=[e.dxf.handle for e in lines],source_wave_omission=dict(expert_issue='ISSUE',source_insert_handles=[w.dxf.handle for w in waves],endpoints=points,physical_length='unknown'))
            graph['edges'].append(merged)
        else:graph['edges'].extend(edges)
        pairs.append(dict(system=system,nodes=[system+'A',system+'B'],wave_handles=[w.dxf.handle for w in waves],retained_edge=system+'0'))
    if control:
        graph['expertWaveOmissionRepair']=dict(source_sha256='C',issue='ISSUE',expert_note='expert connection',steps=[dict(system=p['system'],source_wave_handles=p['wave_handles']) for p in pairs])
        graph['expertWaveDrawingConvention']=dict(confirmation_sha256='CONFIRM',full_graph_accepted=False,pairs=[])
    return doc,graph,pairs,devices,block_fingerprint(block)


def fixture():
    cd,cg,_,_,fp=source(True);doc,g,pairs,devices,_=source()
    confirmation=dict(statement=STATEMENT,full_graph_accepted=False,wave_pairs=[])
    issue=dict(sourceHashes=dict(main_dxf='C'),issue=dict(label='ISSUE',note='expert connection'))
    controls=control_evidence(cd,cg,confirmation,issue,'C','CONFIRM','wave',fp)
    return doc,g,devices,controls,dict(pairs=pairs,block_name='wave',block_fingerprint=fp),cd,cg,confirmation,issue


class Tests(unittest.TestCase):
    def test_off_centre_pair_inherits_actual_control_without_relaxing_old_screen(self):
        doc,g,devices,controls,p,*_=fixture();before=copy.deepcopy((g,devices))
        old=screen(doc,g,block_name='wave',expected_fingerprint=p['block_fingerprint'],max_gap=200)
        self.assertEqual(old['candidate_pairs'],[])
        proof=inspect_pairs(doc,g,controls,p,'S','G');new,rows=reconstruct(g,devices,proof,'S','G')
        self.assertEqual((g,devices),before);self.assertEqual(len(new['edges']),2);self.assertEqual(len(new['nodes']),4)
        self.assertEqual(len(rows),4);self.assertEqual({r['edge_id'] for r in rows},{'supply0','return0'})
        for edge in new['edges']:
            self.assertEqual(edge['path_length'],200);self.assertEqual(len(edge['attribute_paths']),2);self.assertFalse(edge['path_length_complete'])
            self.assertEqual(edge['source_wave_omission']['physical_length'],'unknown');self.assertFalse(edge['source_wave_omission']['physical_component'])
            self.assertNotIn('split_source_edge',edge);self.assertIn('split_source_edge',edge['source_wave_constituents'][0]['edge_snapshot'])
            self.assertEqual(edge['start_port_id'],edge['system']+'PORT0');self.assertEqual(edge['end_port_id'],edge['system']+'PORT1')
        self.assertFalse(new['sourceInheritedWavePairContinuity']['unpaired_continuations_inferred'])

    def test_rotation_and_mirror_keep_native_relative_offsets_and_service_separation(self):
        for angle,mirror in [(90,1),(180,-1),(270,-1)]:
            with self.subTest(angle=angle,mirror=mirror):
                doc,g,ds,controls,p,*_=fixture();matrix=Matrix44.chain(Matrix44.scale(mirror,1,1),Matrix44.z_rotate(math.radians(angle)))
                for entity in doc.modelspace():entity.transform(matrix)
                for node in g['nodes']:node['x'],node['y']=list(matrix.transform((node['x'],node['y'],0)))[:2]
                for edge in g['edges']:
                    for key in ('path','path_points'):edge[key]=[list(matrix.transform((*q,0)))[:2] for q in edge[key]]
                    edge['attribute_paths']=[[list(matrix.transform((*q,0)))[:2] for q in path] for path in edge['attribute_paths']]
                proofs=inspect_pairs(doc,g,controls,p,'S','G');self.assertEqual(len(proofs),2)
                self.assertEqual({x['system'] for x in proofs},{'supply','return'})

    def test_unproved_offset_Z_extra_wave_or_source_pipe_and_cross_system_are_rejected(self):
        for case in ('offset','Z','extra_wave','pipe','system','floor','nonfacing'):
            with self.subTest(case=case):
                doc,g,_,controls,p,*_=fixture()
                if case=='offset':doc.entitydb[p['pairs'][0]['wave_handles'][1]].dxf.insert=(102.2,0,0)
                elif case=='Z':doc.entitydb[g['edges'][0]['source_handles'][0]].dxf.end=(0,0,1)
                elif case=='extra_wave':doc.modelspace().add_blockref('wave',(102,0))
                elif case=='pipe':doc.modelspace().add_line((25,0),(75,0),dxfattribs=dict(layer=LAYERS['supply']))
                elif case=='system':next(n for n in g['nodes'] if n['node_id']=='supplyB')['system']='return'
                elif case=='floor':next(n for n in g['nodes'] if n['node_id']=='supplyB')['floor']=4
                else:g['edges'][1]['attribute_paths']=[[[100,0],[0,0]]]
                with self.assertRaises(ValueError):inspect_pairs(doc,g,controls,p,'S','G')

    def test_new_edge_fields_and_active_retired_references_are_not_discarded(self):
        for case in ('attribute','reference','component'):
            with self.subTest(case=case):
                doc,g,ds,controls,p,*_=fixture();proofs=inspect_pairs(doc,g,controls,p,'S','G')
                if case=='attribute':g['edges'][1]['diameter']='DN80'
                elif case=='reference':g['external_current_mapping']=dict(edge_id='supply1')
                else:ds[0]['device_name']='wrong'
                with self.assertRaises(ValueError):reconstruct(g,ds,proofs,'S','G')

    def test_real_expert_control_scope_source_and_confirmation_cannot_be_forged(self):
        for case in ('statement','source','issue','scope'):
            with self.subTest(case=case):
                *_,cd,cg,c,i=fixture()
                if case=='statement':c['statement']='inferred'
                elif case=='source':cg['metadata']['source_sha256']='other'
                elif case=='issue':i['issue']['note']='changed'
                else:cg['expertWaveDrawingConvention']['pairs']=[dict(system='supply',wave_handles=['x','y'])]
                with self.assertRaises(ValueError):control_evidence(cd,cg,c,i,'C','CONFIRM','wave',block_fingerprint(cd.blocks['wave']))

    def test_entry_replays_native_parent_before_new_reconstruction(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);paths={k:root/(('assigned_edge_device_instances.csv') if k=='devices' else k+'.json') for k in ('source','graph','devices','control_source','control_graph','control_confirmation','control_issue','control_image')}
            for path in paths.values():path.write_text('{}','utf8')
            policy={k+'_sha256':sha(v) for k,v in paths.items()}
            with patch('calibrated_ownership_scope_composition.verify_ownership_output',side_effect=ValueError('native parent changed')),self.assertRaisesRegex(ValueError,'native parent changed'):compute(paths,policy)
            policy['source_sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'dependency changed source'):compute(paths,policy)
        self.assertIn('inherited_wave_pair_continuity.py',implementation_hashes())


if __name__=='__main__':unittest.main()
