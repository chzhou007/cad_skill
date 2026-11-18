import unittest
from unittest.mock import patch
from pipeline import validate_compound_carrier_atom_origins,validate_native_balancing_valves,reconstruct_compound_carrier_atom_origins,reconstruct_native_balancing_valves
from compound_carrier_atom_origins import MODE as ORIGIN
from native_balancing_valve_recovery import MODE as VALVE
from compound_riser_header_members import MODE as MEMBER
from pipeline import validate_compound_riser_header_members

class Tests(unittest.TestCase):
    def test_origin_validation_keeps_physical_assignment_separate(self):
        r=dict(mode=ORIGIN,source_or_graph_mutated=False,physical_members_assigned=0,DN_or_lengths_assigned=0,human_accepted=False,counts={})
        with patch('rebuild_compound_carrier_atom_origins.verify_output',return_value=r):self.assertEqual(validate_compound_carrier_atom_origins('native')['native_compound_atom_origins'],'passed')
        for k,v in [('physical_members_assigned',1),('DN_or_lengths_assigned',1),('source_or_graph_mutated',True),('human_accepted',True)]:
            with self.subTest(key=k),patch('rebuild_compound_carrier_atom_origins.verify_output',return_value=dict(r,**{k:v})),self.assertRaises(ValueError):validate_compound_carrier_atom_origins('native')
    def test_component_recovery_does_not_publish_or_invent_resistance(self):
        r=dict(mode=VALVE,prior_components_unchanged=True,source_graph_unchanged=True,resistance_parameters_assigned=0,published_graph_changed=False,human_accepted=False,counts=dict(prior_components=1),components=[dict(device_name='old'),dict(device_name='new')],added_components=[dict(device_name='new')])
        with patch('rebuild_native_balancing_valves.verify_output',return_value=r):self.assertEqual(validate_native_balancing_valves('native')['native_balancing_valves'],'passed')
        for k,v in [('prior_components_unchanged',False),('resistance_parameters_assigned',1),('published_graph_changed',True),('human_accepted',True)]:
            with self.subTest(key=k),patch('rebuild_native_balancing_valves.verify_output',return_value=dict(r,**{k:v})),self.assertRaises(ValueError):validate_native_balancing_valves('native')
    def test_reconstruction_calls_owners_and_native_validators(self):
        for kind,run in [('compound_carrier_atom_origins',reconstruct_compound_carrier_atom_origins),('native_balancing_valves',reconstruct_native_balancing_valves)]:
            with patch('rebuild_'+kind+'.produce')as p,patch('pipeline.validate_'+kind,return_value={'status':'pending'})as v:
                run('manifest','new');p.assert_called_once_with('manifest','new');v.assert_called_once_with('new')
    def test_rebuilt_member_graph_cannot_claim_unproved_terminal_or_gate_identity(self):
        row=dict(scoped_graph=dict(edges=[dict(component_ids=['a']),dict(component_ids=['b']),dict(component_ids=['c'])]),component_ids_conserved=['a','b','c'],gate_mapping_revalidation_required=True,lower_terminal_identity_selected=False)
        r=dict(mode=MEMBER,raw_graphs_unchanged=True,component_duplicated=False,whole_axis_values_assigned=0,human_accepted=False,records=[row],scoped_member_edges=3,conditional_interval_candidates=2,pending=[])
        with patch('rebuild_compound_riser_header_members.verify_output',return_value=r):self.assertEqual(validate_compound_riser_header_members('native')['scoped_member_edges'],3)
        for key,value in [('gate_mapping_revalidation_required',False),('lower_terminal_identity_selected',True),('component_ids_conserved',['a','b'])]:
            with self.subTest(key=key),patch('rebuild_compound_riser_header_members.verify_output',return_value=dict(r,records=[dict(row,**{key:value})])),self.assertRaises(ValueError):validate_compound_riser_header_members('native')
if __name__=='__main__':unittest.main()
