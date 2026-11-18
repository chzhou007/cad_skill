import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from test_plan_seeded_axis_branch_DN import scene
from axis_unbranched_vertical_DN import native_items
from inherited_marker_and_crossover_evidence import population
from native_paired_caption_geometry import collect as captions
from axis_unbranched_vertical_DN import annotation_index
from normalized_native_junction_evidence import replay
from reapply_inherited_branch_attribute_entries import qualify_with_endpoints,qualify_with_normalization,compare_inherited

def normalized_scene(folder,gap=2.354840376327047,new_DN=False):
    doc,g,route,owners,values=scene();edge=next(e for e in g['edges']if e['edge_id']=='ES')
    s=next(s for s in route['records']if s['edge_id']=='ES'and s['segment_index']==0);line=doc.entitydb[s['native_witnesses'][0]['source_handle']]
    line.dxf.start=(line.dxf.start.x,line.dxf.start.y-gap,line.dxf.start.z)
    s.update(native_source_status='no_witness_in_scoped_search',native_witnesses=[])
    if new_DN:
        a,b=edge['attribute_paths'][0][2:4];doc.modelspace().add_text('DN80',dxfattribs={'insert':(a[0]+5,(a[1]+b[1])/2),'height':5,'rotation':90})
    config=dict(system_layers={'空调冷冻水供水':'supply','空调冷冻水回水':'return'},
        elbow_overshoot=dict(maximum_length=10,maximum_ratio=.1,minimum_angle_degrees=20),
        near_junction=dict(maximum_gap=3,discovery_maximum_gap=10,maximum_ratio=.05,minimum_angle_degrees=20),previous_source_sha256='S')
    _,audit=replay(doc,config);path=Path(folder)/'audit.json';path.write_text(json.dumps(audit),encoding='utf8')
    spec=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    candidate=dict(axis_edge_id='ES',axis_T='S',axis_interface='V',main_arms=['SL','SR'])
    items=native_items(doc,g);pop=population(doc,'S');caps=captions(doc);annotations=annotation_index(doc,g,'S')
    return (candidate,doc,g,route,{r['axis_edge_id']:r for r in owners},values,items,'S','G',pop,caps,annotations),spec,line

class InheritedBranchAttributeComposition(unittest.TestCase):
    def test_old_native_qualifier_receives_only_replayed_semantic_context(self):
        with tempfile.TemporaryDirectory()as folder:
            args,audit,line=normalized_scene(folder);before=copy.deepcopy((args[2],args[3],args[6]));raw_start=list(line.dxf.start)
            with self.assertRaises(ValueError):qualify_with_endpoints(*args,{})
            row,shadow,private_route,private_items,proof=qualify_with_normalization(*args,audit)
            self.assertEqual((args[2],args[3],args[6]),before);self.assertEqual(list(line.dxf.start),raw_start)
            self.assertEqual(row['nominal_mm'],200);self.assertTrue(row['raw_source_gap_still_unwitnessed'])
            self.assertTrue(proof['private_schema_not_raw_LINE_evidence']);self.assertIsNone(row['physical_length_mm'])
            self.assertEqual(row['vertical_values_assigned'],0)
            self.assertTrue(all(s['native_source_status']=='single_source_line_covers'for s in row['horizontal_segment_domains']))
            self.assertFalse(row['whole_axis_DN_assigned'])

    def test_original_gap_limit_and_full_branch_new_DN_barrier_survive_composition(self):
        for kw in(dict(gap=4),dict(new_DN=True)):
            with tempfile.TemporaryDirectory()as folder:
                args,audit,_=normalized_scene(folder,**kw)
                with self.subTest(kw=kw),self.assertRaises(ValueError):qualify_with_normalization(*args,audit)

    def test_old_source_payload_and_current_DN_must_both_stay_exact(self):
        old=[dict(axis_edge_id='E',nominal_mm=200,old_whole_DN=None,native_T={'source':'old'},scope_paths=[[[0,0],[1,0]]])]
        current=copy.deepcopy(old);current[0]['old_whole_DN']=200
        values={'E':{'diameter_nominal_mm':200}}
        self.assertEqual(compare_inherited(old,current,values),['E'])
        for defect in('missing','geometry','old_DN','duplicate'):
            bad=copy.deepcopy(current)
            if defect=='missing':bad=[]
            elif defect=='geometry':bad[0]['scope_paths'][0][0][0]=10
            elif defect=='old_DN':bad[0]['old_whole_DN']=80
            else:bad.append(copy.deepcopy(bad[0]))
            with self.subTest(defect=defect),self.assertRaises(ValueError):compare_inherited(old,bad,values)
if __name__=='__main__':unittest.main()
