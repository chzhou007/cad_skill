import copy, math, unittest
from reviewed_ring_main_partition import declared_values, add_partition_seeds
from projected_circle_plan_DN import infer


def fixture(angle=0, mirror=1, branch_override=False):
    turn = lambda p: [mirror * (p[0] * math.cos(angle) - p[1] * math.sin(angle)),
                      p[0] * math.sin(angle) + p[1] * math.cos(angle)]
    nodes=[]; edges=[]; proofs={}; seeds=[]; systems={}
    for system, xoffset in [('supply',0),('return',100)]:
        positions={'T':(0,0),'U':(0,10),'L':(0,-10),'F':(10,0),
                   'UA':(0,20),'UB':(10,10),'LA':(0,-20),'LB':(10,-10)}
        source=[('UP','T','U'),('LOW','T','L'),('FEED','T','F'),('UPPER','U','UA'),
                ('BRANCH_U','U','UB'),('LOWER','L','LA'),('BRANCH_L','L','LB')]
        names={k:system+':'+k for k in positions}
        for name,p in positions.items():
            q=turn((p[0]+xoffset,p[1]));nodes.append(dict(node_id=names[name],
                node_type='tee'if name in ('T','U','L')else'virtual_equipment',
                system=system,floor=2,x=q[0],y=q[1]))
        for eid,a,b in source:
            points=[turn((positions[n][0]+xoffset,positions[n][1]))for n in (a,b)]
            edges.append(dict(edge_id=system+':'+eid,start_node_id=names[a],end_node_id=names[b],
                system=system,attribute_paths=[points]))
        for nid in ('T','U','L'):
            n=next(n for n in nodes if n['node_id']==names[nid]);rays=[]
            for edge in edges:
                if n['node_id']not in (edge['start_node_id'],edge['end_node_id']):continue
                other=edge['end_node_id']if edge['start_node_id']==n['node_id']else edge['start_node_id']
                peer=next(z for z in nodes if z['node_id']==other)
                rays.append(dict(edge_id=edge['edge_id'],direction=[peer['x']-n['x'],peer['y']-n['y']]))
            proofs[n['node_id']]=dict(source_sha256='s',graph_sha256='g',graph_mutated=False,
                junctions=[dict(node_id=n['node_id'],position=[n['x'],n['y']],source_rays=rays)])
        for eid,value in [('UPPER',200),('LOWER',300),('FEED',450)]:
            seeds.append(dict(edge_id=system+':'+eid,nominal_mm=value,evidence_id='source:'+system+eid))
        if branch_override:seeds.append(dict(edge_id=system+':BRANCH_U',nominal_mm=80,evidence_id='source:branch-'+system))
        systems[system]=dict(boundary_T=names['T'],upper_entry=system+':UP',lower_entry=system+':LOW',
            upper_edges=[system+':UP'],lower_edges=[system+':LOW'])
    graph=dict(nodes=nodes,edges=edges);eligible={e['edge_id']for e in edges}
    baseline=infer(graph,seeds,eligible,proofs,'s','g')
    baseline.update(direct_seed_evidence=seeds,native_current_T_evidence=proofs)
    policy=dict(scope_id='review',upper_direction_WCS=turn((0,1)),systems=systems)
    return graph,baseline,policy,eligible,proofs


class Tests(unittest.TestCase):
    def test_explicit_values_not_calculated_from_room_counts(self):
        message='两个立管之间，上面的环管承担一个包间，管径为200DN，下面承担两个包间，管径为300DN'
        self.assertEqual(declared_values(message),dict(upper=200,lower=300))
        self.assertEqual(declared_values(message.replace('一个包间','九个包间')),dict(upper=200,lower=300))
        with self.assertRaises(ValueError):declared_values('上面一个包间，下面两个包间')

    def test_real_T_partition_inherits_branches_with_rotations_mirrors_and_system_isolation(self):
        for angle in (0,.7,math.pi/2):
            for mirror in (1,-1):
                graph,baseline,policy,scope,proofs=fixture(angle,mirror);before=copy.deepcopy((graph,baseline,policy))
                seeds,selected=add_partition_seeds(graph,baseline,policy,dict(upper=200,lower=300))
                after=infer(graph,seeds,scope,proofs,'s','g');rows={r['edge_id']:r for r in after['records']}
                for system in ('supply','return'):
                    self.assertEqual([rows[system+':'+e]['nominal_mm']for e in ('UP','LOW','BRANCH_U','BRANCH_L','FEED')],[200,300,200,300,450])
                self.assertEqual(len(selected),4);self.assertEqual((graph,baseline,policy),before)

    def test_new_branch_label_is_a_barrier_and_does_not_seed_the_main(self):
        graph,baseline,policy,scope,proofs=fixture(branch_override=True)
        seeds,_=add_partition_seeds(graph,baseline,policy,dict(upper=200,lower=300))
        rows={r['edge_id']:r for r in infer(graph,seeds,scope,proofs,'s','g')['records']}
        self.assertEqual(rows['supply:BRANCH_U']['nominal_mm'],80)
        self.assertEqual(rows['supply:UP']['nominal_mm'],200)
        self.assertEqual(rows['return:LOW']['nominal_mm'],300)

    def test_wrong_arm_side_direct_caption_and_disconnected_scope_rejected(self):
        for kind in ('side','arm','direct','disconnected'):
            graph,baseline,policy,_,_=fixture()
            if kind=='side':policy['upper_direction_WCS']=[0,-1]
            elif kind=='arm':policy['systems']['supply']['upper_entry']='supply:FEED'
            elif kind=='direct':baseline['direct_seed_evidence'].append(dict(edge_id='supply:UP',nominal_mm=200,evidence_id='source:already'))
            else:policy['systems']['supply']['upper_edges'].append('return:UP')
            with self.subTest(kind=kind),self.assertRaises(ValueError):add_partition_seeds(graph,baseline,policy,dict(upper=200,lower=300))


if __name__=='__main__':unittest.main()
