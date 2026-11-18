import copy,unittest
from contact_owner_provider_inventory import inherit
from alias_aware_provider_inventory import COMPLETE_FIELDS

class Tests(unittest.TestCase):
    def fixture(self):
        records=[dict(edge_id=e,classification='horizontal_only',has_existing_correspondence=e=='OLD',correspondence_observations=[dict(provider='old')]if e=='OLD'else[])for e in ('OLD','NEW','WAIT')]
        original=dict(records=records,ordinary_junction_mappings={'3':{'P':'A'}},member_domain_observations=[dict(domain='member',identity='keep')],remaining_horizontal_attributes=[dict(edge_id=e,floor=3,next_scope='unmatched')for e in ('NEW','WAIT')],current_component_inventory=dict(native_inventory='old'),counts={},current_horizontal_frontier={})
        application=dict(axis_edge_id='NEW',plan_edge_id='PN',mapping_id='MN',floor=3,nominal_mm=250.)
        proof=dict(complete_current_parent_replayed=True,native_owner_inventory_replayed=True,all_affected_old_scopes_requalified=True,pipe_graph_restoration_exact=True,human_accepted=False,floor=3,attribute_records=[application],source_batch=dict(records=[dict(iso_edges=['NEW'],mapping_id='MN')],native_bounded_batch=dict(new_junction_mapping={'Q':'B'})),inputs=dict(native_owner_proof='new'),rendered_graph_sha256='c'*64,counts=dict(output_components=10,added_components=1,reassigned_components=2),existing_scope_requalification=dict(requalified_old_axis_edges=['OLD']))
        values=[dict(edge_id='OLD',values=dict(diameter_nominal_mm=80,**{COMPLETE_FIELDS[0]:10})),dict(edge_id='NEW',values=dict(contact_owner_mapping_id='MN',contact_owner_plan_DN_mm=250.,contact_owner_complete_centerline_mm='')),dict(edge_id='WAIT',values={})]
        source=dict(records=[dict(status='no_unique_graph_owner',source_handle='UNKNOWN')],inputs=dict(graph='graph'))
        return original,proof,values,source
    def test_namespace_preservation_unknown_sources_and_mapped_incomplete_length(self):
        args=self.fixture();before=copy.deepcopy(args);result=inherit(*args)
        self.assertEqual(args,before);self.assertEqual(result['counts']['existing_correspondence_edges'],2);self.assertEqual(result['member_domain_observations'],args[0]['member_domain_observations']);self.assertEqual(result['counts']['native_component_ownership_unresolved'],1)
        pending=next(row for row in result['remaining_horizontal_attributes']if row['edge_id']=='NEW');self.assertEqual(pending['next_scope'],'known_contact_owner_plan_length_incomplete');self.assertFalse(pending['complete_centerline'])
    def test_ignored_native_requalification_or_competing_writer_or_anchor_is_blocked(self):
        for kind in ('scope','writer','anchor'):
            args=self.fixture()
            if kind=='scope':args[1]['all_affected_old_scopes_requalified']=False
            elif kind=='writer':args[0]['records'][1]['has_existing_correspondence']=True
            else:args[1]['source_batch']['native_bounded_batch']['new_junction_mapping']={'Q':'A'}
            with self.subTest(kind=kind),self.assertRaises(ValueError):inherit(*args)

if __name__=='__main__':unittest.main()
