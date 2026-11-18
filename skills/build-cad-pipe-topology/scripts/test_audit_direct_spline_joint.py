import unittest,ezdxf,subprocess,sys
from pathlib import Path
from audit_direct_spline_joint import audit

def fixture():
 d=ezdxf.new();b=d.blocks.new('SPLINE_JOINT');b.add_line((0,-1),(0,1));b.add_line((10,-1),(10,1));b.add_point((0,0));b.add_point((10,0));b.add_spline(fit_points=[(0,0),(5,2),(10,0)]);m=d.modelspace();j=m.add_blockref('SPLINE_JOINT',(100,200));layer='空调冷冻水供水';m.add_line((90,200),(100,200),dxfattribs={'layer':layer});m.add_line((110,200),(120,200),dxfattribs={'layer':layer});g={'edges':[{'edge_id':'E','system':'supply','attribute_paths':[[[90,200],[100,200]],[[110,200],[120,200]]]}]};i=[{'device_name':'J','equipment_type':'金属软接','edge_id':'E','assignment_status':'assigned','source_block_name':'SPLINE_JOINT','source_top_handle':j.dxf.handle,'x':'100','y':'200'}];h={'source_sha256':'S','graph_sha256':'G','inventory_sha256':'I'};return d,g,i,dict(h,block_name='SPLINE_JOINT',components=['J']),h
class DirectSplineTest(unittest.TestCase):
 def test_two_distinct_pipes_on_separate_paths(self):
  d,g,i,p,h=fixture();r=audit(d,g,i,p,h);self.assertEqual(r['records'][0]['status'],'same_system_assigned_edge_contact_witnessed');self.assertFalse(r['graph_mutated']);self.assertFalse(r['hil_ready'])
 def test_single_pipe_across_both_contact_points(self):
  d,g,i,p,h=fixture();m=d.modelspace();[m.delete_entity(x) for x in list(m.query('LINE'))];m.add_line((90,200),(120,200),dxfattribs={'layer':'空调冷冻水供水'});g['edges'][0]['attribute_paths']=[[[90,200],[120,200]]];self.assertEqual(audit(d,g,i,p,h)['records'][0]['status'],'same_system_assigned_edge_contact_witnessed')
 def test_opposite_system_and_missing_graph_witness(self):
  d,g,i,p,h=fixture();list(d.modelspace().query('LINE'))[-1].dxf.layer='空调冷冻水回水';self.assertEqual(audit(d,g,i,p,h)['records'][0]['status'],'opposite_system_source_conflict')
  d,g,i,p,h=fixture();g['edges'][0]['attribute_paths']=g['edges'][0]['attribute_paths'][:1];self.assertEqual(audit(d,g,i,p,h)['records'][0]['status'],'assigned_edge_not_witnessed_on_both_contacts')
 def test_entry_requires_ownership_graph(self):
  script=Path(__file__).with_name('build_isometric_v17.py');r=subprocess.run([sys.executable,str(script),'--direct-spline-joint-policy','unused'],capture_output=True,text=True);self.assertNotEqual(r.returncode,0);self.assertIn('requires final ownership graph',r.stderr)
 def test_bad_hash_or_component_binding_rejected(self):
  d,g,i,p,h=fixture();p['graph_sha256']='bad'
  with self.assertRaises(ValueError):audit(d,g,i,p,h)
  p['graph_sha256']='G';i[0]['source_top_handle']='bad'
  with self.assertRaises(ValueError):audit(d,g,i,p,h)
if __name__=='__main__':unittest.main()
