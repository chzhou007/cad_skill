import copy,math,unittest
from through_source_DN_inheritance import infer

def fixture(angle=0,mirror=False):
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    def point(x,y):
        if mirror:x=-x
        return [c*x-s*y,s*x+c*y]
    nodes=[dict(node_id=k,node_type='tee' if k=='T' else 'virtual_equipment',x=p[0],y=p[1],floor=1) for k,p in [('T',point(0,0)),('L',point(-10,0)),('R',point(10,0)),('B',point(0,10))]]
    edges=[dict(edge_id=k,start_node_id='T',end_node_id=k,system='supply',attribute_paths=[[point(0,0),p]]) for k,p in [('L',point(-10,0)),('R',point(10,0)),('B',point(0,10))]]
    rays=[dict(edge_id=k,direction=point(x,y)) for k,x,y in [('L',-1,0),('R',1,0),('B',0,1)]]
    proof=dict(source_sha256='S',graph_sha256='G',graph_mutated=False,junctions=[dict(node_id='T',position=point(0,0),source_rays=rays)])
    return dict(nodes=nodes,edges=edges),{'T':proof}
def seed(edge,value,h=None):return dict(edge_id=edge,nominal_mm=value,evidence_id=h or 'source:'+edge)
class Tests(unittest.TestCase):
    def test_main_through_inheritance_and_branch_override_survive_rotation_mirror(self):
        for angle,mirror in [(0,False),(90,False),(180,True),(270,True)]:
            with self.subTest(angle=angle,mirror=mirror):
                graph,junctions=fixture(angle,mirror);before=copy.deepcopy(graph)
                result=infer(graph,[seed('L',200),seed('B',80)],{'L','R','B'},junctions,'S','G');rows={r['edge_id']:r for r in result['records']}
                self.assertEqual([rows[k]['nominal_mm'] for k in ['L','R','B']],[200,200,80]);self.assertEqual(graph,before)
                self.assertEqual(rows['R']['lineage'][0]['evidence'][0]['through_T_ids'],['T'])
    def test_branch_only_seed_does_not_create_main_or_branch_default(self):
        graph,j=fixture();rows={r['edge_id']:r for r in infer(graph,[seed('B',80)],{'L','R','B'},j,'S','G')['records']}
        self.assertIsNone(rows['L']['nominal_mm']);self.assertIsNone(rows['R']['nominal_mm']);self.assertEqual(rows['B']['nominal_mm'],80)
    def test_direct_change_boundary_and_same_value_repeated_annotations(self):
        graph,j=fixture();result=infer(graph,[seed('L',200),seed('R',100),seed('L',200,'source:second')],{'L','R','B'},j,'S','G')
        self.assertEqual({r['edge_id']:r['nominal_mm'] for r in result['records']},{'B':None,'L':200,'R':100})
        with self.assertRaisesRegex(ValueError,'subdivision'):infer(graph,[seed('L',200),seed('L',100,'source:second')],{'L','R','B'},j,'S','G')
    def test_crossing_wrong_system_hash_or_missing_native_ray_cannot_propagate(self):
        for case in ('crossing','system','hash','ray','position','direction'):
            with self.subTest(case=case):
                graph,j=fixture()
                if case=='crossing':graph['edges'].append(dict(graph['edges'][0],edge_id='EXTRA'))
                elif case=='system':graph['edges'][0]['system']='return'
                elif case=='hash':j['T']['graph_sha256']='old'
                elif case=='ray':j['T']['junctions'][0]['source_rays'].pop()
                elif case=='position':j['T']['junctions'][0]['position']=[2,2]
                else:j['T']['junctions'][0]['source_rays'][0]['direction']=[0,0]
                with self.assertRaises(ValueError):infer(graph,[seed('L',200)],{'L','R','B'},j,'S','G')
if __name__=='__main__':unittest.main()
