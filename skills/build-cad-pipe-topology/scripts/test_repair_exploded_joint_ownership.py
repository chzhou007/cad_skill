import copy,unittest,ezdxf,subprocess,sys
from pathlib import Path
from native_nested_joint_evidence import fingerprint
from repair_exploded_joint_ownership import repair

def fixture():
 d=ezdxf.new();b=d.blocks.new('HOSE');b.add_line((0,-1),(0,1));b.add_line((10,-1),(10,1))
 for x in (2,4,6,8):b.add_arc((x,0),1,0,180)
 m=d.modelspace();joint=m.add_blockref('HOSE',(0,0));left=m.add_line((-10,0),(0,0),dxfattribs={'layer':'空调冷冻水回水'});right=m.add_line((10,0),(20,0),dxfattribs={'layer':'空调冷冻水回水'})
 g={'nodes':[{'node_id':'D','node_type':'equipment'}], 'edges':[{'edge_id':'S','system':'supply','start_node_id':'D','end_node_id':'S1','device_label':'D','attribute_paths':[[[-10,3],[0,3]]],'equipment_inventory':[{'equipment_type':'金属软接','count':1,'device_names':['J']}]},{'edge_id':'R','system':'return','start_node_id':'D','end_node_id':'R1','device_label':'D','attribute_paths':[[[-10,0],[0,0]]],'equipment_inventory':[]}]}
 rows=[{'device_name':'J','equipment_type':'金属软接','source_block_name':'HOSE','source_top_handle':joint.dxf.handle,'owner_equipment':'D','edge_id':'S','assignment_status':'assigned','assignment_x':'0','assignment_y':'0','edge_distance':'3'}];h={'source_sha256':'S','graph_sha256':'G','devices_sha256':'D'};p=dict(h,joint_block='HOSE',block_fingerprint_sha256=fingerprint(b),corrections=[{'joint_handle':joint.dxf.handle,'device_name':'J','from_edge':'S','to_edge':'R'}]);return d,g,rows,p,h,right
class ExplodedJointTest(unittest.TestCase):
 def test_unique_same_system_repairs_inventory_without_topology_change(self):
  d,g,r,p,h,_=fixture();old=copy.deepcopy(g);out,rows,a=repair(d,g,r,p,h);self.assertEqual(g,old);self.assertEqual(out['nodes'],g['nodes']);self.assertEqual(rows[0]['edge_id'],'R');self.assertEqual(rows[0]['original_edge_id'],'S');self.assertEqual(len(a['changes']),1);self.assertFalse(out['metadata']['hil_ready'])
 def test_mixed_system_does_not_authorize_reassignment(self):
  d,g,r,p,h,right=fixture();right.dxf.layer='空调冷冻水供水'
  with self.assertRaisesRegex(ValueError,'not uniquely witnessed'):repair(d,g,r,p,h)
 def test_duplicate_contact_and_stale_hash_fail(self):
  d,g,r,p,h,_=fixture();d.modelspace().add_line((-10,0),(0,0),dxfattribs={'layer':'空调冷冻水回水'})
  with self.assertRaisesRegex(ValueError,'not uniquely witnessed'):repair(d,g,r,p,h)
  d,g,r,p,h,_=fixture();h['graph_sha256']='bad'
  with self.assertRaisesRegex(ValueError,'hash'):repair(d,g,r,p,h)
 def test_wrong_equipment_owner_is_rejected(self):
  d,g,r,p,h,_=fixture();g['edges'][1]['device_label']='OTHER'
  with self.assertRaisesRegex(ValueError,'owner'):repair(d,g,r,p,h)
 def test_entry_requires_attached_device_source_paths(self):
  p=Path(__file__).with_name('build_isometric_v17.py');r=subprocess.run([sys.executable,str(p),'--exploded-joint-ownership-policy','unused'],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('requires device source paths',r.stderr)
if __name__=='__main__':unittest.main()
