import copy,unittest
from test_reconstruct_sideview_equipment_ownership import case,POLICY
from reconstruct_sideview_equipment_ownership import apply
from crossview_equipment_branch_inventory import inspect_branch

class SideviewOwnerInventoryEntryTests(unittest.TestCase):
    def test_existing_entry_handles_both_original_endpoint_roles(self):
        for boundary in (False,True):
            doc,g,e=case(boundary=boundary);out,_=apply(g,e,POLICY,'S','CURRENT');before=copy.deepcopy(out)
            for service in ('supply','return'):
                result=inspect_branch(doc,out,'EQ',service,dict(source_sha256='S',graph_sha256='DERIVED',inventory_sha256='I'),'plan',[])
                self.assertTrue(result['ready_for_mapping_comparison'],result.get('reason'))
                self.assertEqual(result['logical_ownership_basis'],'source_calibrated_equipment_through_confirmed_sideview')
                self.assertEqual(result['source_view_domain'],'detail_drawing_only_not_plan_metric_proof')
                self.assertFalse(result['physical_ports_verified'])
            self.assertEqual(out,before)

    def test_stale_alias_stays_in_source_queue_instead_of_falling_back(self):
        doc,g,e=case();out,_=apply(g,e,POLICY,'S','CURRENT');out['sourceSideviewEquipmentOwnership']['node_aliases'].clear()
        result=inspect_branch(doc,out,'EQ','supply',dict(source_sha256='S',graph_sha256='DERIVED',inventory_sha256='I'),'plan',[])
        self.assertFalse(result['ready_for_mapping_comparison']);self.assertEqual(result['status'],'source_check_pending')

if __name__=='__main__':unittest.main()
