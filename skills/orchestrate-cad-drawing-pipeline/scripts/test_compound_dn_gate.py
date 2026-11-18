import hashlib,json,tempfile,unittest
from pathlib import Path
from source_comparison_gate import compound_dn_context

class CompoundDNGateTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'reports').mkdir();self.graph={'edges':[{'edge_id':'E'}]};self.e={'status':'compound_dn_text_evidence_not_binding','source_sha256':'S','graph_sha256':'G','graph_mutated':False,'human_accepted':False,'hil_ready':False,'records':[{'source_text':{'handle':'H','source_sha256':'S','text':'DN300/DN200'},'values_in_text_order':[{'order_in_text':1,'nominal_mm':300},{'order_in_text':2,'nominal_mm':200}],'candidate_edge_ids':['E'],'status':'compound_values_unbound','edge_binding_confirmed':False,'parenthesized_value_meaning':'uninterpreted','human_accepted':False}]};self.s={'status':self.e['status'],'source_sha256':'S','graph_sha256':'G','candidate_count':1,'hil_ready':False}
 def tearDown(self):self.tmp.cleanup()
 def write(self):
  p=self.root/'reports/final-compound-dn-evidence.json';p.write_text(json.dumps(self.e),encoding='utf8');self.s['evidence_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(self.root/'reports/final-compound-dn-stage.json').write_text(json.dumps(self.s),encoding='utf8')
 def test_current_unbound_text_is_pending(self):
  self.write();r=compound_dn_context(self.root,'G','S',self.graph);self.assertEqual(r[0]['source_handle'],'H');self.assertEqual(r[0]['status'],'compound_dn_edge_binding_unverified')
 def test_stale_or_claimed_binding_fails_closed(self):
  self.write()
  with self.assertRaises(ValueError):compound_dn_context(self.root,'other','S',self.graph)
  self.e['records'][0]['edge_binding_confirmed']=True;self.write()
  with self.assertRaises(ValueError):compound_dn_context(self.root,'G','S',self.graph)
 def test_missing_pair_fails(self):
  self.write();(self.root/'reports/final-compound-dn-stage.json').unlink()
  with self.assertRaises(ValueError):compound_dn_context(self.root,'G','S',self.graph)
 def test_declared_stage_cannot_disappear_as_an_optional_screen(self):
  self.write();d={'status':'required_compound_dn_screen','source_sha256':'S','graph_sha256':'G','policy_map_sha256':'a'*64,'evidence_path':'reports/final-compound-dn-evidence.json','stage_path':'reports/final-compound-dn-stage.json','hil_ready':False};(self.root/'compound-dn-required.json').write_text(json.dumps(d),encoding='utf8');self.assertEqual(len(compound_dn_context(self.root,'G','S',self.graph)),1)
  (self.root/'reports/final-compound-dn-stage.json').unlink();(self.root/'reports/final-compound-dn-evidence.json').unlink()
  with self.assertRaisesRegex(ValueError,'required compound DN stage missing'):compound_dn_context(self.root,'G','S',self.graph)
if __name__=='__main__':unittest.main()
