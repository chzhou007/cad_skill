import copy,unittest
from test_native_repeated_branch_DN_layout import fixture
from native_repeated_branch_DN_layout import collect
from axis_local_DN_segment_domains import locate


def scenario():
    doc,graph,targets,_=fixture()
    for edge in graph['edges']:edge.update(floor_start=3,floor_end=3)
    return graph,collect(doc,graph,targets,'S','G'),'S','G'


class Tests(unittest.TestCase):
    def test_unique_same_floor_native_segment_remains_a_drawing_domain(self):
        args=scenario();before=copy.deepcopy(args);result=locate(*args)
        self.assertEqual(args,before);self.assertEqual(len(result['records']),2)
        for row in result['records']:
            self.assertEqual(row['segment']['drawing_direction'],'vertical_stroke_in_CAD_WCS');self.assertEqual(row['graph_floor_relation'],'same_floor_graph_scope')
            self.assertEqual((row['segment']['path_index'],row['segment']['segment_index']),(0,0))
            self.assertIsNone(row['physical_vertical_length_mm']);self.assertFalse(row['inter_floor_riser_proved']);self.assertFalse(row['equal_plan_axis_segment_extents_proved'])

    def test_unknown_or_different_graph_floors_do_not_prove_interfloor_riser(self):
        for case in ('missing','different'):
            with self.subTest(case=case):
                graph,proof,sh,gh=scenario()
                for edge in graph['edges']:
                    if case=='missing':edge.pop('floor_end')
                    else:edge['floor_end']=4
                out=locate(graph,proof,sh,gh)
                self.assertTrue(all(r['graph_floor_relation']==('unknown_graph_floor_domain' if case=='missing' else 'different_floor_graph_scope') for r in out['records']))
                self.assertTrue(all(not r['inter_floor_riser_proved'] for r in out['records']))

    def test_stale_source_competing_path_shifted_source_or_graph_system_fail(self):
        for case in ('hash','source','path','native','system','floor','duplicate'):
            with self.subTest(case=case):
                graph,proof,sh,gh=scenario();edge=graph['edges'][-2]
                if case=='hash':gh='stale'
                elif case=='source':sh='stale'
                elif case=='path':edge['attribute_paths'].append(copy.deepcopy(edge['attribute_paths'][0]))
                elif case=='native':proof['records'][0]['native_binding']['XYZ'][0][0]+=2
                elif case=='system':edge['system']='return'
                elif case=='floor':edge['start_floor']=4
                else:proof['records'].append(copy.deepcopy(proof['records'][0]))
                with self.assertRaises(ValueError):locate(graph,proof,sh,gh)


if __name__=='__main__':unittest.main()
