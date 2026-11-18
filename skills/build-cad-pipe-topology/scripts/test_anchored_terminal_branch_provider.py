import copy,unittest
from anchored_terminal_branch_provider import adopt_provider
class Provider(unittest.TestCase):
    def data(self):
        old=dict(records=[dict(edge_id='X',classification='mixed_horizontal_vertical',has_existing_correspondence=False,correspondence_observations=[])],counts={},ordinary_junction_mappings={'3':{'P':'A'}},member_domain_observations=[{'old':'member'}],current_component_inventory={'instances':1574},current_horizontal_frontier={'pure_horizontal_complete':228},remaining_horizontal_attributes=[{'edge_id':'H'}],all_current_vertical_DN_domains=[{'old':'vertical'}])
        r=dict(axis_edge_id='X',mapping_id='M',plan_edge_id='B',floor=3,plan_horizontal_projection={'value_mm':1234})
        values=[dict(edge_id='X',values=dict(anchored_branch_mapping_id='M',anchored_branch_plan_edge='B',anchored_branch_plan_pipe_XY_mm=1234))]
        return old,dict(records=[r]),values
    def test_adoption_retains_horizontal_vertical_components_and_namespaces(self):
        old,p,v=self.data();before=copy.deepcopy(old);new=adopt_provider(old,p,v)
        self.assertEqual(old,before);self.assertEqual(new['counts']['existing_correspondence_edges'],1);self.assertEqual(new['counts']['mixed_edges_without_any_correspondence'],0)
        self.assertEqual(new['ordinary_junction_mappings'],old['ordinary_junction_mappings']);self.assertFalse(new['records'][0]['correspondence_observations'][0]['remote_equipment_identity_inferred'])
    def test_source_only_or_existing_branch_cannot_be_counted(self):
        old,p,v=self.data();v[0]['values']={}
        with self.assertRaisesRegex(ValueError,'actual viewer'):adopt_provider(old,p,v)
        old,p,v=self.data();old['records'][0]['has_existing_correspondence']=True
        with self.assertRaisesRegex(ValueError,'old drawing'):adopt_provider(old,p,v)
if __name__=='__main__':unittest.main()
