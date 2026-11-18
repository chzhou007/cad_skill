import copy,unittest
from unittest.mock import patch
import test_native_named_riser_evidence as old_fixture
from batch_native_named_interfaces import discover

class NamedBatchTests(unittest.TestCase):
    def fixture(self):
        f=old_fixture.NamedRiserEvidenceTests();f.setUp();return f
    def read(self,f,**kwargs):return discover(f.doc,f.graph,f.source,f.hash,'plan',['ANNOT'],['ANNOT'],**kwargs)
    def test_complete_local_discovery_reuses_native_reader_without_assigning_edge_DN(self):
        f=self.fixture();before=copy.deepcopy(f.graph);r=self.read(f);self.assertEqual(r['counts'],dict(source_labels=1,source_witnessed=1,pending=0));row=r['records'][0]
        self.assertEqual(row['role'],'plan_riser_circle');self.assertEqual(row['node_id'],'RIF1');self.assertEqual(row['observed_named_DN_mm'],450);self.assertFalse(row['native_evidence']['physical_diameter_selected']);self.assertEqual(r['whole_edge_DN_assigned'],0);self.assertEqual(f.graph,before)
    def test_one_bad_caption_does_not_stop_independent_source_labels(self):
        f=self.fixture();f.doc.modelspace().add_text('CHWS3 DN200',dxfattribs=dict(insert=(100,100),height=2,layer='ANNOT'));r=self.read(f)
        self.assertEqual(r['counts'],dict(source_labels=2,source_witnessed=1,pending=1));self.assertEqual(len(r['named_source_evidence']['records']),1)
    def test_axis_and_plan_roles_do_not_merge_from_equal_names(self):
        f=self.fixture();r=discover(f.doc,f.graph,f.source,f.hash,'axis',['ANNOT'],['ANNOT']);self.assertEqual(r['counts']['source_witnessed'],1);self.assertEqual(r['records'][0]['role'],'axis_source_line');self.assertIsNone(r['records'][0]['floor']);self.assertEqual(r['crossview_mappings_assigned'],0)
    def test_rejected_external_provider_cannot_fall_back_to_weaker_named_binding(self):
        f=self.fixture();policy=dict(source_sha256=f.source,members=[dict(text_handle=f.text.dxf.handle)])
        with patch('batch_native_named_interfaces.external_plan_collect',side_effect=ValueError('marker membership incomplete')):
            r=self.read(f,external_templates=[dict(kind='plan_frontiers',policy=policy)])
        self.assertEqual(r['counts']['source_witnessed'],0);self.assertEqual(r['records'][0]['reason'],'external_native_provider_rejected');self.assertIsNone(r['named_source_evidence'])
    def test_external_policy_is_replayed_on_current_graph_without_rewriting_template(self):
        f=self.fixture();origin=dict(source_sha256=f.source,graph_sha256='old-graph',members=[dict(text_handle=f.text.dxf.handle)]);before=copy.deepcopy(origin)
        row=dict(native_name_evidence=dict(text_handle=f.text.dxf.handle),identifier='CHWS1',system='supply',node_id='RIF1',floor=1,local_nominal_mm_observed=450)
        with patch('batch_native_named_interfaces.external_plan_collect',return_value=dict(records=[row]))as native:
            r=self.read(f,external_templates=[dict(kind='plan_frontiers',policy=origin)])
        self.assertEqual(native.call_args.args[2]['graph_sha256'],f.hash);self.assertEqual(origin,before);self.assertEqual(r['records'][0]['role'],'external_plan_frontier');self.assertEqual(r['whole_edge_DN_assigned'],0)
    def test_wrong_source_or_ambiguous_leader_stays_closed(self):
        f=self.fixture();f.graph['metadata']['source_sha256']='changed'
        with self.assertRaises(ValueError):self.read(f)
        f=self.fixture();f.doc.modelspace().add_line((10,10),(25,5),dxfattribs=dict(layer='ANNOT'));r=self.read(f);self.assertEqual(r['counts']['source_witnessed'],0);self.assertEqual(r['counts']['pending'],1)
if __name__=='__main__':unittest.main()
