import copy
import unittest

from review_view_lineage import audit

SOURCE = 'a' * 64
PAIR = 'b' * 64


def fixture(owned=True):
    answer = dict(decision='对应同一组管路', comment='透视延续，支路连三通')
    canonical = dict(abbreviated_edge='OLD', system='supply', question_id='Q', answer=copy.deepcopy(answer),
                     pair_sha256=PAIR, canonical_edge='NEW', canonical_interface='VIF',
                     verified_detail_tee=dict(tee='T'), projected_main_identity='not_inferred')
    graph = dict(nodes=[dict(node_id='T'), dict(node_id='DEVICE' if owned else 'VIF')],
                 edges=[dict(edge_id='NEW', system='supply', start_node_id='T', end_node_id='DEVICE' if owned else 'VIF')],
                 sourceDetailComparison=dict(source_sha256=SOURCE, pairs=[dict(upper_edge='OLD', upper_terminal='WAVE',
                                            upper_pipe='HANDLE', detail_tee='T', system='supply')]),
                 confirmedSideviewCanonicalization=dict(source_sha256=SOURCE, records=[canonical],
                     representation_only_edges=[dict(edge_id='OLD', source_handles=['HANDLE'])],
                     representation_only_nodes=[dict(node_id='WAVE')], edge_aliases=dict(OLD='NEW')))
    if owned:
        graph['sourceSideviewEquipmentOwnership'] = dict(source_sha256=SOURCE, records=[
            dict(edge_id='NEW', system='supply', equipment_id='DEVICE', source_sha256=SOURCE, original_canonical_interface_id='VIF')])
    review = dict(sections=[dict(image=dict(sha256=PAIR), questions=[dict(id='Q', options=['对应同一组管路', '不是同一组'])])],
                  received_feedback=dict(answers=dict(Q=copy.deepcopy(answer))))
    return graph, review


