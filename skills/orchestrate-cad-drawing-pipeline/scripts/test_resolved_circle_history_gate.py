import copy
import hashlib
import json
import unittest
from source_comparison_gate import graph_comparison_blockers, resolved_circle_crossover_history


class ResolvedCircleHistoryTests(unittest.TestCase):
    def setUp(self):
        self.g={'metadata':{'source_sha256':'source'}, 'nodes':[], 'edges':[],
                'sourceCircleCrossoverConflicts':[], 'preHilComparison':{'status':'pending','previous_comparison':
                {'families':[{'id':'circle_crossover_conflict','status':'pending'},{'id':'other_pending','status':'pending'}]}}}
        connections=[]
        for i in (1,2):
            ev={'circle_handle':'C'+str(i),'branch_handle':'B'+str(i),'user_evidence_manifest_sha256':'ev'}
            self.g['nodes'].append({'node_id':'T'+str(i),'node_type':'tee','system':'supply','user_confirmed_overlap_connection':ev})
            self.g['edges'].extend([{'edge_id':'B'+str(i),'start_node_id':'T'+str(i),'end_node_id':'V'+str(i),'system':'supply','user_confirmed_overlap_connection':ev},
                                   {'edge_id':'M'+str(i),'start_node_id':'T'+str(i),'end_node_id':'X'+str(i),'system':'supply'}])
            connections.append({'circle_handle':'C'+str(i),'branch_handle':'B'+str(i),'branch_edge':'B'+str(i),'node_id':'T'+str(i),'main_edges':['M'+str(i),'MID']})
        self.g['edges'].append({'edge_id':'MID','start_node_id':'T1','end_node_id':'T2','system':'supply'})
        original={'status':'pending','source_handles':['B1','B2']}
        digest=hashlib.sha256(json.dumps(original,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
        self.g['sourceCircleCrossoverConflictHistory']=[{'source_sha256':'source','connectivity_changed':False,'evidence_manifest_sha256':'ev',
            'records':[{'original_conflict':original,'conflict_sha256':digest,'resolution':'separate_confirmed_tees_on_native_main_not_collinear_gap','connections':connections,'native_main_edge':'MID'}]}]

    def test_ignores_only_proven_obsolete_family(self):
        _,families=graph_comparison_blockers(self.g)
        self.assertNotIn('circle_crossover_conflict',families)
        self.assertIn('other_pending',families);self.assertIn('source_comparison_status:pending',families)

    def test_empty_list_without_archive_is_not_resolution(self):
        self.g.pop('sourceCircleCrossoverConflictHistory')
        self.assertIn('circle_crossover_conflict',graph_comparison_blockers(self.g)[1])

    def test_changed_graph_evidence_and_remaining_conflicts_block(self):
        for mode in ('source','endpoint','system','fourway','evidence','record','pending'):
            g=copy.deepcopy(self.g)
            if mode=='source':g['metadata']['source_sha256']='other'
            elif mode=='endpoint':g['edges'][0]['start_node_id']='T2'
            elif mode=='system':g['edges'][0]['system']='return'
            elif mode=='fourway':g['edges'].append(dict(g['edges'][0],edge_id='extra'))
            elif mode=='evidence':g['edges'][0]['user_confirmed_overlap_connection']['circle_handle']='wrong'
            elif mode=='record':g['sourceCircleCrossoverConflictHistory'][0]['records'][0]['original_conflict']['status']='changed'
            elif mode=='pending':g['sourceCircleCrossoverConflicts']=[{'status':'pending'}]
            with self.subTest(mode=mode):
                self.assertFalse(resolved_circle_crossover_history(g))
                self.assertIn('circle_crossover_conflict',graph_comparison_blockers(g)[1])


if __name__=='__main__':unittest.main()
