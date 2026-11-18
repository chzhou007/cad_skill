import copy,unittest
import test_native_user_circle_endpoint_rays as source_fixture
import test_full_plan_DN_inheritance as ordinary_fixture
from native_user_circle_endpoint_rays import collect
from full_plan_DN_inheritance import infer as previous_infer
from source_main_DN_continuity import infer,BASIS


class Tests(unittest.TestCase):
    def native_corner(self,angle=0,mirror=1):
        fixture=source_fixture.Tests();self.addCleanup(fixture.doCleanups)
        doc,graph,nid,parents,review=fixture.fixture(angle,mirror)
        proof=collect(doc,graph,nid,'S','G',parents,review)
        record=graph['userConfirmedCircleJunctionRepair']['records'][0]
        return graph,nid,proof,record

    def run_case(self,graph,nid,proof,seeds):
        return infer(graph,[dict(edge_id=e,nominal_mm=v,evidence_id='explicit:'+e)for e,v in seeds],
            {e['edge_id']for e in graph['edges']},{nid:proof},'S','G')

    def test_native_turning_main200_branch80_does_not_create_a_false_conflict(self):
        for angle,mirror in[(0,1),(37,1),(90,1),(180,-1),(270,-1)]:
            graph,nid,proof,record=self.native_corner(angle,mirror);before=copy.deepcopy(graph)
            result=self.run_case(graph,nid,proof,[('M',200),('BR',80)])
            values={r['edge_id']:r['nominal_mm']for r in result['records']}
            self.assertEqual([values[e]for e in record['main_child_edges']],[200,200]);self.assertEqual(values['BR'],80)
            self.assertEqual(result['roles'][nid]['role_basis'],BASIS)
            self.assertEqual(result['roles'][nid]['branch'],'BR');self.assertEqual(graph,before)
            self.assertFalse(result['native_ray_directions_or_graph_geometry_changed'])

    def test_reproduces_old_false_conflict_and_branch_backflow_before_fix(self):
        graph,nid,proof,record=self.native_corner();scope={e['edge_id']for e in graph['edges']}
        seed=lambda e,v:dict(edge_id=e,nominal_mm=v,evidence_id='explicit:'+e)
        old=previous_infer(graph,[seed('M',200),seed('BR',80)],scope,{nid:proof},'S','G')
        other=next(e for e in record['main_child_edges']if e!='M')
        self.assertEqual(next(r for r in old['records']if r['edge_id']==other)['status'],'conflict')
        fixed=self.run_case(graph,nid,proof,[('BR',80)]);values={r['edge_id']:r['nominal_mm']for r in fixed['records']}
        self.assertIsNone(values['M']);self.assertIsNone(values[other]);self.assertEqual(values['BR'],80)

    def test_explicit_changed_main_DN_still_forms_a_boundary(self):
        graph,nid,proof,record=self.native_corner();other=next(e for e in record['main_child_edges']if e!='M')
        result=self.run_case(graph,nid,proof,[('M',200),(other,300),('BR',80)])
        values={r['edge_id']:r['nominal_mm']for r in result['records']}
        self.assertEqual(values,{'BR':80,'M':200,other:300})

    def test_stale_original_main_and_rim_branch_contracts_fail(self):
        for mode in('root','main_identity','center_scope','rim_scope','parent','branch','screen'):
            graph,nid,proof,record=self.native_corner()
            if mode=='root':graph.pop('userConfirmedCircleJunctionRepair')
            elif mode=='main_identity':record['main_child_edges']=['M','BR']
            elif mode=='center_scope':next(r for r in proof['junctions'][0]['source_rays']if r['edge_id']=='M')['scope']='other'
            elif mode=='rim_scope':next(r for r in proof['junctions'][0]['source_rays']if r['edge_id']=='BR')['scope']='confirmed_native_circle_center_LINE_endpoint'
            elif mode=='parent':proof['original_review']['original_graph_sha256']='OTHER'
            elif mode=='branch':record['branch_edge']='M'
            else:proof['original_review']['native_screen_sha256']='OTHER'
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.run_case(graph,nid,proof,[('M',200),('BR',80)])

    def test_ordinary_native_geometric_T_results_remain_exactly_unchanged(self):
        graph,junctions=ordinary_fixture.fixture();seeds=[dict(edge_id='A',nominal_mm=300,evidence_id='source:A'),dict(edge_id='C',nominal_mm=80,evidence_id='source:C')]
        old=previous_infer(graph,seeds,{'A','B','C'},junctions,'s','g');new=infer(graph,seeds,{'A','B','C'},junctions,'s','g')
        self.assertEqual(new['native_main_continuity_nodes'],[])
        for key,value in old.items():self.assertEqual(new[key],value)


if __name__=='__main__':unittest.main()
