import unittest
from test_main_continuity_full_plan_DN_gate import fixture as previous_fixture
from local_detail_full_plan_DN_gate import check

def fixture():
    data=previous_fixture();data.update(previous_main_continuity_mode=data['mode'],mode='complete_local_plan_native_DN_unowned_detail_T_v7')
    result=data['floors']['1'];proof=dict(status='native_local_detail_circle_T_replayed_without_equipment_owner',equipment_ownership_inferred=False,main_detail_correspondence_inferred=False,physical_ports_verified=False,physical_length_mm=None,graph_mutated=False,human_accepted=False,source_view_domain='detail_drawing_only_not_plan_metric_proof')
    result['native_local_detail_T_evidence']={'D':proof};result['native_local_detail_T_nodes']=['D'];result['roles']['D']=dict(source_T_proof=proof)
    return data

class Tests(unittest.TestCase):
    def test_local_native_T_does_not_require_or_imply_equipment_identity(self):
        report=check(fixture());self.assertEqual(report['native_local_detail_T_nodes'],{'1':['D']});self.assertFalse(report['hil_ready']);self.assertFalse(report['human_accepted'])

    def test_missing_proof_and_semantic_promotions_fail(self):
        for mode in('inventory','role','owner','alias','port','metric','source_domain'):
            data=fixture();result=data['floors']['1'];proof=result['native_local_detail_T_evidence']['D']
            if mode=='inventory':result['native_local_detail_T_nodes']=[]
            elif mode=='role':result['roles']['D']={}
            elif mode=='owner':proof['equipment_ownership_inferred']=True
            elif mode=='alias':proof['main_detail_correspondence_inferred']=True
            elif mode=='port':proof['physical_ports_verified']=True
            elif mode=='metric':proof['physical_length_mm']=0
            else:proof['source_view_domain']='measured_floor_plan'
            with self.subTest(mode=mode),self.assertRaises(ValueError):check(data)

if __name__=='__main__':unittest.main()
