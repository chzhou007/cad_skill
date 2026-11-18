import copy,math,unittest
from full_plan_DN_inheritance import infer


def fixture(angle=0,mirror=1):
    node=dict(node_id='T',node_type='tee',floor=1,x=0,y=0)
    specs=[('A',[-1,0]),('B',[1,0]),('C',[0,1])]
    turn=lambda p:[mirror*(p[0]*math.cos(angle)-p[1]*math.sin(angle)),p[0]*math.sin(angle)+p[1]*math.cos(angle)]
    nodes=[node];edges=[];rays=[]
    for eid,p in specs:
        q=turn(p);nodes.append(dict(node_id=eid,node_type='virtual_equipment',floor=1,x=q[0],y=q[1]))
        edges.append(dict(edge_id=eid,start_node_id='T',end_node_id=eid,system='supply',attribute_paths=[[[0,0],q]]))
        rays.append(dict(edge_id=eid,direction=q))
    proof=dict(source_sha256='s',graph_sha256='g',graph_mutated=False,junctions=[dict(node_id='T',position=[0,0],source_rays=rays)])
    return dict(nodes=nodes,edges=edges),{'T':proof}


class Tests(unittest.TestCase):
    def test_no_labels_no_checked_Ts_or_all_blocked_paths_are_unknown_not_a_batch_failure(self):
        graph,_=fixture()
        r=infer(graph,[],{'A','B','C'},{},'s','g')
        self.assertTrue(all(x['nominal_mm']is None for x in r['records']))
        self.assertEqual(infer(graph,[],set(),{},'s','g')['records'],[])
        r=infer(graph,[dict(edge_id='A',nominal_mm=80,evidence_id='native:a')],{'A','B','C'},{},'s','g')
        self.assertEqual([x['nominal_mm']for x in r['records']],[80,None,None])
    def run_case(self,seeds,angle=0,mirror=1):
        graph,proofs=fixture(angle,mirror);before=copy.deepcopy(graph)
        result=infer(graph,[dict(edge_id=e,nominal_mm=v,evidence_id='source:'+e)for e,v in seeds],{'A','B','C'},proofs,'s','g')
        self.assertEqual(graph,before);return {r['edge_id']:r for r in result['records']}
    def test_main_seed_reaches_through_and_unlabelled_branch_in_rotated_mirrored_cases(self):
        for angle in [0,.7,math.pi/2]:
            for mirror in [1,-1]:
                with self.subTest(angle=angle,mirror=mirror):
                    r=self.run_case([('A',200)],angle,mirror);self.assertEqual([r[e]['nominal_mm']for e in ['A','B','C']],[200,200,200])
                    self.assertEqual(r['C']['status'],'T_branch_inherited_plan_DN')
    def test_explicit_branch_value_overrides_without_backflow(self):
        r=self.run_case([('A',300),('C',80)])
        self.assertEqual([r[e]['nominal_mm']for e in ['A','B','C']],[300,300,80])
        r=self.run_case([('C',80)]);self.assertIsNone(r['A']['nominal_mm']);self.assertIsNone(r['B']['nominal_mm'])
    def test_conflicting_through_arms_keep_branch_unknown(self):
        r=self.run_case([('A',300),('B',200)]);self.assertIsNone(r['C']['nominal_mm']);self.assertEqual(r['C']['status'],'conflict')
        self.assertEqual([r['A']['nominal_mm'],r['B']['nominal_mm']],[300,200])
    def test_missing_source_ray_or_system_is_not_inferred(self):
        graph,proof=fixture();proof['T']['junctions'][0]['source_rays'].pop()
        with self.assertRaises(ValueError):infer(graph,[dict(edge_id='A',nominal_mm=200,evidence_id='a')],{'A','B','C'},proof,'s','g')
        graph,proof=fixture();graph['edges'][1]['system']='return'
        with self.assertRaises(ValueError):infer(graph,[dict(edge_id='A',nominal_mm=200,evidence_id='a')],{'A','B','C'},proof,'s','g')
    def test_unverified_arm_prevents_a_branch_default(self):
        graph,proof=fixture();r=infer(graph,[dict(edge_id='A',nominal_mm=200,evidence_id='a')],{'A','C'},proof,'s','g')
        self.assertIsNone(next(x for x in r['records']if x['edge_id']=='C')['nominal_mm'])
    def test_a_reviewed_segment_is_kept_inside_its_confirmed_bounds_not_exported_as_a_new_source_label(self):
        graph,proof=fixture();seeds=[dict(edge_id='A',nominal_mm=450,evidence_id='reviewed:A',scope_only=True),dict(edge_id='B',nominal_mm=200,evidence_id='source:B')]
        r=infer(graph,seeds,{'A','B','C'},proof,'s','g');rows={x['edge_id']:x for x in r['records']}
        self.assertEqual(rows['A']['nominal_mm'],450);self.assertEqual(rows['A']['status'],'reviewed_plan_DN_scope')
        self.assertEqual(rows['B']['nominal_mm'],200);self.assertIsNone(rows['C']['nominal_mm'])
    def test_explicit_annotation_along_a_branch_overrides_the_parent_main_default(self):
        graph,proof=fixture();graph['nodes']=[n for n in graph['nodes']if n['node_id']!='C']
        graph['nodes']+= [dict(node_id='T2',node_type='tee',floor=1,x=0,y=1),dict(node_id='D',node_type='virtual_equipment',floor=1,x=0,y=2),dict(node_id='E',node_type='virtual_equipment',floor=1,x=1,y=1)]
        graph['edges'][2]['end_node_id']='T2'
        graph['edges']+=[dict(edge_id='D',start_node_id='T2',end_node_id='D',system='supply',attribute_paths=[[[0,1],[0,2]]]),dict(edge_id='E',start_node_id='T2',end_node_id='E',system='supply',attribute_paths=[[[0,1],[1,1]]])]
        proof['T2']=dict(source_sha256='s',graph_sha256='g',graph_mutated=False,junctions=[dict(node_id='T2',position=[0,1],source_rays=[dict(edge_id=e,direction=d)for e,d in [('C',[0,-1]),('D',[0,1]),('E',[1,0])]])])
        seeds=[dict(edge_id=e,nominal_mm=v,evidence_id=e)for e,v in [('A',300),('D',200)]]
        r=infer(graph,seeds,{'A','B','C','D','E'},proof,'s','g');rows={x['edge_id']:x for x in r['records']}
        self.assertEqual(rows['A']['nominal_mm'],300);self.assertEqual(rows['D']['nominal_mm'],200)
        self.assertEqual(rows['C']['nominal_mm'],200);self.assertEqual(rows['E']['nominal_mm'],200)

if __name__=='__main__':unittest.main()
