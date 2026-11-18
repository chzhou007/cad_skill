import copy
import unittest
import hashlib
import json
import tempfile
from pathlib import Path
import ezdxf
from repair_confirmed_circle_junctions import apply, pos, segments_for_interval


class ConfirmedCircleTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new();m=self.doc.modelspace()
        main=m.add_line((0,0),(1000,0));branch=m.add_line((400,300),(400,80));circle=m.add_circle((400,0),80)
        mh,bh,ch=main.dxf.handle,branch.dxf.handle,circle.dxf.handle
        self.circle=ch
        self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'A','node_type':'tee','system':'supply','x':0,'y':0,'floor':1},
                    {'node_id':'B','node_type':'tee','system':'supply','x':1000,'y':0,'floor':1},
                    {'node_id':'U','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','x':400,'y':80,'floor':1},
                    {'node_id':'EQ','node_type':'equipment','x':400,'y':300,'floor':1}],
                    'edges':[{'edge_id':'M','start_node_id':'A','end_node_id':'B','system':'supply','start_floor':1,'end_floor':1,'path':[[0,0],[1000,0]],'path_points':[[0,0],[1000,0]],'attribute_paths':[[[0,0],[1000,0]]],'path_length':1000,'source_handles':[mh],'equipment_names':['C1','C2'],'equipment_counts':{'valve':2}},
                             {'edge_id':'BR','start_node_id':'EQ','end_node_id':'U','system':'supply','start_floor':1,'end_floor':1,'path':[[400,300],[400,80]],'path_points':[[400,300],[400,80]],'attribute_paths':[[[400,300],[400,80]]],'path_length':220,'source_handles':[bh],'equipment_names':[],'equipment_counts':{}}],
                    'virtual_equipment_ports':[],'confirmedEquipmentInterfaceRepair':{'input_graph_sha256':'prior'}}
        self.screen={'source_sha256':'s','graph_sha256':'prior','candidates':[{'circle_handle':ch,'main_graph_edges':['M'],'branch_graph_edges':['BR'],'rim_virtual_nodes':['U'],'protected_boundaries':[],'status':'source_shape_graph_connection_not_established','line_system':'supply','main_handle':mh,'branch_handle':bh,'circle_layer':'0','circle_layer_matches_lines':True,'z_consistent_within_tolerance':True,'circle_z':0,'main_z_at_center':0,'branch_z_at_rim':0,'center':[400,0],'branch_rim':[400,80],'radius':80}]}
        self.policy={'source_sha256':'s','input_graph_sha256':'g','screen_sha256':'screen','circle_handles':[ch],
                     'confirmation':{'confirmed_by':'user','question':'接入?','answer':'连接'}}
        self.rows=[{'edge_id':'M','device_name':'C1','equipment_type':'valve','x':'200','y':'0'},
                   {'edge_id':'M','device_name':'C2','equipment_type':'valve','x':'700','y':'0'}]
    def test_confirmed_split_conserves_devices_and_unknown_radius(self):
        g,rows,audit=apply(self.doc,self.graph,self.rows,self.screen,self.policy,'s','g','screen')
        self.assertEqual(len(audit['records']),1);tee='T-USER-'+self.circle
        incident=[e for e in g['edges'] if tee in (e['start_node_id'],e['end_node_id'])]
        self.assertEqual(len(incident),3);self.assertEqual({e['system'] for e in incident},{'supply'})
        self.assertEqual({r['device_name'] for r in rows},{'C1','C2'});self.assertEqual(len({r['edge_id'] for r in rows}),2)
        branch=next(e for e in g['edges'] if e['edge_id']=='BR');self.assertEqual(branch['path_length'],220)
        self.assertEqual(branch['attribute_paths'],[[[400,300],[400,80]]]);self.assertFalse(branch['path_length_complete'])
        self.assertFalse(g['metadata']['hil_ready']);self.assertEqual(self.graph['edges'][1]['end_node_id'],'U')
    def test_stale_unconfirmed_and_wrong_system_fail(self):
        with self.assertRaises(ValueError):apply(self.doc,self.graph,self.rows,self.screen,self.policy,'s','wrong','screen')
        policy=copy.deepcopy(self.policy);policy['confirmation']['confirmed_by']='algorithm'
        with self.assertRaises(ValueError):apply(self.doc,self.graph,self.rows,self.screen,policy,'s','g','screen')
        graph=copy.deepcopy(self.graph);graph['edges'][1]['system']='return'
        with self.assertRaises(ValueError):apply(self.doc,graph,self.rows,self.screen,self.policy,'s','g','screen')
    def test_component_at_cut_rejected(self):
        rows=copy.deepcopy(self.rows);rows[0]['x']='400'
        with self.assertRaises(ValueError):apply(self.doc,self.graph,rows,self.screen,self.policy,'s','g','screen')
    def test_two_mapped_tees_rebuild_one_main_into_three_component_owned_edges(self):
        graph=copy.deepcopy(self.graph);screen=copy.deepcopy(self.screen);policy=copy.deepcopy(self.policy)
        branch=self.doc.modelspace().add_line((700,300),(700,80))
        circle=self.doc.modelspace().add_circle((700,0),80)
        graph['nodes'] += [dict(node_id='U2',node_type='virtual_equipment',subtype='unresolved_source_terminal',system='supply',x=700,y=80,floor=1),dict(node_id='EQ2',node_type='equipment',x=700,y=300,floor=1)]
        second=copy.deepcopy(graph['edges'][1]);second.update(edge_id='BR2',start_node_id='EQ2',end_node_id='U2',path=[[700,300],[700,80]],path_points=[[700,300],[700,80]],attribute_paths=[[[700,300],[700,80]]],source_handles=[branch.dxf.handle])
        graph['edges'].append(second)
        candidate=copy.deepcopy(screen['candidates'][0]);candidate.update(circle_handle=circle.dxf.handle,branch_handle=branch.dxf.handle,branch_graph_edges=['BR2'],rim_virtual_nodes=['U2'],center=[700,0],branch_rim=[700,80])
        screen['candidates'].append(candidate);policy['circle_handles'].append(circle.dxf.handle)
        graph['edges'][0].update(equipment_names=['C1','C2','C3'],equipment_counts={'valve':3})
        rows=[dict(edge_id='M',device_name=name,equipment_type='valve',x=str(x),y='0') for name,x in [('C1',200),('C2',550),('C3',900)]]
        graph['metadata'].update(hil_ready=True,review_status='accepted')
        out,assigned,audit=apply(self.doc,graph,rows,screen,policy,'s','g','screen')
        children=[e for e in out['edges'] if e.get('split_source_edge',{}).get('edge_id')=='M']
        self.assertEqual(len(children),3);self.assertEqual(len(out['edges']),5)
        self.assertEqual([e['path_length'] for e in children],[400,300,300])
        self.assertEqual(len({r['edge_id'] for r in assigned}),3)
        self.assertEqual({r['device_name'] for r in assigned},{'C1','C2','C3'})
        for record in audit['records']:
            self.assertEqual(set(record['main_child_edges']),{e['edge_id'] for e in children})
            self.assertEqual(sum(record['tee'] in (e['start_node_id'],e['end_node_id']) for e in out['edges']),3)
        self.assertFalse(out['metadata']['hil_ready'])
        self.assertEqual(out['metadata']['review_status'],'unreviewed_after_semantic_change')
        self.assertEqual(out['preHilComparison']['status'],'pending')
        self.assertEqual(graph['edges'][0]['path'],[[0,0],[1000,0]])
    def test_diameter_on_split_main_requires_explicit_remapping(self):
        graph=copy.deepcopy(self.graph);graph['edges'][0]['diameter_nominal_mm']=300
        with self.assertRaises(ValueError):apply(self.doc,graph,self.rows,self.screen,self.policy,'s','g','screen')
    def test_user_confirmation_preserves_layer_and_z_conflict(self):
        screen=copy.deepcopy(self.screen);c=screen['candidates'][0]
        c['circle_layer_matches_lines']=False;c['z_consistent_within_tolerance']=False;c['circle_z']=-2
        graph,_,_=apply(self.doc,self.graph,self.rows,screen,self.policy,'s','g','screen')
        evidence=next(e for e in graph['edges'] if e['edge_id']=='BR')['source_user_circle_connection']
        self.assertFalse(evidence['circle_layer_matches_lines']);self.assertFalse(evidence['z_consistent_within_tolerance']);self.assertEqual(evidence['circle_z'],-2)
    def test_split_source_paths_and_reject_ambiguous_projection(self):
        path=[[0,0],[1000,0]]
        self.assertEqual(segments_for_interval(path,[[[0,0],[300,0]],[[700,0],[1000,0]]],200,800),[[[200,0],[300,0]],[[700,0],[800,0]]])
        with self.assertRaises(ValueError):pos([[0,0],[100,0],[0,0]],[50,0])

    def test_current_screen_requires_hash_bound_review_scope(self):
        with tempfile.TemporaryDirectory() as td:
            image=Path(td)/'pair.png';image.write_bytes(b'reviewed-pair')
            manifest=Path(td)/'manifest.json'
            manifest.write_text(json.dumps({'source_sha256':'s','graph_sha256':'g',
                'pairs':[{'connections':[{'circle_handle':self.circle}]}]}),encoding='utf8')
            sh=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            policy=copy.deepcopy(self.policy);policy['screen_basis']='current_graph'
            policy['review_evidence']={'image':str(image),'image_sha256':sh(image),
                'manifest':str(manifest),'manifest_sha256':sh(manifest),'shown_circle_handles':[self.circle]}
            screen=copy.deepcopy(self.screen);screen['graph_sha256']='g'
            result,_,_=apply(self.doc,self.graph,self.rows,screen,policy,'s','g','screen')
            self.assertEqual(result['userConfirmedCircleJunctionRepair']['records'][0]['circle_handle'],self.circle)
            policy['review_evidence']['shown_circle_handles']=[]
            with self.assertRaises(ValueError):apply(self.doc,self.graph,self.rows,screen,policy,'s','g','screen')
            policy['review_evidence']['shown_circle_handles']=[self.circle];image.write_bytes(b'changed')
            with self.assertRaises(ValueError):apply(self.doc,self.graph,self.rows,screen,policy,'s','g','screen')
    def test_expert_confirmation_preserves_duplicate_identity_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            image=Path(td)/'pair.png';image.write_bytes(b'pair')
            manifest=Path(td)/'manifest.json';manifest.write_text(json.dumps({'source_sha256':'s','graph_sha256':'g','pairs':[{'connections':[{'circle_handle':self.circle}]}]}),encoding='utf8')
            issue=Path(td)/'issue.json';issue.write_text(json.dumps({'sourceHashes':{'main_dxf':'s'},'issue':{'id':'case','note':'connect','sourceBounds':[0,-50,1000,100],'nodes':['U'],'edges':['M','BR']}}),encoding='utf8')
            sh=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            main=self.doc.entitydb[self.graph['edges'][0]['source_handles'][0]];duplicate=self.doc.modelspace().add_line(main.dxf.start,main.dxf.end)
            screen=copy.deepcopy(self.screen);screen['graph_sha256']='g';screen['candidates'][0].update(coincident_native_main_handles=[main.dxf.handle,duplicate.dxf.handle],physical_main_identity='unresolved')
            policy=copy.deepcopy(self.policy);policy.update(screen_basis='current_graph',confirmation={'confirmed_by':'expert','question':'selected?','answer':'connect'},expert_issue_evidence={'issue':str(issue),'issue_sha256':sh(issue),'issue_id':'case'},review_evidence={'image':str(image),'image_sha256':sh(image),'manifest':str(manifest),'manifest_sha256':sh(manifest),'shown_circle_handles':[self.circle]})
            result,_,_=apply(self.doc,self.graph,self.rows,screen,policy,'s','g','screen')
            self.assertIn('expertConfirmedCircleJunctionRepair',result)
            branch=next(e for e in result['edges'] if e['edge_id']=='BR');self.assertEqual(branch['source_expert_circle_connection']['physical_main_identity'],'unresolved')
            issue.write_text('{}',encoding='utf8')
            with self.assertRaises(ValueError):apply(self.doc,self.graph,self.rows,screen,policy,'s','g','screen')

if __name__=='__main__':unittest.main()
