import copy,json,unittest
from test_repair_native_flexible_joints import NativeJointTests
from repair_native_flexible_joints import repair,fingerprint
from native_inline_joint_path_coverage import collect
from native_line_path_evidence import LAYERS

def fixture(rotation=0,mirror=False,encoded=False):
    doc,graph,policy=NativeJointTests().setup_case(rotation,mirror)
    doc.blocks['JOINT'].add_spline(fit_points=[(-5,0),(0,1),(5,0)])
    policy.update(block_fingerprint_sha256=fingerprint(doc.blocks['JOINT']),confirmation_basis='source_geometry_calibrated')
    for e in graph['edges']:
        line=doc.modelspace().add_line(e['path'][0],e['path'][-1],dxfattribs=dict(layer=LAYERS[e['system']]))
        e['source_handles']=[line.dxf.handle]
    current,rows,_=repair(graph,[],doc,policy)
    if encoded:current['edges'][0]['attribute_paths']=[copy.deepcopy(current['edges'][0]['path_points'])]
    current=json.loads(json.dumps(current))
    hashes=dict(source_sha256='S'*64,graph_sha256='G'*64,inventory_sha256='I'*64)
    cfg=dict(hashes,block_name='JOINT',block_fingerprint_sha256=policy['block_fingerprint_sha256'],edges=[current['edges'][0]['edge_id']])
    return doc,current,rows,cfg,hashes

class Tests(unittest.TestCase):
    def test_plan_split_and_axis_marker_span_preserve_unknown_length_and_original_paths(self):
        for encoded in (False,True):
            for rotation,mirror in [(0,False),(90,False),(180,True),(270,True)]:
                with self.subTest(encoded=encoded,rotation=rotation,mirror=mirror):
                    args=fixture(rotation,mirror,encoded);before=copy.deepcopy(args[1]);result=collect(*args)
                    self.assertEqual(args[1],before);self.assertEqual(result['physical_lengths_assigned'],0)
                    row=result['records'][0];self.assertEqual(row['source_drawn_pipe_length_units'],40)
                    self.assertEqual([p['kind'] for p in row['private_ordered_pieces']],['native_pipe','native_inline_joint','native_pipe'])
                    self.assertIsNone(row['physical_length_mm']);self.assertTrue(row['joint_spans_excluded_from_pipe_length'])
    def test_wrong_system_duplicate_typed_line_or_Z_disagreement_blocks(self):
        for failure in ('system','duplicate','Z'):
            args=list(fixture());doc=args[0];line=next(iter(doc.modelspace().query('LINE')))
            if failure=='system':line.dxf.layer=LAYERS['return']
            elif failure=='duplicate':doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs=dict(layer=line.dxf.layer))
            else:line.dxf.start=(line.dxf.start.x,line.dxf.start.y,1);line.dxf.end=(line.dxf.end.x,line.dxf.end.y,1)
            with self.subTest(failure=failure),self.assertRaises(ValueError):collect(*args)
    def test_stale_hash_template_and_missing_path_do_not_pass(self):
        for failure in ('hash','template','paths'):
            args=list(fixture())
            if failure=='hash':args[3]['graph_sha256']='old'
            elif failure=='template':args[3]['block_fingerprint_sha256']='old'
            else:args[1]['edges'][0]['attribute_paths']=[]
            with self.subTest(failure=failure),self.assertRaises(ValueError):collect(*args)
    def test_inventory_duplicate_or_graph_component_mismatch_blocks(self):
        for failure in ('duplicate','name','metadata','foreign_owner'):
            args=list(fixture())
            if failure=='duplicate':args[2].append(copy.deepcopy(args[2][0]))
            elif failure=='name':args[1]['edges'][0]['equipment_names']=[]
            elif failure=='metadata':args[1]['edges'][0]['source_flexible_joints'][0]['physical_length']='0'
            else:args[2][0]['edge_id']='other'
            with self.subTest(failure=failure),self.assertRaises(ValueError):collect(*args)
    def test_unrelated_unwitnessed_span_is_not_permitted_by_nearby_joint(self):
        args=list(fixture(encoded=True));args[1]['edges'][0]['attribute_paths'][0].insert(1,[80,210])
        with self.assertRaises(ValueError):collect(*args)
    def test_disconnected_extra_source_piece_is_not_a_valid_chain(self):
        args=list(fixture());doc=args[0]
        doc.modelspace().add_line((500,500),(510,500),dxfattribs=dict(layer=LAYERS['supply']))
        args[1]['edges'][0]['attribute_paths'].append([[500,500],[510,500]])
        with self.assertRaisesRegex(ValueError,'chain'):collect(*args)

if __name__=='__main__':unittest.main()
