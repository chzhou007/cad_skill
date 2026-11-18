import copy,unittest
import ezdxf
from native_touching_plan_path_chunks import project,collect,measured_scopes,implementation_hashes


def fixture():
    doc=ezdxf.new('R2018');doc.header['$INSUNITS']=4;m=doc.modelspace()
    title=m.add_text('三层顶部水管平面图',dxfattribs=dict(insert=(0,0),height=10))
    specs=[]
    for point,angle in [((600,0),0),((0,750),90)]:
        drawing=m.add_linear_dim(base=(1000,1000),p1=(0,0),p2=point,angle=angle);drawing.render();dim=drawing.dimension
        text=next(t for t in doc.blocks[dim.dxf.geometry] if t.dxftype() in ('TEXT','MTEXT'))
        specs.append(dict(handle=dim.dxf.handle,text_handle=text.dxf.handle,text=text.plain_text()))
    m.add_line((100,100),(200,100),dxfattribs=dict(layer='空调冷冻水供水'))
    m.add_line((200,100),(200,300),dxfattribs=dict(layer='空调冷冻水供水'))
    graph=dict(metadata=dict(source_sha256='S'),nodes=[dict(node_id='A',floor=3,x=100,y=100),dict(node_id='B',floor=3,x=200,y=300)],
        edges=[dict(edge_id='P',system='supply',start_node_id='A',end_node_id='B',connection_mode=None,
            attribute_paths=[[[100,100],[200,100]],[[200,100],[200,300]]],device_names=['V1'])])
    policy=dict(view_kind='floor_plan',floor=3,source_sha256='S',graph_sha256='G',edges=['P'],records=[dict(scope_id='APPROACH',floor=3,system='supply',plan_edges=['P'])])
    metric=dict(view_kind='floor_plan',floor_title_handle=title.dxf.handle,floor_title=title.plain_text(),plan_window=[-100,1500,-100,1500],unit_dimensions=specs)
    return doc,graph,policy,metric


class Tests(unittest.TestCase):
    def test_private_join_adds_no_span_and_preserves_all_public_graph_fields(self):
        doc,graph,policy,metric=fixture();before=copy.deepcopy(graph)
        out,proof,locations=project(graph,['P'],3)
        self.assertEqual(out['edges'][0]['attribute_paths'],[[[100,100],[200,100],[200,300]]])
        self.assertEqual(proof[0]['added_span_units'],0);self.assertEqual(proof[0]['physical_nodes_added'],0)
        self.assertEqual(locations[('P',1)]['path_index'],1);self.assertEqual(graph,before)
    def test_native_metric_reuses_kernels_and_points_back_to_original_chunks(self):
        doc,graph,policy,metric=fixture();before=copy.deepcopy(graph)
        result=measured_scopes(doc,graph,policy,metric,'S','G');row=result['measured_scopes'][0]
        self.assertEqual(row['horizontal_projection']['value_mm'],300)
        self.assertEqual([(p['path_index'],p['segment_index']) for p in row['horizontal_projection']['pieces']],[(0,0),(1,0)])
        self.assertIsNone(row['installed_whole_edge_length_mm']);self.assertFalse(result['local_graph_mutated']);self.assertEqual(graph,before)
    def test_gap_crossing_retracing_and_other_floor_cannot_become_touching_chunks(self):
        for case in ('tiny_gap','reversed','interior_crossing','overlap','duplicate','other_floor','unknown_endpoint','omission','detail','nonfinite'):
            doc,graph,policy,metric=fixture();edge=graph['edges'][0]
            if case=='tiny_gap':edge['attribute_paths'][1][0][0]+=.001
            elif case=='reversed':edge['attribute_paths'][1].reverse()
            elif case=='interior_crossing':edge['attribute_paths'][1]=[[150,50],[150,150]]
            elif case=='overlap':edge['attribute_paths'][1]=[[200,100],[150,100]]
            elif case=='duplicate':edge['attribute_paths']=[[[100,100],[200,100]],[[200,100],[100,100]]]
            elif case=='other_floor':graph['nodes'][1]['floor']=2
            elif case=='unknown_endpoint':edge['end_node_id']='MISSING'
            elif case=='omission':edge['source_wave_omission']={}
            elif case=='detail':edge['source_view_context']={}
            else:edge['attribute_paths'][1][1][0]=float('nan')
            with self.subTest(case=case),self.assertRaises(ValueError):project(graph,['P'],3)
    def test_missing_or_opposite_system_source_and_wrong_units_still_block(self):
        for case in ('missing','system','duplicate_source','units','hash','record_floor'):
            doc,graph,policy,metric=fixture()
            if case=='missing':doc.modelspace().delete_entity(next(iter(doc.modelspace().query('LINE'))))
            elif case=='system':next(iter(doc.modelspace().query('LINE'))).dxf.layer='空调冷冻水回水'
            elif case=='duplicate_source':doc.modelspace().add_line((100,100),(200,100),dxfattribs=dict(layer='空调冷冻水供水'))
            elif case=='units':doc.header['$INSUNITS']=0
            elif case=='hash':policy['graph_sha256']='changed'
            else:policy['records'][0]['floor']=2
            with self.subTest(case=case),self.assertRaises(ValueError):measured_scopes(doc,graph,policy,metric,'S','G')
    def test_single_path_keeps_exact_geometry_and_original_index(self):
        doc,graph,policy,metric=fixture();graph['edges'][0]['attribute_paths']=[[[100,100],[200,100],[200,300]]]
        result=measured_scopes(doc,graph,policy,metric,'S','G')
        self.assertEqual(result['normalizations'][0]['join_points'],[])
        self.assertEqual([p['path_index'] for p in result['measured_scopes'][0]['horizontal_projection']['pieces']],[0,0])
    def test_dependency_closure_keeps_historical_native_and_metric_kernels(self):
        self.assertTrue({'native_plan_projection_lengths.py','native_path_coverage_audit.py','source_readability.py'}<=implementation_hashes().keys())


if __name__=='__main__':unittest.main()
