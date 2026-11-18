import copy,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
from native_plan_projection_lengths import lengths
from native_main_interval_metrics import touching_projection,measure,coalesced_scope

def fixture():
    paths=[[[0,0],[10,0]],[[10,0],[10,20]]];edge=dict(edge_id='P',system='supply',attribute_paths=paths)
    segments=[dict(index=0,path_index=i,start=p[0],end=p[1],drawing_length=[10,20][i],status='single_source_line_covers',witnesses=[dict(scope='modelspace',source_handle=str(i))])for i,p in enumerate(paths)]
    return dict(edges=[edge]),dict(edges=[dict(edge_id='P',system='supply',segments=segments)]),dict(mapping_id='M',plan_edges=['P'],iso_edges=['A'],system='supply'),dict(plan_window=[-1,100,-1,100])
class Tests(unittest.TestCase):
    def test_exact_touching_bent_native_subdivisions_reuse_original_metric(self):
        graph,proof,row,units=fixture();before=copy.deepcopy((graph,proof,row))
        with self.assertRaisesRegex(ValueError,'separate plan paths'):lengths(graph,proof,row,units)
        result=touching_projection(graph,proof,row,units)
        self.assertEqual(result['value_mm'],30);self.assertEqual([(p['path_index'],p['segment_index'])for p in result['pieces']],[(0,0),(1,0)])
        self.assertIsNone(result['installed_whole_edge_length_mm']);self.assertFalse(result['graphic_or_omitted_spans_added']);self.assertEqual((graph,proof,row),before)
    def test_nonzero_gap_even_small_is_not_a_touching_subdivision(self):
        for gap in(.00000001,100):
            g,p,r,u=fixture();g['edges'][0]['attribute_paths'][1][0][0]+=gap
            with self.assertRaisesRegex(ValueError,'do not touch exactly'):touching_projection(g,p,r,u)
    def test_bad_coverage_service_and_duplicate_witnesses_remain_rejected(self):
        for mode in('service','duplicate_witness','missing_segment','detail'):
            g,p,r,u=fixture()
            if mode=='service':r['system']='return'
            elif mode=='duplicate_witness':p['edges'][0]['segments'][0]['witnesses']*=2
            elif mode=='missing_segment':p['edges'][0]['segments'].pop()
            else:g['edges'][0]['source_view_context']={'kind':'detail'}
            with self.assertRaises((ValueError,KeyError)):touching_projection(g,p,r,u)
    def test_existing_crossover_reader_is_used_after_basic_scope_rejection(self):
        g,p,r,u=fixture();g['edges'][0]['attribute_paths'][1][0]=[11,0]
        inherited=dict(mapping_id='M',plan_edges=['P'],iso_edges=['A'],projection={'value_mm':29,'installed_whole_edge_length_mm':None},reader='inherited_native_crossover_pipe_XY',attempts=[])
        with patch('native_main_interval_metrics.extend',return_value=dict(records=[inherited]))as owner:
            result=measure(None,g,[],p,r,u,{},{});self.assertEqual(result['reader'],'inherited_native_crossover_pipe_XY');self.assertEqual(result['projection']['value_mm'],29);owner.assert_called_once()
    def test_unsupported_metric_preserves_unknown_and_mapping_scope(self):
        g,p,r,u=fixture();g['edges'][0]['attribute_paths'][1][0]=[11,0]
        inherited=dict(mapping_id='M',plan_edges=['P'],iso_edges=['A'],projection=None,reader=None,reason='unsupported existing source omission',attempts=[])
        with patch('native_main_interval_metrics.extend',return_value=dict(records=[inherited])):
            result=measure(None,g,[],p,r,u,{},{});self.assertIsNone(result['projection']);self.assertEqual(result['iso_edges'],['A']);self.assertFalse(result['unknown_length_filled_with_zero'])
    def test_exact_touching_projection_preserves_real_gap_and_original_indices(self):
        g,p,r,u=fixture();g['edges'][0]['attribute_paths'].insert(0,[[-10,0],[-2,0]])
        before=copy.deepcopy(g);private,binding=coalesced_scope(g,r)
        self.assertEqual(private['edges'][0]['attribute_paths'],[[[-10,0],[-2,0]],[[0,0],[10,0],[10,20]]])
        self.assertEqual(binding['original_indices'],[[(0,0)],[(1,0),(2,0)]])
        self.assertNotEqual(binding['input_graph_value_sha256'],binding['projection_graph_sha256']);self.assertEqual(g,before)
if __name__=='__main__':unittest.main()
