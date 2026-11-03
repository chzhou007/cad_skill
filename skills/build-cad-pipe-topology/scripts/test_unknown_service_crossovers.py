import unittest,tempfile,json
from pathlib import Path
import ezdxf
import pipe_geometry as pg
from straight_crossovers import recover_straight_crossovers
from source_coverage_gate import source_coverage_gate
class UnknownServiceCrossovers(unittest.TestCase):
 def fixture(self):
  return [dict(a=(-100,0),b=(-10,0),system='physical',source_system='unclassified_water',source_layer='N',handle='L'),dict(a=(10,0),b=(100,0),system='physical',source_system='unclassified_water',source_layer='N',handle='R'),dict(a=(0,-100),b=(0,100),system='physical',source_system='return',source_layer='CWR',handle='X')]
 def run_case(self,segs=None,**kw):
  cfg=dict(maximum_gap_native_units=30,verified_unknown_service_layers=['N']);cfg.update(kw);audit=[];spans,applied=recover_straight_crossovers(self.fixture()if segs is None else segs,[],cfg,discovery_audit=audit);return spans,applied,audit
 def test_verified_unknown_group_restores_without_assigning_service(self):
  spans,audit,discovery=self.run_case();self.assertEqual(len(spans),1);self.assertEqual(spans[0]['source_system'],'unclassified_water');self.assertEqual(spans[0]['crossing_connectivity'],'independent_pipes_no_junction');self.assertEqual(audit[0]['source_group_evidence']['source_layer'],'N')
 def test_unverified_group_is_explicit_not_silent_no_evidence(self):
  spans,audit,d=self.run_case(verified_unknown_service_layers=[]);self.assertEqual(spans,[]);self.assertTrue(any(r['reason']=='source_group_not_verified_despite_crossing_evidence'and r['crossings']for r in d))
 def test_different_unknown_source_layers_do_not_join(self):
  ss=self.fixture();ss[1]['source_layer']='OTHER';spans,_,d=self.run_case(ss,verified_unknown_service_layers=['N','OTHER']);self.assertEqual(spans,[]);self.assertTrue(any(r['reason']=='conflicting_source_groups'for r in d))
 def test_conflicting_known_services_do_not_join(self):
  ss=self.fixture();ss[0]['source_system']='supply';ss[1]['source_system']='return';self.assertEqual(self.run_case(ss)[0],[])
 def test_ordinary_gap_remains_unjoined_with_explicit_reason(self):
  spans,_,d=self.run_case(self.fixture()[:2]);self.assertEqual(spans,[]);self.assertTrue(any(r['reason']=='no_independent_crossed_pipe'for r in d))
 def test_multiple_crossed_pipes_are_ambiguous(self):
  ss=self.fixture();ss.append(dict(ss[2],a=(5,-100),b=(5,100),handle='X2'));self.assertEqual(self.run_case(ss)[0],[])
 def test_native_inline_symbol_gap_is_excluded(self):
  audit=[];ss=self.fixture();symbols=[dict(block='VALVE',bounds=[-11,-2,11,2])];spans,_=recover_straight_crossovers(ss,symbols,dict(maximum_gap_native_units=30,verified_unknown_service_layers=['N'],exclude_symbol_bounds=True),discovery_audit=audit);self.assertEqual(spans,[]);self.assertTrue(any(r['reason']=='native_symbol_interference'for r in audit))
 def test_gap_endpoint_true_branch_is_preserved(self):
  ss=self.fixture();ss.append(dict(a=(-10,0),b=(-10,100),system='physical',source_system='unclassified_water',source_layer='N',handle='SIDE'));spans,_,_=self.run_case(ss);self.assertEqual(len(spans),1)
 def gate(self,complete):
  d=ezdxf.new();cfg=dict(system_layers={},auxiliary_pipe_layer='N',required_source_gap_spans=[dict(a=(-10,0),b=(10,0),source_handles=['L','R'])]);edge=dict(edge_id='E1',start_node_id='A',end_node_id='B',source_handles=['L','R'],attribute_paths=[[(-100,0),(100,0)]]if complete else[[(-100,0),(-10,0)],[(10,0),(100,0)]]);g=dict(nodes=[dict(node_id='A',node_type='virtual_equipment'),dict(node_id='B',node_type='virtual_equipment')],edges=[edge])
  with tempfile.TemporaryDirectory()as tmp:return source_coverage_gate(d,g,cfg,Path(tmp))
 def test_gate_blocks_gap_even_when_both_source_handles_exist(self):
  with self.assertRaises(ValueError):self.gate(False)
 def test_gate_accepts_complete_source_span(self):self.assertEqual(self.gate(True)['status'],'PASS_WITH_PENDING_CONTEXT')
 def test_gate_blocks_proven_crossing_skipped_only_by_service_filter(self):
  _,_,discovery=self.run_case(verified_unknown_service_layers=[])
  with tempfile.TemporaryDirectory()as tmp:
   out=Path(tmp);(out/'straight_crossover_discovery.json').write_text(json.dumps(discovery),encoding='utf8')
   with self.assertRaises(ValueError):source_coverage_gate(ezdxf.new(),dict(nodes=[],edges=[]),dict(system_layers={},auxiliary_pipe_layer='N'),out)
   self.assertTrue(json.loads((out/'source_group_gap_blockers.json').read_text()))
if __name__=='__main__':unittest.main(verbosity=2)
