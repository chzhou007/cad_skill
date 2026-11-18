import copy, unittest,subprocess,sys
from pathlib import Path
from test_native_nested_joint_evidence import fixture
from native_nested_joint_evidence import collect
from attach_native_device_source_paths import attach


def setup():
 d,g,i,c,p,h=fixture();g['nodes']=[{'node_id':'D','node_type':'equipment'}];g['edges'][0].update(start_node_id='D',end_node_id='T',physical_length='unknown',path_length_complete=False,source_path_coverage={'source_sha256':'S'});h['joint_sha256']='J';j=collect(d,g,i,c,p,h)
 return d,g,i,c,j,p,h


class AttachTest(unittest.TestCase):
 def test_attach_changes_evidence_only(self):
  d,g,i,c,j,p,h=setup();before=copy.deepcopy(g);r=attach(d,g,i,c,j,p,h);self.assertEqual(g,before)
  ext=r['edges'][0].pop('source_device_extension');self.assertEqual(r['edges'],g['edges']);self.assertFalse(ext['physical_port_verified']);self.assertFalse(ext['changes_topology']);self.assertEqual(ext['physical_length'],'unknown')
 def test_fails_on_changed_graph_or_incomplete_length_protection(self):
  d,g,i,c,j,p,h=setup();j['edges'][0]['matches'][0]['component_name']='different'
  with self.assertRaisesRegex(ValueError,'reproduce'):attach(d,g,i,c,j,p,h)
  d,g,i,c,j,p,h=setup();g['edges'][0]['physical_length']=0
  with self.assertRaisesRegex(ValueError,'length protection'):attach(d,g,i,c,j,p,h)
 def test_entry_requires_joint_policy(self):
  p=Path(__file__).with_name('build_isometric_v17.py');r=subprocess.run([sys.executable,str(p),'--attach-device-source-paths'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('require nested joint evidence',r.stderr)


if __name__=='__main__':unittest.main()
