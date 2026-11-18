import copy,unittest,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
import ezdxf
from convert_expert_non_node_boundaries import convert
class ConvertBoundaries(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();m=self.d.modelspace();self.l=m.add_line((1,1),(1,5),dxfattribs={'layer':'P'});self.c=m.add_circle((1,1),.8,dxfattribs={'layer':'P'});self.s={'expert_node_id':'OLD','system':'supply','pipe_handle':self.l.dxf.handle,'circle_handle':self.c.dxf.handle,'x':1,'y':1,'radius':.8,'source_layer':'P'};self.p={'source_sha256':'sha','expert_issue':'ERR','expert_note':'not node','anchors':[self.s]};self.i={'sourceHashes':{'main_dxf':'sha'},'issue':{'label':'ERR','note':'not node','sourceBounds':[0,0,3,3],'nodes':['OLD']}};self.g={'metadata':{'source_sha256':'sha'},'nodes':[{'node_id':'N','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','x':1,'y':1,'source_handles':[self.l.dxf.handle]},{'node_id':'T'}],'edges':[{'edge_id':'E','start_node_id':'T','end_node_id':'N','system':'supply','source_handles':[self.l.dxf.handle]}]}
 def test_leaf_converts_without_mutation(self):
  before=copy.deepcopy(self.g);r,c=convert(self.g,self.d,self.i,self.p);self.assertEqual(before,self.g);self.assertEqual(len(r['nodes']),1);self.assertEqual(r['edges'][0]['end_boundary_id'],'A-N');self.assertIsNone(r['edges'][0]['end_node_id']);self.assertEqual(r['boundary_anchors'][0]['legacy_node'],before['nodes'][0]);self.assertFalse(r['metadata']['hil_ready']);self.assertEqual(c[0]['input_node_id'],'N')
 def test_nonleaf_and_system_conflict_rejected(self):
  for kind in ('nonleaf','system'):
   g=copy.deepcopy(self.g)
   if kind=='nonleaf':g['edges'].append(dict(g['edges'][0],edge_id='E2'))
   else:g['edges'][0]['system']='return'
   with self.assertRaises(ValueError):convert(g,self.d,self.i,self.p)
 def test_expert_scope_and_geometry_rejected(self):
  for field,value in [('expert_node_id','WRONG'),('source_layer','bad'),('radius',5),('x',2)]:
   p=copy.deepcopy(self.p);p['anchors'][0][field]=value
   with self.assertRaises(ValueError):convert(self.g,self.d,self.i,p)
 def test_no_system_reclassification_or_crossing_join(self):
  g=copy.deepcopy(self.g);g['nodes'].append({'node_id':'X','system':'return'});g['edges'].append({'edge_id':'R','start_node_id':'X','end_node_id':'T','system':'return','source_handles':[]});r,_=convert(g,self.d,self.i,self.p);self.assertEqual(r['edges'][1],g['edges'][1])
 def test_comparison_references_cannot_be_orphaned(self):
  g=copy.deepcopy(self.g);g['sourceDetailComparison']={'pairs':[{'detail_tee':'T','upper_terminal':'N','upper_edge':'E'}]}
  with self.assertRaisesRegex(ValueError,'detail comparison references invalid'):convert(g,self.d,self.i,self.p)
 def test_two_bar_marker_requires_both_source_lines(self):
  m=self.d.modelspace();a=m.add_line((0,1),(2,1),dxfattribs={'layer':'MARK'});b=m.add_line((.5,1.5),(1.5,1.5),dxfattribs={'layer':'MARK'});p=copy.deepcopy(self.p);s=p['anchors'][0];s.pop('circle_handle');s.update(marker_kind='two_bar',marker_handles=[a.dxf.handle,b.dxf.handle],marker_layer='MARK',long_length=2,short_length=1,spacing=.5)
  r,_=convert(self.g,self.d,self.i,p);self.assertEqual(r['boundary_anchors'][0]['source_marker_handles'],[a.dxf.handle,b.dxf.handle]);self.assertEqual(r['boundary_anchors'][0]['connectivity_beyond_boundary'],'unknown')
  p['anchors'][0]['marker_handles'][1]='MISSING'
  with self.assertRaisesRegex(ValueError,'two-bar source mismatch'):convert(self.g,self.d,self.i,p)
 def test_similar_marker_requires_reference_and_preserves_existing_anchors(self):
  m=self.d.modelspace();ref1=m.add_line((0,1),(2,1),dxfattribs={'layer':'MARK'});ref2=m.add_line((.5,1.5),(1.5,1.5),dxfattribs={'layer':'MARK'});pipe=m.add_line((10,1),(10,5),dxfattribs={'layer':'P'});a=m.add_line((9,1),(11,1),dxfattribs={'layer':'MARK'});b=m.add_line((9.5,1.5),(10.5,1.5),dxfattribs={'layer':'MARK'});g=copy.deepcopy(self.g);g['nodes'][0].update(x=10,source_handles=[pipe.dxf.handle]);g['edges'][0]['source_handles']=[pipe.dxf.handle];g['boundary_anchors']=[{'boundary_id':'existing'}];p=copy.deepcopy(self.p);s=p['anchors'][0];s.clear();s.update(system='supply',pipe_handle=pipe.dxf.handle,x=10,y=1,source_layer='P',marker_kind='two_bar',marker_handles=[a.dxf.handle,b.dxf.handle],marker_layer='MARK',long_length=2,short_length=1,spacing=.5,evidence_basis='source_similar_inferred',reference_expert_node_id='OLD',reference_pipe_handle=self.l.dxf.handle,reference_marker_handles=[ref1.dxf.handle,ref2.dxf.handle],allow_outside_expert_region=True)
  r,_=convert(g,self.d,self.i,p);self.assertEqual(len(r['boundary_anchors']),2);self.assertEqual(r['boundary_anchors'][1]['evidence_basis'],'source_similar_inferred')
  s['reference_expert_node_id']='wrong'
  with self.assertRaisesRegex(ValueError,'expert reference'):convert(g,self.d,self.i,p)
 def test_cli_rejects_unpinned_graph_without_output(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);paths={k:root/k for k in ('source','graph','devices','issue','policy')}
   for k in ('source','graph','devices','issue'):paths[k].write_text(k,encoding='utf8')
   sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
   policy={'source_sha256':sha(paths['source']),'input_graph_sha256':'wrong','devices_sha256':sha(paths['devices']),'issue_sha256':sha(paths['issue'])};paths['policy'].write_text(json.dumps(policy),encoding='utf8');out=root/'out';cmd=[sys.executable,str(Path(__file__).with_name('convert_expert_non_node_boundaries.py'))]
   for k,p in paths.items():cmd.extend(['--'+k,str(p)])
   result=subprocess.run(cmd+['--output',str(out)],capture_output=True,text=True);self.assertNotEqual(result.returncode,0);self.assertIn('input_graph_sha256 mismatch',result.stderr);self.assertFalse(out.exists())
if __name__=='__main__':unittest.main()
