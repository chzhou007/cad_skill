import copy,unittest
import ezdxf
from native_nested_paired_caption_DN import collect
from native_line_path_evidence import LAYERS

def scene(rotation=0):
    doc=ezdxf.new('R2013');space=doc.modelspace();block=doc.blocks.new('paired_native_pipes')
    source={}
    for system,x in [('return',0),('supply',200)]:source[system]=block.add_line((x,0,0),(x,2000,0),dxfattribs={'layer':LAYERS[system]})
    root=space.add_blockref(block.name,(10000,10000),dxfattribs={'rotation':rotation});matrix=root.matrix44()
    texts=[]
    for x,value in [(350,80),(-50,65)]:
        point=matrix.transform((x,500,0));texts.append(space.add_text('DN'+str(value),dxfattribs={'insert':point,'height':100,'rotation':(90+rotation)%360}))
    sh='a'*64;gh='b'*64;graph=dict(metadata=dict(source_sha256=sh),nodes=[],edges=[]);route=dict(inputs=dict(source=dict(sha256=sh),graph=dict(sha256=gh)),records=[])
    for system,line in source.items():
        points=[list(matrix.transform(p))[:2] for p in (line.dxf.start,line.dxf.end)];eid=system
        graph['edges'].append(dict(edge_id=eid,system=system,source_insert_handle=root.dxf.handle,attribute_paths=[points],floor_start=1,floor_end=1))
        route['records'].append(dict(edge_id=eid,path_index=0,segment_index=0,system=system,scope_points=points,direction_class='vertical',floor_start=1,floor_end=1,
            native_source_status='single_source_line_covers',native_witnesses=[dict(scope='decomposed_selected_insert',source_handle=root.dxf.handle,layer=LAYERS[system],start=points[0],end=points[1])]))
    return doc,graph,route,[t.dxf.handle for t in texts],sh,gh

class NativeNestedPairTests(unittest.TestCase):
    def test_original_geometric_order_on_actual_block_and_rotated_instance(self):
        for rotation in (0,180):
            with self.subTest(rotation=rotation):
                args=scene(rotation);before=copy.deepcopy(args[1:]);result=collect(*args)
                self.assertEqual(args[1:],before);self.assertEqual({r['system']:r['nominal_mm'] for r in result['records']},{'return':65,'supply':80})
                self.assertTrue(result['original_geometry_reader_reused']);self.assertFalse(result['DN_used_to_choose_pipe']);self.assertFalse(result['layout_control_threshold_changed'])
                self.assertEqual(result['physical_lengths_assigned'],0)
                for r in result['records']:
                    self.assertIsNone(r['physical_length_mm']);self.assertFalse(r['whole_edge_DN_assigned']);self.assertEqual(r['observations'][0]['native_evidence']['source_chain'][0],args[1]['edges'][0]['source_insert_handle'])

    def test_full_projection_keeps_third_competitor_and_duplicate_source(self):
        args=scene();args[0].modelspace().add_line((10100,10000),(10100,12000),dxfattribs={'layer':LAYERS['return']})
        result=collect(*args);self.assertFalse(result['records']);self.assertTrue(any('other parallel pipes' in p['reason'] for p in result['held_pairs']))
        args=scene();root=args[0].entitydb[args[1]['edges'][0]['source_insert_handle']];args[0].blocks[root.dxf.name].add_line((0,0),(0,2000),dxfattribs={'layer':LAYERS['return']})
        self.assertFalse(collect(*args)['records'])

    def test_competing_caption_and_noncoincident_source_Z_stay_unknown(self):
        args=scene();args[0].modelspace().add_text('DN100',dxfattribs={'insert':(9960,10500),'height':100,'rotation':90})
        result=collect(*args);self.assertFalse(result['records']);self.assertTrue(any('competing' in p['reason'] for p in result['held_pairs']))
        args=scene();root=args[0].entitydb[args[1]['edges'][0]['source_insert_handle']];root.dxf.insert=(10000,10000,10)
        result=collect(*args);self.assertFalse(result['records']);self.assertTrue(any('source Z' in p['reason'] for p in result['held_pairs']))

if __name__=='__main__':unittest.main()
