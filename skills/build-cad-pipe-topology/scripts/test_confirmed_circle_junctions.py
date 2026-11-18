import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import ezdxf
from confirmed_circle_junctions import apply


class ConfirmedCircleTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();self.circle=self.doc.modelspace().add_circle((0,0),1,dxfattribs={'layer':'return'})
  self.handle=self.circle.dxf.handle
  points=[(1,0),(0,1),(-1,0)]
  self.graph={'metadata':{'source_sha256':'source'},'nodes':[],'edges':[]}
  bindings=[]
  for i,(x,y) in enumerate(points):
   nid='U'+str(i);other='N'+str(i);eid='E'+str(i)
   self.graph['nodes'] += [{'node_id':nid,'node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'return','floor':'F1','x':x,'y':y},{'node_id':other,'node_type':'equipment','x':2*x,'y':2*y}]
   self.graph['edges'].append({'edge_id':eid,'start_node_id':nid,'end_node_id':other,'system':'return','source_handles':['H'+str(i)],'path_points':[[x,y],[2*x,2*y]],'attribute_paths':[[[x,y],[2*x,2*y]]],'path_length':1,'equipment_inventory':[{'id':i}]})
   bindings.append({'edge_id':eid,'edge_side':'start','existing_node_id':nid,'existing_source_handles':['H'+str(i)]})
  self.plan={'source_sha256':'source','graph_sha256':'graph','groups':[{'circle_handle':self.handle,'source_layer':'return','center':[0,0],'radius':1,'proposed_system':'return','old_boundary_nodes':['U0','U1','U2'],'proposed_edge_endpoint_rebindings':bindings}]}
  self.policy={'source_sha256':'source','graph_sha256':'graph','confirmed_circle_handles':[self.handle],'user_confirmation':'confirmed','confirmation_evidence':'human response'}
 def run_apply(self):return apply(self.graph,self.doc,self.plan,self.policy,graph_sha256='graph',source_sha256='source')
 def test_confirmed_junction_preserves_source_and_components(self):
  before=copy.deepcopy(self.graph);g,a=self.run_apply();self.assertEqual(self.graph,before)
  self.assertEqual(len(a['rewired_edge_ends']),3);self.assertEqual(len(a['new_tee_nodes']),1)
  tid=a['new_tee_nodes'][0];self.assertTrue(all(e['start_node_id']==tid for e in g['edges']))
  for old,new in zip(before['edges'],g['edges']):
   for key in ('attribute_paths','source_handles','path_length','equipment_inventory'):self.assertEqual(old[key],new[key])
   self.assertFalse(new['path_length_complete'])
  self.assertFalse(g['metadata']['hil_ready']);self.assertEqual(g['preHilComparison']['families'][-1]['status'],'algorithm_pending')
 def test_cross_service_rejected(self):
  self.graph['edges'][0]['system']='supply'
  with self.assertRaises(ValueError):self.run_apply()
 def test_no_circle_or_confirmation_rejected(self):
  self.policy['confirmed_circle_handles']=[]
  with self.assertRaises(ValueError):self.run_apply()
  self.policy['confirmed_circle_handles']=[self.handle];self.policy['confirmation_evidence']=''
  with self.assertRaises(ValueError):self.run_apply()
 def test_stale_sources_and_unexpected_source_handles_rejected(self):
  self.policy['source_sha256']='wrong'
  with self.assertRaises(ValueError):self.run_apply()
  self.policy['source_sha256']='source';self.graph['edges'][0]['source_handles']=['different']
  with self.assertRaises(ValueError):self.run_apply()
 def test_nonfinite_circle_geometry_rejected(self):
  self.plan['groups'][0]['center']=[float('nan'),0]
  with self.assertRaises(ValueError):self.run_apply()
 def test_duplicate_and_partial_endpoint_selection_rejected(self):
  self.plan['groups'][0]['proposed_edge_endpoint_rebindings'][1]=copy.deepcopy(self.plan['groups'][0]['proposed_edge_endpoint_rebindings'][0])
  with self.assertRaises(ValueError):self.run_apply()
 def test_cli_validates_hash_before_output(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'source.dxf';self.doc.saveas(source)
   source_hash=hashlib.sha256(source.read_bytes()).hexdigest();self.graph['metadata']['source_sha256']=source_hash
   graph=root/'graph.json';graph.write_text(json.dumps(self.graph),encoding='utf-8');graph_hash=hashlib.sha256(graph.read_bytes()).hexdigest()
   self.plan.update(source_sha256=source_hash,graph_sha256=graph_hash);self.policy.update(source_sha256=source_hash,graph_sha256=graph_hash)
   plan=root/'plan.json';plan.write_text(json.dumps(self.plan),encoding='utf-8')
   policy=root/'policy.json';policy.write_text(json.dumps(self.policy),encoding='utf-8')
   script=Path(__file__).with_name('confirmed_circle_junctions.py');output=root/'out'
   cmd=[sys.executable,str(script),'--graph',str(graph),'--source',str(source),'--plan',str(plan),'--policy',str(policy),'--output-dir',str(output)]
   stale=copy.deepcopy(self.policy);stale['source_sha256']='bad';policy.write_text(json.dumps(stale),encoding='utf-8')
   self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0);self.assertFalse(output.exists())
   policy.write_text(json.dumps(self.policy),encoding='utf-8')
   run=subprocess.run(cmd,capture_output=True);self.assertEqual(run.returncode,0,run.stderr)
   self.assertFalse(json.loads((output/'graph_with_edges.json').read_text(encoding='utf-8'))['metadata']['hil_ready'])
   self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)

if __name__=='__main__':unittest.main()
