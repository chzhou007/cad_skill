import copy,json,tempfile,unittest
from pathlib import Path
from replay_family_source_backtest import validate_manifest,edge_key,node_key,exact_map,MODE,sha,compare

class FamilyBacktestTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=self.root/'source.dxf';self.source.write_text('原图')
  self.config=self.root/'config.json';self.config.write_text('{}')
  pin=lambda p:dict(path=str(p),sha256=sha(p))
  self.row=dict(id='03-native',entry='schematic',drawing='03',input_role='primary_non_T3',inputs=dict(source=pin(self.source),config=pin(self.config),profiles=pin(self.config),bindings=pin(self.config)))
  self.manifest=dict(schema=MODE,cases=[self.row])
 def test_native_and_historical_prepared_lanes_keep_distinct_identity(self):
  other=copy.deepcopy(self.row);other.update(id='03-prepared',input_role='historical_prepared_reference_separate');self.manifest['cases'].append(other)
  fixed=validate_manifest(self.manifest);self.assertEqual(len(fixed),2)
 def test_T3_cannot_be_relabelled_native_and_mutated_input_is_rejected(self):
  self.source.rename(self.root/'source_t3.dxf');self.row['inputs']['source']['path']=str(self.root/'source_t3.dxf')
  with self.assertRaisesRegex(ValueError,'non-T3'):validate_manifest(self.manifest)
  self.row['input_role']='historical_prepared_reference_separate';validate_manifest(self.manifest)
  self.config.write_text('changed')
  with self.assertRaisesRegex(ValueError,'fixed family input changed'):validate_manifest(self.manifest)
 def test_escape_case_duplicate_case_and_unproved_entry_rejected(self):
  self.row['id']='../elsewhere'
  with self.assertRaisesRegex(ValueError,'case identity'):validate_manifest(self.manifest)
  self.row['id']='X';self.manifest['cases'].append(copy.deepcopy(self.row));self.manifest['cases'][1]['id']='x'
  with self.assertRaisesRegex(ValueError,'case identity'):validate_manifest(self.manifest)
  self.manifest['cases'].pop();self.row['entry']='arbitrary-script'
  with self.assertRaisesRegex(ValueError,'original entry'):validate_manifest(self.manifest)
 def graphs(self):
  old=dict(nodes=[dict(node_id='A',x=0,y=0,source_handles=['N1'],node_type='tee'),dict(node_id='B',x=10,y=0,source_handles=['N2'],node_type='tee')],edges=[dict(edge_id='E1',start_node_id='A',end_node_id='B',system='supply',source_handles=['LINE1'],attribute_paths=[[[0,0],[10,0]]],path_length=10)])
  new=copy.deepcopy(old);new['nodes'][0]['node_id']='N99';new['nodes'][1]['node_id']='N98';new['edges'][0].update(edge_id='E99',start_node_id='N99',end_node_id='N98');return old,new
 def compare(self,old,new):
  before=self.root/'old.json';before.write_text(json.dumps(old));out=self.root/'output';out.mkdir(exist_ok=True);(out/'graph_with_edges.json').write_text(json.dumps(new));return compare(dict(graph=dict(path=str(before),sha256=sha(before))),out)
 def test_numeric_ID_changes_do_not_change_source_correspondence(self):
  old,new=self.graphs();result=self.compare(old,new);self.assertEqual(result['old_to_new_edges'],{'E1':'E99'});self.assertTrue(result['exact_native_geometry_and_adjacency']);self.assertFalse(result['historical_annotations_transferred'])
 def test_same_counts_but_shifted_geometry_or_system_never_pass(self):
  old,new=self.graphs();new['edges'][0]['system']='return'
  with self.assertRaisesRegex(ValueError,'source identities'):self.compare(old,new)
  old,new=self.graphs();new['nodes'][0]['x']=.01
  with self.assertRaisesRegex(ValueError,'source identities'):self.compare(old,new)
 def test_role_difference_retained_even_when_paths_match(self):
  old,new=self.graphs();new['nodes'][0]['node_type']='virtual_equipment';r=self.compare(old,new);self.assertEqual(len(r['node_role_differences']),1)
 def test_ambiguous_source_identity_does_not_use_ID_as_tiebreaker(self):
  old,new=self.graphs();new['edges'].append(copy.deepcopy(new['edges'][0]));new['edges'][1]['edge_id']='E100'
  with self.assertRaisesRegex(ValueError,'ambiguous'):self.compare(old,new)
if __name__=='__main__':unittest.main()
