import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from build_calculation_aggregate import build

class AggregateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);p=Path(self.tmp.name);self.tasks=[]
  for tid in ['a','b']:
   g={'nodes':[{'node_id':'v','node_type':'virtual_equipment','x':0,'y':0,'ports':[{'port_id':'s','system':'supply','x':0,'y':0},{'port_id':'r','system':'return','x':1,'y':0}]},{'node_id':'t','node_type':'tee','x':2,'y':0}],'edges':[{'edge_id':'e','start_node_id':'v','start_port_id':'s','end_node_id':'t','system':'supply'}]};f=p/(tid+'.json');f.write_text(json.dumps(g));d=p/(tid+'.csv');d.write_text('edge_id,device_name\ne,valve\n');self.tasks.append(dict(task_id=tid,graph=str(f),graph_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),devices=str(d),scope='test'))
  self.cfg=dict(project_id='test',tasks=self.tasks,links=[{'from':'a::s','to':'b::s','evidence':'test'}])
 def test_ports_split_sources_immutable(self):
  before=[Path(t['graph']).read_bytes()for t in self.tasks];g=build(self.cfg);self.assertEqual(6,len(g['nodes']));self.assertEqual(2,len(g['edges']));self.assertEqual(1,len(g['proposed_links']));self.assertFalse(g['metadata']['default_include_proposed_links']);self.assertEqual(before,[Path(t['graph']).read_bytes()for t in self.tasks]);self.assertEqual(2,len(g['instances']))
 def test_cross_system_rejected(self):
  self.cfg['links'][0]['to']='b::r'
  with self.assertRaises(ValueError):build(self.cfg)
 def test_reused_port_rejected(self):
  self.cfg['links']*=2
  with self.assertRaises(ValueError):build(self.cfg)
 def test_changed_source_rejected(self):
  Path(self.tasks[0]['graph']).write_text('{}')
  with self.assertRaises(ValueError):build(self.cfg)
if __name__=='__main__':unittest.main()
