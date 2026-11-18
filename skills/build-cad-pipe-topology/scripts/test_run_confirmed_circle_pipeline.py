import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_confirmed_circle_junctions import ConfirmedCircleTests

class PipelineTests(unittest.TestCase):
 def test_combined_post_build_and_bad_original_hash(self):
  f=ConfirmedCircleTests();f.setUp();h=f.handle
  f.doc.modelspace().add_text('冷塔单模块')
  f.graph['sourceThreeRimCandidates']=[{'circle_handle':h,'contacts':[{'node_id':'U'+str(i)} for i in range(3)]}]
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'source.dxf';f.doc.saveas(source);sh=hashlib.sha256(source.read_bytes()).hexdigest()
   f.graph['metadata']['source_sha256']=sh
   graph=root/'graph.json';graph.write_text(json.dumps(f.graph),encoding='utf-8');gh=hashlib.sha256(graph.read_bytes()).hexdigest()
   f.plan.update(source_sha256=sh,graph_sha256=gh);f.policy.update(source_sha256=sh,graph_sha256=gh,original_source_sha256=sh)
   inv={'source_sha256':sh,'graph_sha256':gh,'records':[{'node_id':'U'+str(i),'edge_id':'E'+str(i),'family':'circle_rim'} for i in range(3)]}
   for name,obj in [('plan.json',f.plan),('policy.json',f.policy),('inventory.json',inv)]:
    (root/name).write_text(json.dumps(obj,ensure_ascii=False),encoding='utf-8')
   out=root/'out';script=Path(__file__).with_name('run_confirmed_circle_pipeline.py')
   cmd=[sys.executable,str(script),'--graph',str(graph),'--source',str(source),'--original-source',str(source),'--plan',str(root/'plan.json'),'--policy',str(root/'policy.json'),'--inventory',str(root/'inventory.json'),'--output-dir',str(out)]
   self.assertNotEqual(subprocess.run(cmd+['--length-control',str(graph)],capture_output=True).returncode,0);self.assertFalse(out.exists())
   self.assertNotEqual(subprocess.run(cmd+['--overlay-spans',str(graph)],capture_output=True).returncode,0);self.assertFalse(out.exists())
   self.assertNotEqual(subprocess.run(cmd+['--component-inventory',str(graph)],capture_output=True).returncode,0);self.assertFalse(out.exists())
   bad=dict(f.policy,original_source_sha256='wrong');(root/'policy.json').write_text(json.dumps(bad),encoding='utf-8')
   self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0);self.assertFalse(out.exists())
   (root/'policy.json').write_text(json.dumps(f.policy),encoding='utf-8')
   result=subprocess.run(cmd,capture_output=True);self.assertEqual(result.returncode,0,result.stderr)
   final=json.loads((out/'graph_with_edges.json').read_text(encoding='utf-8'));invout=json.loads((out/'remaining-terminal-source-inventory.json').read_text(encoding='utf-8'))
   self.assertEqual(invout['graph_sha256'],hashlib.sha256((out/'graph_with_edges.json').read_bytes()).hexdigest())
   self.assertEqual(invout['records'],[]);self.assertEqual(len(final['sourceThreeRimCandidateHistory']['records']),1)
   self.assertFalse(final['metadata']['hil_ready']);self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)

if __name__=='__main__':unittest.main()
