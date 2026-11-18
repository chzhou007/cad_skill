import copy,json,tempfile,unittest
from pathlib import Path
from refresh_nonnode_boundary_branches import delta,provider_from,FIELDS

class NonNodePublicationTests(unittest.TestCase):
    def fixture(self):
        r=dict(axis_edge_id='M',plan_edge_id='P',mapping_id='CAP',floor=3)
        proof=dict(records=[r]);before=[dict(edge_id=e,values=dict(diameter_nominal_mm=100,length=None,vertical='11',source='old'))for e in ['M','R']];after=copy.deepcopy(before)
        after[0]['values'].update(boundary_branch_mapping_id='CAP',boundary_branch_plan_edge='P',boundary_branch_boundary_id='U',boundary_branch_axis_port='S',boundary_branch_scope='native',boundary_branch_evidence_json=json.dumps(r))
        return before,after,proof
    def test_only_drawing_context_is_added(self):
        before,after,proof=self.fixture();r=delta(before,after,proof)
        self.assertEqual(r['new_drawing_correspondences'],1);self.assertEqual(r['new_lengths'],0);self.assertEqual(r['new_whole_DN_values'],0)
    def test_prior_values_and_other_system_are_protected(self):
        before,after,proof=self.fixture()
        for i,key,value in [(0,'length',0),(0,'vertical','plan'),(0,'source','new'),(1,'boundary_branch_mapping_id','CAP')]:
            bad=copy.deepcopy(after);bad[i]['values'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):delta(before,bad,proof)
    def test_provider_has_one_new_context_without_anchor_or_other_port_changes(self):
        before,after,proof=self.fixture();prior=dict(records=[dict(edge_id=e,classification='mixed_horizontal_vertical',has_existing_correspondence=False,correspondence_observations=[])for e in ['M','R']],counts={},ordinary_junction_mappings={'3':{'T':'A'}},member_domain_observations=['old'],all_current_vertical_DN_domains=4,current_component_inventory={'instances':2},remaining_horizontal_attributes=[],current_horizontal_frontier={})
        original=copy.deepcopy(prior)
        with tempfile.TemporaryDirectory()as folder:
            p=Path(folder)/'proof';p.write_text('native',encoding='utf8');result=provider_from(prior,proof,after,dict(reviewed_uniform_subroute_DN={'records':[]}),p)
            with self.assertRaisesRegex(ValueError,'old branch writer'):provider_from(result,proof,after,dict(reviewed_uniform_subroute_DN={'records':[]}),p)
        self.assertEqual(prior,original);self.assertTrue(result['records'][0]['has_existing_correspondence']);self.assertFalse(result['records'][1]['has_existing_correspondence']);self.assertEqual(result['counts']['mixed_edges_without_any_correspondence'],1)
        for k in ['ordinary_junction_mappings','member_domain_observations','all_current_vertical_DN_domains','current_component_inventory']:self.assertEqual(result[k],prior[k])

if __name__=='__main__':unittest.main()