class Tests(unittest.TestCase):
    def test_adopted_alias_is_not_a_repeated_question_or_physical_claim(self):
        graph, review = fixture()
        before = copy.deepcopy((graph, review))
        result = audit(graph, review, SOURCE)
        self.assertEqual((graph, review), before)
        self.assertEqual((result['historical_candidates'], result['adopted_sideview_relations'], result['owner_known']), (1, 1, 1))
        row = result['records'][0]
        self.assertFalse(row['repeated_sideview_question_needed'])
        self.assertFalse(row['whole_main_correspondence_proven'])
        self.assertFalse(row['physical_ports_verified'])
        self.assertIsNone(row['installed_length_mm'])
        self.assertFalse(row['rebuilt_graph_human_accepted'])

    def test_relation_and_owner_have_separate_states(self):
        graph, review = fixture(False)
        result = audit(graph, review, SOURCE)
        self.assertEqual(result['adopted_sideview_relations'], 1)
        self.assertEqual(result['owner_known'], 0)
        self.assertEqual(result['owner_unresolved'], 1)
        self.assertEqual(result['records'][0]['status'], 'sideview_confirmed_owner_unresolved')
        self.assertFalse(result['records'][0]['repeated_sideview_question_needed'])

    def test_unadopted_candidate_remains_unknown(self):
        graph, review = fixture()
        graph.pop('confirmedSideviewCanonicalization')
        graph.pop('sourceSideviewEquipmentOwnership')
        graph['edges'] = [dict(edge_id='OLD')]
        result = audit(graph, review, SOURCE)
        self.assertEqual(result['not_adopted_candidates'], 1)
        self.assertFalse(result['records'][0]['sideview_relation_proved'])
        self.assertEqual(result['new_HIL_questions'], 0)

    def test_changed_answer_pair_or_missing_original_answer_blocks_old_confirmation(self):
        for case in ['decision', 'pair', 'missing']:
            with self.subTest(case=case):
                graph, review = fixture()
                if case == 'decision': review['received_feedback']['answers']['Q']['decision'] = '不是同一组'
                elif case == 'pair': review['sections'][0]['image']['sha256'] = 'c' * 64
                else: review['received_feedback']['answers'].clear()
                with self.assertRaises(ValueError): audit(graph, review, SOURCE)

    def test_stale_source_and_wrong_system_do_not_reuse_a_disposition(self):
        for case in ['historical_source', 'canonical_source', 'ownership_source', 'edge_system']:
            with self.subTest(case=case):
                graph, review = fixture()
                if case == 'historical_source': graph['sourceDetailComparison']['source_sha256'] = 'c' * 64
                elif case == 'canonical_source': graph['confirmedSideviewCanonicalization']['source_sha256'] = 'c' * 64
                elif case == 'ownership_source': graph['sourceSideviewEquipmentOwnership']['source_sha256'] = 'c' * 64
                else: graph['edges'][0]['system'] = 'return'
                with self.assertRaises(ValueError): audit(graph, review, SOURCE)

    def test_alias_snapshots_and_T_must_be_current(self):
        for case in ['alias', 'lost_snapshot', 'wrong_handle', 'duplicate_active', 'missing_T', 'wrong_T']:
            with self.subTest(case=case):
                graph, review = fixture()
                root = graph['confirmedSideviewCanonicalization']
                if case == 'alias': root['edge_aliases']['OLD'] = 'MISSING'
                elif case == 'lost_snapshot': root['representation_only_nodes'].clear()
                elif case == 'wrong_handle': root['representation_only_edges'][0]['source_handles'] = ['OTHER']
                elif case == 'duplicate_active': graph['edges'].append(dict(edge_id='OLD'))
                elif case == 'missing_T': graph['nodes'] = [n for n in graph['nodes'] if n['node_id'] != 'T']
                else: root['records'][0]['verified_detail_tee']['tee'] = 'OTHER'
                with self.assertRaises(ValueError): audit(graph, review, SOURCE)

    def test_wrong_current_owner_and_duplicate_relations_block(self):
        for case in ['owner', 'original_interface', 'duplicate_owner', 'duplicate_relation', 'duplicate_candidate']:
            with self.subTest(case=case):
                graph, review = fixture()
                if case == 'owner': graph['sourceSideviewEquipmentOwnership']['records'][0]['equipment_id'] = 'OTHER'
                elif case == 'original_interface': graph['sourceSideviewEquipmentOwnership']['records'][0]['original_canonical_interface_id'] = 'OTHER'
                elif case == 'duplicate_owner': graph['sourceSideviewEquipmentOwnership']['records'] *= 2
                elif case == 'duplicate_relation': graph['confirmedSideviewCanonicalization']['records'] *= 2
                else: graph['sourceDetailComparison']['pairs'] *= 2
                with self.assertRaises(ValueError): audit(graph, review, SOURCE)

    def test_no_historical_candidates_needs_no_synthetic_question(self):
        result = audit(dict(nodes=[], edges=[]), dict(sections=[]), SOURCE)
        self.assertEqual(result['historical_candidates'], 0)
        self.assertEqual(result['new_HIL_questions'], 0)
        self.assertFalse(result['native_source_replay'])

    def test_explicit_reopening_invalidates_confirmation_without_blocking_review(self):
        graph, review = fixture()
        review['review_workflow'] = dict(reopened_question_ids=['Q'])
        review['received_feedback']['answers']['Q']['decision'] = '不是同一组'
        before = copy.deepcopy((graph, review))
        result = audit(graph, review, SOURCE)
        self.assertEqual((graph, review), before)
        self.assertEqual(result['explicitly_reopened_relations'], 1)
        self.assertEqual(result['adopted_sideview_relations'], 0)
        self.assertFalse(result['records'][0]['sideview_relation_proved'])
        self.assertFalse(result['records'][0]['rebuilt_graph_human_accepted'])
        self.assertEqual(result['new_HIL_questions'], 0)


if __name__ == '__main__':
    unittest.main()
