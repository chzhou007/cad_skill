import copy,unittest
from test_native_confirmed_equipment_pair_circle_evidence import case
from crossview_equipment_branch_inventory import native_tee,inspect_branch

class ConfirmedPairInventoryEntryTests(unittest.TestCase):
    def test_both_services_enter_existing_inventory_after_original_reconstruction(self):
        doc,graph=case(z=True);before=copy.deepcopy(graph)
        for service in ('supply','return'):
            evidence=inspect_branch(doc,graph,'device',service,dict(source_sha256='S',graph_sha256='CURRENT',inventory_sha256='I'),'plan',[])
            self.assertTrue(evidence['ready_for_mapping_comparison'],evidence.get('reason'))
            self.assertEqual(evidence['junction_evidence']['status'],'native_confirmed_equipment_pair_circle_replayed_parent_verification_required')
        self.assertEqual(graph,before)

    def test_stale_root_stays_explicitly_pending_instead_of_becoming_a_plain_T(self):
        doc,graph=case();graph['confirmedEquipmentPairReconstruction']['source_sha256']='OTHER'
        evidence=inspect_branch(doc,graph,'device','supply',dict(source_sha256='S',graph_sha256='CURRENT',inventory_sha256='I'),'plan',[])
        self.assertFalse(evidence['ready_for_mapping_comparison']);self.assertEqual(evidence['status'],'source_check_pending')
        self.assertIn('source/root',evidence['reason'])

if __name__=='__main__':unittest.main()
