import copy,unittest,subprocess,sys
from pathlib import Path
from test_native_nested_joint_evidence import fixture
from repair_offset_nested_joint_ownership import repair

def make_case():
 d,g,inv,c,p,h=fixture();circle=next(e for e in d.blocks['EQ'] if e.dxftype()=='CIRCLE');circle.dxf.center=(-9,0,0);circle.dxf.radius=10
 g['nodes']=[{'node_id':'D','node_type':'equipment'},{'node_id':'T1','node_type':'tee'},{'node_id':'T2','node_type':'tee'}];target=g['edges'][0];target.update(start_node_id='T1',end_node_id='D',equipment_inventory=[]);g['edges'].append({'edge_id':'R','system':'return','device_label':'D','start_node_id':'T2','end_node_id':'D','attribute_paths':[[[80,180],[80,190]]],'equipment_inventory':[{'equipment_type':'金属软接','count':1,'device_names':['J']}]});inv[0].update(edge_id='R',owner_equipment='D',assignment_x=inv[0]['x'],assignment_y=inv[0]['y']); hashes={'source_sha256':'S','graph_sha256':'G','devices_sha256':'I'};policy=dict(hashes,max_radius_ratio=.2,joint_block='HOSE',block_fingerprint_sha256=p['block_fingerprint_sha256'],corrections=[{'device_name':'J','from_edge':'R','to_edge':'E'}]);return d,g,inv,policy,hashes
class OffsetJointRepairTest(unittest.TestCase):
 def test_unique_source_moves_component_and_preserves_source_graph(self):
  d,g,i,p,h=make_case();before=copy.deepcopy(g);out,rows,a=repair(d,g,i,p,h);self.assertEqual(g,before);self.assertEqual(rows[0]['edge_id'],'E');self.assertEqual(out['edges'][0]['equipment_inventory'][0]['device_names'],['J']);self.assertEqual(out['edges'][1]['equipment_inventory'],[]);self.assertEqual(out['edges'][0]['attribute_paths'],g['edges'][0]['attribute_paths']);self.assertFalse(a['hil_ready'])
 def test_duplicate_graph_witness_is_rejected(self):
  d,g,i,p,h=make_case();duplicate=copy.deepcopy(g['edges'][0]);duplicate['edge_id']='E2';g['edges'].append(duplicate)
  with self.assertRaisesRegex(ValueError,'not unique'):repair(d,g,i,p,h)
 def test_scope_and_system_errors_are_rejected(self):
  d,g,i,p,h=make_case();p['corrections'][0]['from_edge']='wrong'
  with self.assertRaises(ValueError):repair(d,g,i,p,h)
  d,g,i,p,h=make_case();g['edges'][1]['system']='supply'
  with self.assertRaises(ValueError):repair(d,g,i,p,h)
 def test_entry_requires_previous_ownership_stage(self):
  script=Path(__file__).with_name('build_isometric_v17.py');r=subprocess.run([sys.executable,str(script),'--offset-nested-ownership-policy','unused'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('requires previous ownership stage',r.stderr)
 def test_incorrect_native_offset_is_rejected(self):
  d,g,i,p,h=make_case();circle=next(e for e in d.blocks['EQ'] if e.dxftype()=='CIRCLE');circle.dxf.center=(-10,0,0)
  with self.assertRaisesRegex(ValueError,'offset candidate'):repair(d,g,i,p,h)
if __name__=='__main__':unittest.main()
