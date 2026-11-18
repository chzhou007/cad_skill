import copy,json,tempfile,unittest
from pathlib import Path
from refresh_plan_seeded_axis_branch_DN import retained_vertical_domains,delta,provider_from,CONTEXT,FIELDS

class PlanBranchDNPublicationTests(unittest.TestCase):
    def fixture(self):
        edge=dict(edge_id='E',system='supply',attribute_paths=[[[0,0],[0,-10],[20,-30],[21,-31]]])
        h=dict(edge_id='E',path_index=0,segment_index=1,scope_points=[[0,-10],[20,-30]])
        native=dict(nominal_mm=200,horizontal_segment_domains=[h],excluded_marker_display_segment=2)
        vertical=dict(edge_id='E',path_index=0,segment_index=0,scope_points=[[0,0],[0,-10]],nominal_mm=200,system='supply',axis_source_sha256='S',human_accepted=False)
        values=dict(diameter_nominal_mm=None,length=None,axis_rule_vertical_DN_segments_json=json.dumps([vertical]))
        return edge,native,vertical,values

    def test_whole_completion_requires_exact_vertical_source_domain_not_equal_DN_count(self):
        edge,native,vertical,values=self.fixture();retained,complete=retained_vertical_domains(edge,native,values,'S')
        self.assertTrue(complete);self.assertEqual(len(retained),1);self.assertFalse(retained[0]['new_vertical_value_assigned'])
        for defect in('absent','duplicate','other_segment','other_points','other_source','other_system','other_DN','accepted'):
            row=copy.deepcopy(vertical);rows=[row]
            if defect=='absent':rows=[]
            elif defect=='duplicate':rows.append(copy.deepcopy(row))
            elif defect=='other_segment':row['segment_index']=1
            elif defect=='other_points':row['scope_points']=[[0,0],[0,-9]]
            elif defect=='other_source':row['axis_source_sha256']='OTHER'
            elif defect=='other_system':row['system']='return'
            elif defect=='other_DN':row['nominal_mm']=80
            else:row['human_accepted']=True
            with self.subTest(defect=defect):self.assertFalse(retained_vertical_domains(edge,native,dict(values,axis_rule_vertical_DN_segments_json=json.dumps(rows)),'S')[1])

    def delta_fixture(self):
        record=dict(axis_edge_id='E',nominal_mm=200,whole_physical_DN_complete=True,horizontal_segment_domains=[{}])
        old=[dict(edge_id=e,values=dict(diameter_nominal_mm=None,diameter_text='',diameter_status='unknown',length=None,vertical='native11',mapping='unchanged'))for e in('E','R')]
        new=copy.deepcopy(old);new[0]['values'].update(diameter_nominal_mm=200,diameter_text='DN200',diameter_status='plan_and_native11',**{k:''for k in FIELDS})
        new[0]['values']['plan_branch_DN_domains_json']=json.dumps(record)
        return old,new,dict(records=[record]),{CONTEXT:dict(records=[record]),'reviewed_uniform_subroute_DN':dict(records=[])}

    def test_only_unknown_whole_DN_and_declared_evidence_are_adopted(self):
        old,new,proof,context=self.delta_fixture();r=delta(old,new,proof,context)
        self.assertEqual(r['new_whole_physical_DN_edges'],['E']);self.assertEqual(r['new_lengths'],0);self.assertEqual(r['new_vertical_values'],0)
        for i,key,value in[(0,'length',0),(0,'vertical','plan'),(0,'mapping','new'),(1,'diameter_nominal_mm',200),(1,'plan_branch_DN_T','T')]:
            bad=copy.deepcopy(new);bad[i]['values'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):delta(old,bad,proof,context)
        old[0]['values']['diameter_nominal_mm']=80
        with self.assertRaisesRegex(ValueError,'conflicts'):delta(old,new,proof,context)

    def test_incomplete_vertical_coverage_cannot_promote_whole_DN(self):
        old,new,proof,context=self.delta_fixture();context[CONTEXT]['records'][0]['whole_physical_DN_complete']=False
        new[0]['values']['plan_branch_DN_domains_json']=json.dumps(context[CONTEXT]['records'][0])
        with self.assertRaises(ValueError):delta(old,new,proof,context)

    def test_provider_keeps_individual_mappings_and_components_unchanged(self):
        old,new,proof,context=self.delta_fixture();prior=dict(records=[dict(edge_id=e,classification='mixed_horizontal_vertical',has_existing_correspondence=False)for e in('E','R')],counts={},ordinary_junction_mappings={},member_domain_observations=['old'],all_current_vertical_DN_domains=2,current_component_inventory={'instances':3},remaining_horizontal_attributes=[],current_horizontal_frontier={})
        before=copy.deepcopy(prior)
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'proof.json';path.write_text('native');result=provider_from(prior,proof,new,context,path)
        self.assertEqual(prior,before);self.assertEqual(result['counts']['current_effective_whole_DN_known'],1)
        for key in('records','ordinary_junction_mappings','member_domain_observations','all_current_vertical_DN_domains','current_component_inventory'):self.assertEqual(result[key],prior[key])
if __name__=='__main__':unittest.main()
