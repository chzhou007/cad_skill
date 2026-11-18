import copy, unittest
from anchored_cycle_gate_matching import discover, cycle_blocks

def fixture(prefix, count, gates, system='supply', floor=2):
    nodes=[dict(node_id=prefix+str(i),node_type='tee',floor=floor,x=i*11,y=i*7)for i in range(count)]
    edges=[]
    def edge(a,b):
        edges.append(dict(edge_id=prefix+'e'+str(len(edges)),start_node_id=a,end_node_id=b,system=system))
    for i in range(count):edge(prefix+str(i),prefix+str((i+1)%count))
    anchors=set(gates.values())
    for anchor in sorted(anchors):nodes.append(dict(node_id=prefix+anchor,node_type='tee',floor=floor))
    for i in range(count):
        if i in gates:edge(prefix+str(i),prefix+gates[i])
        else:
            n=prefix+'leaf'+str(i);nodes.append(dict(node_id=n,node_type='virtual_equipment',floor=floor));edge(prefix+str(i),n)
    for anchor in sorted(anchors):
        degree=sum(prefix+anchor in(e['start_node_id'],e['end_node_id'])for e in edges)
        for k in range(3-degree):
            n=prefix+anchor+'outside'+str(k);nodes.append(dict(node_id=n,node_type='virtual_equipment',floor=floor));edge(prefix+anchor,n)
    return dict(nodes=nodes,edges=edges)

class CycleGateTests(unittest.TestCase):
    def views(self):
        return dict(plan=fixture('p',4,{0:'A',2:'B'}),iso=fixture('a',6,{1:'A',4:'B'}))
    def test_different_branch_counts_match_only_attachment_gates(self):
        g=self.views();before=copy.deepcopy(g);r=discover(g,{'pA':'aA','pB':'aB'},2)
        self.assertEqual(r['new_junction_mapping'],{'p0':'a1','p2':'a4'})
        self.assertEqual(len(r['groups']),1)
        self.assertFalse(r['groups'][0]['interior_branch_counts_equal'])
        self.assertFalse(r['interior_node_identities_assigned']);self.assertEqual(g,before)
    def test_rotation_mirror_and_DN_do_not_choose_identity(self):
        g=self.views()
        for node in g['iso']['nodes']:
            node.update(x=-node.get('y',0),y=-node.get('x',0),diameter_nominal_mm=999)
        for edge in g['plan']['edges']:edge['diameter_nominal_mm']=7
        r=discover(g,{'pA':'aA','pB':'aB'},2)
        self.assertEqual(r['new_junction_mapping'],{'p0':'a1','p2':'a4'})
    def test_one_anchor_is_insufficient(self):
        self.assertFalse(discover(self.views(),{'pA':'aA'},2)['new_junction_mapping'])
    def test_system_and_floor_do_not_mix(self):
        for change in ('system','floor'):
            g=self.views()
            if change=='system':
                for e in g['iso']['edges']:e['system']='return'
            else:
                for n in g['iso']['nodes']:n['floor']=3
            self.assertFalse(discover(g,{'pA':'aA','pB':'aB'},2)['new_junction_mapping'])
    def test_gap_or_unresolved_junction_does_not_close_cycle(self):
        for change in ('gap','review'):
            g=self.views()
            if change=='gap':g['plan']['edges'].pop(0)
            else:g['plan']['nodes'][1]['review_required']=True
            self.assertFalse(discover(g,{'pA':'aA','pB':'aB'},2)['new_junction_mapping'])
    def test_duplicate_gate_signature_not_paired_by_order(self):
        g=dict(plan=fixture('p',5,{0:'A',2:'A',3:'B'}),iso=fixture('a',6,{0:'A',2:'A',4:'B'}))
        r=discover(g,{'pA':'aA','pB':'aB'},2)
        self.assertEqual(r['new_junction_mapping'],{'p3':'a4'})
        self.assertTrue(any(p['reason']=='nonunique_cycle_gate_signature'for p in r['pending']))
    def test_parallel_two_edge_cycle_and_chorded_block_not_simple_cycle(self):
        self.assertEqual(cycle_blocks({'a':[('b','x'),('b','y')],'b':[('a','x'),('a','y')]}),[])
        adj={'a':[('b','ab'),('c','ac'),('d','ad')],'b':[('a','ab'),('c','bc')],
             'c':[('a','ac'),('b','bc'),('d','cd')],'d':[('a','ad'),('c','cd')]}
        self.assertEqual(cycle_blocks(adj),[])
    def test_anchor_identity_and_namespace_fail_closed(self):
        for mapping in ({'pA':'aA','pB':'aA'},{'MEMBER:pA':'aA','pB':'aB'}):
            with self.assertRaises(ValueError):discover(self.views(),mapping,2)

if __name__=='__main__':unittest.main()
