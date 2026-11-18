import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
import ezdxf
from native_line_path_evidence import LAYERS
from anchor_bounded_main_paths import corridors,discover,prove,apply

def fixture(prefix,iso=False):
    positions={'A':(0,0),'U':(100,100)if iso else(0,100),'V':(300,100),'B':(400,0)if iso else(300,0),
               'X':(0,100)if iso else(-100,100),'Y':(400,100),'A1':(-100,0),'A2':(-100,100)if iso else(100,0),'B1':(500,0)if iso else(200,0),'B2':(500,100)if iso else(400,0)}
    nodes=[dict(node_id=prefix+n,node_type='tee'if n in'AUVB'else'unknown_terminal',floor=2,system='supply',x=p[0],y=p[1])for n,p in positions.items()]
    doc=ezdxf.new();edges=[]
    for n,(a,b)in enumerate([('A','U'),('U','V'),('V','B'),('U','X'),('V','Y'),('A','A1'),('A','A2'),('B','B1'),('B','B2')]):
        line=doc.modelspace().add_line(positions[a],positions[b],dxfattribs={'layer':LAYERS['supply']})
        edges.append(dict(edge_id=prefix+str(n),start_node_id=prefix+a,end_node_id=prefix+b,system='supply',floor_start=2,floor_end=2,attribute_paths=[[list(positions[a]),list(positions[b])]],source_handles=[line.dxf.handle]))
    rows=[dict(edge_id=prefix+str(i),equipment_type='球阀'if iso else'ball_valve')for i,count in enumerate([1,2,1])for _ in range(count)]
    return doc,dict(nodes=nodes,edges=edges),rows

class Tests(unittest.TestCase):
    def fixture(self):
        p,pg,pc=fixture('P');a,ag,ac=fixture('I',True)
        return dict(plan=p,iso=a),dict(plan=pg,iso=ag),dict(junction_mapping={'PA':'IA','PB':'IB'},records=[]),dict(plan=pc,iso=ac)
    def test_bent_route_with_offpath_arms_native_proof_and_independent_anchors(self):
        docs,graphs,parent,components=self.fixture();before=copy.deepcopy(graphs)
        hashes={v:dict(source_sha256='S',graph_sha256='G')for v in graphs}
        result=apply(docs,graphs,parent,2,components,hashes,[0,45,135])
        self.assertEqual(result['counts'],dict(source_checked_groups=1,unique_new_axis_edges=3,new_junctions=2))
        self.assertEqual(result['new_junction_mapping'],{'PU':'IU','PV':'IV'})
        self.assertEqual(graphs,before);self.assertFalse(result['off_path_branch_correspondence_assigned']);self.assertFalse(result['DN_used_for_matching'])
    def test_components_are_guard_not_label_or_dn_evidence(self):
        _,graphs,parent,components=self.fixture()
        components['iso'].pop();good,pending=discover(graphs,parent['junction_mapping'],[],2,components)
        self.assertFalse(good);self.assertEqual(pending[0]['reason'],'per_interval_component_profiles_differ')
    def test_prior_writer_cannot_be_removed_to_manufacture_a_route(self):
        _,graphs,parent,components=self.fixture();parent['records']=[dict(plan_edges=['P1'],iso_edges=['I1'])]
        good,pending=discover(graphs,parent['junction_mapping'],parent['records'],2,components)
        self.assertFalse(good);self.assertEqual(pending[0]['reason'],'prior_path_writer_present')
    def test_parallel_cycle_wrong_system_floor_and_review_are_not_eligible(self):
        for mode in('parallel','system','floor','review'):
            _,graphs,parent,components=self.fixture();g=graphs['iso']
            if mode=='parallel':g['edges'].append(dict(g['edges'][1],edge_id='EXTRA'))
            elif mode=='system':g['edges'][1]['system']='return'
            elif mode=='floor':next(n for n in g['nodes']if n['node_id']=='IU')['floor']=3
            else:next(n for n in g['nodes']if n['node_id']=='IU')['review_required']=True
            self.assertFalse(discover(graphs,parent['junction_mapping'],[],2,components)[0],mode)
    def test_missing_native_ray_is_not_promoted_to_mapped(self):
        docs,graphs,parent,components=self.fixture();docs['plan'].modelspace().delete_entity(docs['plan'].entitydb[graphs['plan']['edges'][3]['source_handles'][0]])
        result=apply(docs,graphs,parent,2,components,{v:dict(source_sha256='S',graph_sha256='G')for v in graphs},[0,45,135])
        self.assertFalse(result['records']);self.assertEqual(result['pending'][0]['reason'],'native_bounded_path_check_failed')
    def test_reversed_anchor_orientation_keeps_same_interval_identity(self):
        _,graphs,parent,components=self.fixture();parent['junction_mapping']={'PA':'IB','PB':'IA'}
        # Equal symmetric component profiles permit this candidate, but endpoint
        # identities must remain explicit; no nearest coordinate fixes direction.
        rows,_=discover(graphs,parent['junction_mapping'],[],2,components)
        self.assertEqual(rows[0]['iso']['nodes'],['IB','IV','IU','IA'])
    def test_known_junction_is_a_boundary_not_an_internal_path_vertex(self):
        _,graphs,parent,components=self.fixture();parent['junction_mapping']['PU']='IU'
        rows,_=discover(graphs,parent['junction_mapping'],[],2,components)
        self.assertTrue(rows)
        self.assertTrue(all(not set(r['plan']['nodes'][1:-1])&set(parent['junction_mapping'])for r in rows))
    def test_duplicate_anchor_identity_is_an_implementation_error(self):
        _,graphs,parent,components=self.fixture()
        with self.assertRaisesRegex(ValueError,'collapse'):discover(graphs,{'PA':'IA','PB':'IA'},[],2,components)
    def test_cycle_through_unknown_Ts_keeps_every_alternative(self):
        _,graphs,parent,components=self.fixture();g=graphs['plan']
        # Keep all four unknown nodes degree-three: U-X-Y-V and U-V form a ring.
        for n in g['nodes']:
            if n['node_id']in('PX','PY'):n['node_type']='tee'
        for i,(a,b)in enumerate([('PX','PY'),('PX','PA1'),('PY','PB1')]):
            g['edges'].append(dict(edge_id='CYCLE'+str(i),start_node_id=a,end_node_id=b,system='supply',floor_start=2,floor_end=2,attribute_paths=[[[0,0],[1,1]]]))
        self.assertFalse(corridors(g,parent['junction_mapping'],2))

if __name__=='__main__':unittest.main()
