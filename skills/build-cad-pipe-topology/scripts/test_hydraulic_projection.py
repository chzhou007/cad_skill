import unittest
from derive_hydraulic_graph import derive
class Projection(unittest.TestCase):
 def graph(self):return dict(nodes=[dict(node_id='A',node_type='tee',x=0,y=0),dict(node_id='P',node_type='equipment',subtype='Water Pump',x=10,y=0,source_handles=['pump']),dict(node_id='B',node_type='tee',x=20,y=0)],edges=[dict(edge_id='E1',start_node_id='A',end_node_id='P',system='supply',path_points=[[0,0],[9,0]],source_handles=['L']),dict(edge_id='E2',start_node_id='P',end_node_id='B',system='supply',path_points=[[11,0],[20,0]],source_handles=['R'])])
 def test_pump_is_one_edge_attribute_source_graph_unchanged(self):
  g=self.graph();v,rows,a=derive(g,[dict(device_name='V1',edge_id='E2')],{});self.assertEqual(len(g['nodes']),3);self.assertEqual(len(v['nodes']),2);self.assertEqual(len(v['edges']),1);self.assertEqual(len(v['edges'][0]['attribute_paths']),2);self.assertEqual({x['device_name']for x in rows},{'V1','P'});self.assertTrue(a['conservation'])
 def test_conflicting_system_pump_does_not_bridge(self):
  g=self.graph();g['edges'][1]['system']='return';v,rows,a=derive(g,[],{});self.assertEqual(len(v['edges']),2);self.assertIn('P',{n['node_id']for n in v['nodes']})
 def test_equipment_branch_exclusion_rejected(self):
  with self.assertRaises(ValueError):derive(self.graph(),[dict(device_name='V1',edge_id='E2')],dict(excluded_source_handles=['R']))
 def test_equipment_type_exclusion_rejected(self):
  with self.assertRaises(ValueError):derive(self.graph(),[],dict(excluded_equipment_types=['Water Pump']))
 def test_equipment_block_exclusion_rejected(self):
  g=self.graph();g['nodes'][1]['source_block']='BLOCK'
  with self.assertRaises(ValueError):derive(g,[],dict(excluded_equipment_blocks=['BLOCK']))
 def test_resistance_not_assumed_zero(self):
  g=self.graph();g['nodes'][1]['subtype']='Heat Exchanger';v,r,a=derive(g,[],{})
  n=next(n for n in v['nodes']if n['node_id']=='P');self.assertFalse(n['hydraulic_model']['assumed_zero_resistance']);self.assertFalse(v['hydraulicReadiness']['solver_ready'])
 def test_projection_never_inherits_human_confirmation(self):
  g=self.graph();g['metadata']={'hil_ready':True,'review_status':'reviewed'};out,_,_=derive(g,[],{})
  self.assertFalse(out['metadata']['hil_ready']);self.assertEqual(out['metadata']['review_status'],'unreviewed');self.assertTrue(g['metadata']['hil_ready'])
 def test_isolated_physical_equipment_not_dropped(self):
  g=self.graph();g['nodes'].append(dict(node_id='X',node_type='equipment',subtype='Dosing Unit',x=30,y=0));v,r,a=derive(g,[],{})
  self.assertIn('X',{n['node_id']for n in v['nodes']});self.assertEqual(next(n for n in v['hydraulicEquipmentCoverage']if n['node_id']=='X')['connection_status'],'source_ports_unresolved')
 def test_unresolved_detail_alternatives_block_projection(self):
  g=self.graph();g['sourceDetailComparison']={'status':'candidate_mapping_equipment_and_boundaries_pending'}
  with self.assertRaisesRegex(ValueError,'main/detail alternative'):derive(g,[],{})
 def test_unwitnessed_equipment_connector_blocks_projection_unless_confirmed(self):
  g=self.graph();g['metadata']={'source_sha256':'S'};e=g['edges'][0];e['attribute_paths']=[[[0,0],[9,0],[10,0]]];e['source_path_coverage']={'source_sha256':'S','unverified_segment_indices':[1]}
  with self.assertRaisesRegex(ValueError,'Unwitnessed equipment connection'):derive(g,[],{})
  c={'confirmed_by':'user','question':'接入该设备？','answer':'是'}
  e['confirmed_equipment_interface']={'source_sha256':'S','interface_side':'end','physical_port_verified':False,'interface_to_equipment_length_known':False,'original_interface':{'node_id':'V'},'confirmation':c}
  g['confirmedEquipmentInterfaceRepair']={'source_sha256':'S','confirmation':c.copy(),'mappings':[{'edge_id':'E1','equipment_id':'P','system':'supply','retired_node_id':'V'}]}
  derive(g,[],{})
  e['confirmed_equipment_interface']['confirmation']['confirmed_by']='inferred'
  with self.assertRaisesRegex(ValueError,'Unwitnessed equipment connection'):derive(g,[],{})
 def test_unverified_nonterminal_segment_does_not_imply_unverified_equipment_connector(self):
  g=self.graph();g['metadata']={'source_sha256':'S'};e=g['edges'][0];e['attribute_paths']=[[[0,0],[5,0],[10,0]]];e['source_path_coverage']={'source_sha256':'S','unverified_segment_indices':[0]}
  derive(g,[],{})
 def test_source_block_attachment_is_scoped_and_retained_on_contraction(self):
  import copy
  g=self.graph();g['metadata']={'source_sha256':'S'};e=g['edges'][0]
  e.update(attribute_paths=[[[0,0],[9,0],[10,0]]],source_path_coverage={'source_sha256':'S','unverified_segment_indices':[1]},physical_length='unknown',path_length_complete=False,source_insert_handle='ROOT')
  e['source_device_extension']={'status':'source_drawn_line_with_joint_evidence_unreviewed','source_sha256':'S','physical_port_verified':False,'physical_length':'unknown','source_circle_chain':['ROOT','C'],'source_joint_chain':['ROOT','J']}
  e['source_block_equipment_attachment']={'status':'source_supported_logical_attachment_not_human_accepted','source_sha256':'S','input_graph_sha256':'G','evidence_sha256':'H','equipment_id':'P','interface_side':'end','source_insert_handle':'ROOT','source_circle_handle':'C','source_joint_chain':['ROOT','J'],'physical_port_verified':False,'physical_length':'unknown','human_accepted':False}
  e['source_block_equipment_attachment']['source_edge_snapshot']={'start_node_id':e['start_node_id'],'end_node_id':e['end_node_id'],'system':e['system'],'attribute_paths':copy.deepcopy(e['attribute_paths']),'equipment_xy':[10,0]}
  g['sourceBlockEquipmentAttachment']={'status':'source_supported_logical_attachments_not_human_accepted','source_sha256':'S','input_graph_sha256':'G','evidence_sha256':'H','physical_ports_verified':False,'physical_lengths_known':False,'human_accepted':False,'mappings':[{'edge_id':'E1','equipment_id':'P','system':'supply','source_insert_handle':'ROOT','source_circle_handle':'C'}]}
  out,_,_=derive(g,[],{});merged=out['edges'][0]
  self.assertFalse(merged['path_length_complete']);self.assertNotIn('source_block_equipment_attachment',merged)
  self.assertEqual(merged['calculation_source_equipment_attachments'][0]['source_edge_id'],'E1')
  for change in ('source','joint','duplicate','path','equipment_xy'):
   bad=copy.deepcopy(g)
   if change=='source':bad['edges'][0]['source_block_equipment_attachment']['source_sha256']='wrong'
   elif change=='joint':bad['edges'][0]['source_device_extension']['source_joint_chain']=['wrong']
   elif change=='duplicate':bad['sourceBlockEquipmentAttachment']['mappings'].append(copy.deepcopy(bad['sourceBlockEquipmentAttachment']['mappings'][0]))
   elif change=='path':bad['edges'][0]['attribute_paths'][0][1][1]=1
   else:next(n for n in bad['nodes'] if n['node_id']=='P')['x']=11
   with self.assertRaisesRegex(ValueError,'Unwitnessed equipment connection'):derive(bad,[],{})
 def test_unresolved_source_conflicts_block_even_when_scope_excludes_edges(self):
  for key in ('sourceInlineSystemConflicts','sourceCircleCrossoverConflicts'):
   g=self.graph();g[key]=[{'status':'pending'}]
   with self.assertRaisesRegex(ValueError,'source conflict blocks'):derive(g,[],{'excluded_edge_ids':['E1']})
   g[key]='invalid'
   with self.assertRaisesRegex(ValueError,'Invalid source conflict'):derive(g,[],{})
 def test_inferred_circle_blocks_even_if_scope_would_exclude_it(self):
  g=self.graph();g['edges'][0]['source_expert_circle_link']={'similar_location_inferred':True,'expert_review':'unreviewed'}
  with self.assertRaisesRegex(ValueError,'Inferred similar-circle'):derive(g,[],{'excluded_edge_ids':['E1']})
  del g['edges'][0]['source_expert_circle_link'];g['expertLeftCircleRepairs']=[{'created_tee':'T','similar_location_inferred':True}]
  with self.assertRaisesRegex(ValueError,'Inferred similar-circle'):derive(g,[],{})
  g['expertLeftCircleRepairs'][0].pop('similar_location_inferred');derive(g,[],{})
 def test_source_pending_is_not_discarded(self):
  g=self.graph();g['technicalPending']=[{'id':'SOURCE-UNRESOLVED','reason':'source context'}]
  v,_,_=derive(g,[],{})
  self.assertEqual([x['id'] for x in v['technicalPending']],['SOURCE-UNRESOLVED','CALCULATION-SCOPE'])
  self.assertEqual(g['technicalPending'],[{'id':'SOURCE-UNRESOLVED','reason':'source context'}])
 def test_contraction_excludes_display_gap_and_conserves_both_component_inventories(self):
  g=self.graph();a,b=g['edges']
  a.update(path_length=10,source_path_length=9,path_length_complete=False,path_length_scope='source_only',equipment_inventory=[{'equipment_type':'Valve','count':1,'device_names':['V1']}],source_symbol_connectors=[{'source_circle_handle':'C1'}])
  b.update(path_length=10,source_path_length=9,path_length_complete=False,path_length_scope='source_only',equipment_inventory=[{'equipment_type':'Valve','count':1,'device_names':['V2']}],source_symbol_connectors=[{'source_circle_handle':'C2'}])
  out,rows,audit=derive(g,[{'device_name':'V1','edge_id':'E1'},{'device_name':'V2','edge_id':'E2'}],{})
  e=out['edges'][0];self.assertEqual(e['path_length'],18);self.assertFalse(e['path_length_complete'])
  self.assertEqual(e['path_length_scope'],'sum_of_source_edge_lengths_no_display_connector')
  self.assertEqual(e['equipment_inventory'],[{'equipment_type':'Valve','count':2,'device_names':['V1','V2']}])
  self.assertEqual([x['source_circle_handle'] for x in e['source_symbol_connectors']],['C1','C2'])
  self.assertEqual({x['device_name'] for x in rows},{'V1','V2','P'});self.assertTrue(audit['conservation'])
  self.assertEqual(len(e['calculation_source_length_evidence']),2)
 def test_unknown_source_length_stays_unknown(self):
  g=self.graph();g['edges'][0].update(path_length=9,path_length_complete=True)
  out,_,_=derive(g,[],{});self.assertIsNone(out['edges'][0]['path_length']);self.assertFalse(out['edges'][0]['path_length_complete'])
 def test_incomplete_unqualified_display_length_is_not_used(self):
  g=self.graph();g['edges'][0].update(path_length=9,path_length_complete=True)
  g['edges'][1].update(path_length=11,path_length_complete=False)
  out,_,_=derive(g,[],{});self.assertIsNone(out['edges'][0]['path_length']);self.assertFalse(out['edges'][0]['path_length_complete'])
 def test_contiguous_complete_lengths_can_remain_complete(self):
  g=self.graph();g['edges'][0].update(path_points=[[0,0],[10,0]],path_length=10,path_length_complete=True)
  g['edges'][1].update(path_points=[[10,0],[20,0]],path_length=10,path_length_complete=True)
  out,_,_=derive(g,[],{});self.assertEqual(out['edges'][0]['path_length'],20);self.assertTrue(out['edges'][0]['path_length_complete'])
 def test_duplicate_component_identity_rejected(self):
  g=self.graph()
  for e in g['edges']:e['equipment_inventory']=[{'equipment_type':'Valve','count':1,'device_names':['V1']}]
  with self.assertRaisesRegex(ValueError,'Duplicate'):derive(g,[],{})
if __name__=='__main__':unittest.main()
