import copy,unittest
import test_native_exploded_endpoint_evidence as fixtures
from crossview_equipment_branch_inventory import inspect_branch
from crossview_equipment_branch_inventory_v2 import extend,UNSUPPORTED


class EndpointInventoryTests(unittest.TestCase):
    def setUp(self):
        self.f=fixtures.ExplodedEndpointEvidenceTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def data(self):
        f=self.f.f
        branch=inspect_branch(f.doc,f.g,'D','supply',f.h,'iso',f.inv)
        self.assertEqual(branch.get('reason'),UNSUPPORTED)
        ready=dict(ready_for_mapping_comparison=True,trace=dict(status='unique_graph_service_to_T',edges=['OTHER']))
        row=dict(equipment_id='D',floor=1,ready_for_mapping_comparison=False,
            views=dict(plan=dict(services=dict(supply=copy.deepcopy(ready),return_=copy.deepcopy(ready))),
                iso=dict(services=dict(supply=branch,return_=copy.deepcopy(ready)))))
        for view in row['views'].values():view['services']['return']=view['services'].pop('return_')
        previous=dict(equipment_id='PREVIOUS',floor=1,ready_for_mapping_comparison=True,
            views={v:dict(services={s:copy.deepcopy(ready) for s in ('supply','return')}) for v in ('plan','iso')})
        result=dict(status='source_comparison_inventory_not_mapping',records=[row,previous],
            counts=dict(equipment=2,ready_for_mapping_comparison=1),source_evidence_implementation_sha256={},
            local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False)
        return result,self.f.check()

    def test_real_native_chain_composes_with_inherited_T_and_coverage(self):
        result,proof=self.data();before=copy.deepcopy(result);graph=copy.deepcopy(self.f.f.g)
        upgraded=extend(result,proof)
        self.assertEqual(upgraded['counts'],dict(equipment=2,ready_for_mapping_comparison=2))
        self.assertEqual(len(upgraded['endpoint_reader_changes']),1)
        self.assertEqual(upgraded['records'][1],before['records'][1]);self.assertEqual(result,before);self.assertEqual(self.f.f.g,graph)
        self.assertFalse(upgraded['hil_ready']);self.assertEqual(upgraded['mapped_paths'],0)

    def test_unresolved_plan_still_blocks_equipment_even_when_axis_passes(self):
        result,proof=self.data();result['records'][0]['views']['plan']['services']['supply']['ready_for_mapping_comparison']=False
        upgraded=extend(result,proof)
        self.assertEqual(upgraded['counts']['ready_for_mapping_comparison'],1)
        self.assertTrue(upgraded['records'][0]['views']['iso']['services']['supply']['ready_for_mapping_comparison'])

    def test_other_defect_or_changed_T_or_coverage_cannot_be_bypassed(self):
        for mutation in ('reason','tee','coverage','owner','physical','accepted','duplicate'):
            with self.subTest(mutation=mutation):
                result,proof=self.data();branch=result['records'][0]['views']['iso']['services']['supply']
                if mutation=='reason':branch['reason']='actual native path gap'
                elif mutation=='tee':branch['junction_evidence']={}
                elif mutation=='coverage':branch['coverage']={}
                elif mutation=='owner':proof['records'][0]['equipment_id']='OTHER'
                elif mutation=='physical':proof['records'][0]['physical_port_verified']=True
                elif mutation=='accepted':proof['human_accepted']=True
                else:proof['records'].append(copy.deepcopy(proof['records'][0]))
                with self.assertRaises(ValueError):extend(result,proof)

    def test_unselected_service_and_previously_ready_records_remain_exact(self):
        result,proof=self.data();original=copy.deepcopy(result['records'][0]['views']['iso']['services']['return'])
        upgraded=extend(result,proof)
        self.assertEqual(upgraded['records'][0]['views']['iso']['services']['return'],original)
        self.assertEqual(upgraded['records'][1],result['records'][1])


if __name__=='__main__':unittest.main()
