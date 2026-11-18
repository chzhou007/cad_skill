import copy,unittest
import test_match_paired_service_crossview_paths as fixtures
from match_paired_service_crossview_paths import pair_paths
from paired_plan_DN_scopes import topology_contract


class PairedDNTopologyTests(unittest.TestCase):
    def fixture(self,**options):
        doc,graph,rows=fixtures.fixture(**options);hashes={v:dict(source_sha256='S',graph_sha256='G') for v in ('plan','iso')}
        state=pair_paths(dict(plan=doc,iso=doc),dict(plan=graph,iso=graph),rows,['D0','D1'],2,hashes)
        return doc,graph,dict(pair_id='P01',equipment_ids=['D0','D1'],services=state)
    def test_two_device_both_service_through_roles_come_from_native_lines(self):
        doc,g,pair=self.fixture();before=copy.deepcopy(g);r=topology_contract(doc,g,pair,'S','G',2)
        self.assertEqual(len(r['main_edges']),2);self.assertEqual(len(r['branches']),4);self.assertEqual(len(r['verified_taps']),4)
        self.assertEqual(r['branch_frontier_edges'],[]);self.assertEqual(g,before)
    def test_internal_true_T_keeps_non_through_network_branch_separate(self):
        doc,g,pair=self.fixture(interior=True);r=topology_contract(doc,g,pair,'S','G',2)
        self.assertEqual(len(r['verified_taps']),6);self.assertEqual(set(r['branch_frontier_edges']),{'supplyX','returnX'})
        self.assertEqual(len(r['main_edges']),4);self.assertEqual(len(r['branches']),4)
    def test_reverse_drawing_order_preserves_source_roles(self):
        doc,g,pair=self.fixture(reverse=True);r=topology_contract(doc,g,pair,'S','G',2)
        self.assertEqual(len(r['branches']),4);self.assertEqual(set(r['native_through_corridors']),{'supply','return'})
    def test_changed_route_corridor_owner_or_review_status_is_not_propagated(self):
        for mode in ('route','corridor','owner','review','floor'):
            doc,g,pair=self.fixture();s=pair['services']['supply']
            if mode=='route':s['routes']['plan']['edges']=[]
            elif mode=='corridor':s['native_corridors']['plan']['source_line_handle']='OTHER'
            elif mode=='owner':s['branches']['plan']['D0']=s['branches']['plan']['D1']
            elif mode=='review':next(n for n in g['nodes'] if n['node_id']=='supply0')['review_required']=True
            else:next(n for n in g['nodes'] if n['node_id']=='supply0')['floor']=1
            with self.assertRaises(ValueError):topology_contract(doc,g,pair,'S','G',2)
    def test_degree_two_subdivision_needs_its_own_DN_normalization(self):
        doc,g,pair=self.fixture(subdivision=True)
        with self.assertRaisesRegex(ValueError,'degree-two'):topology_contract(doc,g,pair,'S','G',2)


if __name__=='__main__':unittest.main()
