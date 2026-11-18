import copy
import unittest
import ezdxf
from confirmed_overlaid_supply import apply


class ConfirmedOverlayTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace();self.groups=[];self.graph={'metadata':{'source_sha256':'s'},'nodes':[],'edges':[]}
  for i,x in enumerate((0,10)):
   r=m.add_circle((x,-2),1,dxfattribs={'layer':'R'});c=m.add_circle((x,0),1,dxfattribs={'layer':'S'});line=m.add_line((x,1),(x,3),dxfattribs={'layer':'S'})
   gid='g'+str(i);uid='U'+str(i);eid='E'+str(i);eq='Q'+str(i)
   self.groups.append({'group_id':gid,'return_circle':r.dxf.handle,'supply_circle':c.dxf.handle,'supply_circle_center':[x,0],'supply_native_branch_handles':[line.dxf.handle]})
   self.graph['nodes'] += [{'node_id':uid,'node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','floor':'F1','x':x,'y':1},{'node_id':eq,'node_type':'equipment','x':x,'y':3}]
   self.graph['edges'].append({'edge_id':eid,'start_node_id':uid,'end_node_id':eq,'system':'supply','source_handles':[line.dxf.handle],'path_points':[[x,1],[x,3]],'attribute_paths':[[[x,1],[x,3]]],'path_length':2,'equipment_inventory':[],'floor_location_text_zh':'首层'})
  self.return_line=m.add_line((0,0),(10,0),dxfattribs={'layer':'R'})
  self.graph['confirmedCircleJunctions']={'source_sha256':'s','rewired_edge_ends':[{'circle_handle':g['return_circle']} for g in self.groups]}
  self.inventory={'source_sha256':'s','graph_sha256':'g','records':[{'node_id':'U'+str(i),'edge_id':'E'+str(i),'family':'circle_rim'} for i in range(2)]}
  self.spans={'source_sha256':'s','records':[{'group_a':'g0','group_b':'g1','a_xy':[0,0],'b_xy':[10,0],'span':10,'source_segments':[{'source_handle':self.return_line.dxf.handle,'source_layer':'R'}]}]}
  self.group_data={'source_sha256':'s','records':self.groups}
  self.policy={'source_sha256':'s','graph_sha256':'g','span_evidence_sha256':'span','group_evidence_sha256':'groups','supply_layer':'S','return_layer':'R','max_display_gap':6,'confirmed_spans':[{'pair':['g0','g1'],'kind':'hidden_supply'}],'user_confirmation':'confirmed','confirmation_evidence':'user response'}
 def run_apply(self):return apply(self.graph,self.inventory,self.doc,self.spans,self.group_data,self.policy,graph_sha256='g',source_sha256='s',inventory_sha256='i',span_evidence_sha256='span',group_evidence_sha256='groups')
 def test_hidden_span_requires_ring_and_preserves_source(self):
  before=copy.deepcopy(self.graph);g,inv,a=self.run_apply();self.assertEqual(self.graph,before)
  e=next(e for e in g['edges'] if e['edge_id'] in a['created_edges']);self.assertEqual(e['system'],'supply');self.assertEqual(e['attribute_paths'],[])
  self.assertFalse(e['path_length_complete']);self.assertEqual(e['physical_length'],'unknown');self.assertEqual(e['floor_location_text_zh'],'首层')
  self.assertEqual(len(inv['records']),0);self.assertFalse(g['metadata']['hil_ready'])
 def test_missing_circle_and_unauthorized_scope_rejected(self):
  self.graph['confirmedCircleJunctions']['rewired_edge_ends'].pop()
  with self.assertRaises(ValueError):self.run_apply()
  self.graph['confirmedCircleJunctions']['rewired_edge_ends'].append({'circle_handle':self.groups[1]['return_circle']});self.policy['confirmation_evidence']=''
  with self.assertRaises(ValueError):self.run_apply()
 def test_wrong_system_and_stale_inventory_rejected(self):
  self.graph['edges'][0]['system']='return'
  with self.assertRaises(ValueError):self.run_apply()
  self.graph['edges'][0]['system']='supply';self.inventory['graph_sha256']='stale'
  with self.assertRaises(ValueError):self.run_apply()
 def test_stale_evidence_and_crossing_without_matching_centers_rejected(self):
  self.policy['span_evidence_sha256']='old'
  with self.assertRaises(ValueError):self.run_apply()
  self.policy['span_evidence_sha256']='span';self.spans['records'][0]['a_xy']=[0,4]
  with self.assertRaises(ValueError):self.run_apply()
 def test_unrelated_parallel_source_line_rejected(self):
  self.return_line.dxf.start=(0,4,0);self.return_line.dxf.end=(10,4,0)
  with self.assertRaisesRegex(ValueError,'does not overlap'):self.run_apply()
 def test_native_partial_span_preserves_components(self):
  main=self.doc.modelspace().add_line((4,0),(6,0),dxfattribs={'layer':'S'})
  self.graph['nodes'] += [{'node_id':'U2','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','floor':'F1','x':4,'y':0},{'node_id':'U3','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','floor':'F1','x':6,'y':0}]
  e={'edge_id':'E2','start_node_id':'U2','end_node_id':'U3','system':'supply','source_handles':[main.dxf.handle],'path_points':[[4,0],[6,0]],'attribute_paths':[[[4,0],[6,0]]],'path_length':2,'equipment_inventory':[{'device_names':['V1'],'count':1}]}
  self.graph['edges'].append(copy.deepcopy(e));self.inventory['records'] += [{'node_id':'U2','edge_id':'E2','family':'no_circle'},{'node_id':'U3','edge_id':'E2','family':'no_circle'}]
  self.spans['records'][0]['source_segments'].append({'source_handle':main.dxf.handle,'source_layer':'S'});self.policy['confirmed_spans'][0]['kind']='native_partial_supply'
  g,inv,a=self.run_apply();actual=next(x for x in g['edges'] if x['edge_id']=='E2')
  for k in ('source_handles','attribute_paths','path_length','equipment_inventory'):self.assertEqual(actual[k],e[k])
  self.assertEqual(len(actual['source_overlay_connectors']),2);self.assertFalse(actual['path_length_complete']);self.assertEqual(inv['records'],[])
  self.assertEqual(actual['edge_type'],'tee_to_tee')

if __name__=='__main__':unittest.main()
