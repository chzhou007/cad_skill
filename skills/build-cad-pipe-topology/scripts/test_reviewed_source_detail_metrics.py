import copy, unittest
from reviewed_source_detail_metrics import authorize
from cycle_gate_plan_lengths import qualify
from test_cycle_gate_plan_lengths import fixture as metric_fixture


def fixture():
    decision = '平面省略，实物按轴测两阀'
    row = dict(axis_edge_id='A', plan_edge_id='P', source_detail_difference=True,
               component_profiles=dict(plan=dict(ball_valve=1), iso=dict(ball_valve=2)))
    answer = dict(question_id='Q', pair_sha256='a' * 64,
        explicit_answer=dict(decision=decision, source_pair_sha256='a' * 64),
        source_evidence=dict(related_current_axis_edges=['A'], source_plan_edges=['P'],
            plan_native_ball_instances=1, axis_native_ball_instances=2))
    return dict(records=[answer]), 'Q', decision, [row]


class Tests(unittest.TestCase):
    def test_exact_scope_answer_explains_detail_not_diameter_or_positions(self):
        args = fixture(); before = copy.deepcopy(args)
        answer = authorize(*args)
        self.assertEqual(answer['question_id'], 'Q')
        self.assertEqual(args, before)
        metric = metric_fixture()
        metric[2]['component_profiles'] = args[3][0]['component_profiles']
        result = qualify(*metric)
        self.assertEqual(result['complete_horizontal_centerline_mm'], 10)
        self.assertIsNone(result['nominal_mm'])
        self.assertIsNone(result['physical_installed_length_mm'])
        self.assertIsNone(result['net_pipe_cut_length_mm'])

    def test_changed_choice_extent_counts_or_pair_cannot_clear_gate(self):
        for key in ('choice', 'scope', 'counts', 'pair', 'other_components'):
            args = list(fixture())
            answer = args[0]['records'][0]
            if key == 'choice': answer['explicit_answer']['decision'] = '暂不确定'
            elif key == 'scope': answer['source_evidence']['related_current_axis_edges'] = ['OTHER']
            elif key == 'counts': args[3][0]['component_profiles']['iso']['ball_valve'] = 3
            elif key == 'pair': answer['explicit_answer']['source_pair_sha256'] = 'b' * 64
            else: args[3][0]['component_profiles']['plan']['unknown_component'] = 1
            with self.subTest(key=key), self.assertRaises(ValueError): authorize(*args)
        args = list(fixture()); args[2] = '暂不确定'
        args[0]['records'][0]['explicit_answer']['decision'] = args[2]
        with self.assertRaises(ValueError): authorize(*args)

    def test_confirmation_does_not_make_gaps_or_same_floor_vertical_into_lengths(self):
        authorize(*fixture())
        gap = metric_fixture([[[0, 0], [4, 0]], [[6, 0], [10, 0]]])
        with self.assertRaises(ValueError): qualify(*gap)
        vertical = metric_fixture()
        vertical[1]['nodes'][1].update(x=0, y=10)
        vertical[1]['edges'][0]['attribute_paths'] = [[[0, 0], [0, 10]]]
        with self.assertRaises(ValueError): qualify(*vertical)


if __name__ == '__main__': unittest.main()
