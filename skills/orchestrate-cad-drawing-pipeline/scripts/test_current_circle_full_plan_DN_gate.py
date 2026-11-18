import unittest
from test_full_plan_DN_gate import fixture
from current_circle_full_plan_DN_gate import check


def current_fixture():
    data = fixture()
    data.update(previous_mode=data['mode'], mode='complete_local_plan_native_DN_current_circle_main_lineage_v3',
        historical_native_implementations_or_globals_changed=False)
    data['local_parent_replay']['1']['graph_sha256']='G'
    result=data['floors']['1']
    result.update(source_sha256='S', roles={'T':{}}, source_T_exceptions={}, current_circle_lineage_nodes=['T'],
        current_circle_lineage_evidence={'T': dict(graph_sha256='G',source_sha256='S',graph_mutated=False,
            physical_values_assigned=0,historical_reader_or_globals_changed=False,current_main_lineage=[{'kind':'source_bound_main_split'}])})
    return data


class Tests(unittest.TestCase):
    def test_complete_current_source_evidence_keeps_conflicts_and_HIL_pending(self):
        report=check(current_fixture())
        self.assertEqual(report['current_circle_lineage_nodes'],{'1':['T']})
        self.assertEqual(report['conflicting_DN_edges'],1)
        self.assertFalse(report['human_accepted'])

    def test_inventories_stale_hashes_and_false_promotions_fail(self):
        for mode in ('missing_role','exception','graph','source','mutation','metric','lineage','nodes'):
            data=current_fixture();result=data['floors']['1'];proof=result['current_circle_lineage_evidence']['T']
            if mode=='missing_role':result['roles']={}
            elif mode=='exception':result['source_T_exceptions']['T']='native ambiguity'
            elif mode=='graph':proof['graph_sha256']='OLD'
            elif mode=='source':proof['source_sha256']='OTHER'
            elif mode=='mutation':proof['graph_mutated']=True
            elif mode=='metric':proof['physical_values_assigned']=1
            elif mode=='lineage':proof['current_main_lineage']=[]
            else:result['current_circle_lineage_nodes']=[]
            with self.subTest(mode=mode),self.assertRaises(ValueError):check(data)


if __name__=='__main__':unittest.main()
