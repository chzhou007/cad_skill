import copy,unittest,tempfile
from pathlib import Path
from test_native_line_f_diameter_evidence import NativeLineFTests
from test_calibrated_direct_dn_evidence import CalibratedDirectDNTests
from full_plan_DN_inherited_annotations import collect,current_calibration
from rebuild_inherited_full_plan_DN import configuration


class Tests(unittest.TestCase):
    def test_complete_json_replay_ignores_only_object_key_order_and_python_tuple_storage(self):
        from verify_inherited_plan_DN_semantics import canonical
        a=dict(DN=100,lineage=[dict(point=(1,2),service='supply')],unknown=None)
        b=dict(unknown=None,lineage=[dict(service='supply',point=[1,2])],DN=100)
        self.assertEqual(canonical(a),canonical(b))
        for key,value in [('DN',True),('DN',100.0),('unknown',0),('lineage',[]),('extra',False)]:
            changed=copy.deepcopy(b);changed[key]=value
            with self.subTest(key=key,value=value):self.assertNotEqual(canonical(a),canonical(changed))
        c=dict(records=[dict(edge='a'),dict(edge='b')])
        self.assertNotEqual(canonical(c),canonical(dict(records=list(reversed(c['records'])))))
    def test_complete_json_verifier_keeps_receipt_and_all_native_implementation_checks(self):
        import json
        from unittest.mock import patch
        import verify_inherited_plan_DN_semantics as verifier
        from confirm_crossview_paths import encode,sha
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);manifest=root/'manifest.json';manifest.write_bytes(encode(dict(plans=[])))
            target=root/'inherited-plan-DN-results.json';target.write_bytes(encode(dict(z=[1,2],a=None)))
            receipt=dict(mode=verifier.MODE,implementation_sha256=verifier.implementation_hashes(),output_sha256=sha(target),manifest=dict(path=str(manifest),sha256=sha(manifest)))
            rp=root/'inherited-plan-DN-receipt.json';rp.write_bytes(encode(receipt))
            with patch.object(verifier,'compute',return_value=dict(a=None,z=(1,2)))as native:
                self.assertEqual(verifier.verify_output(root),dict(a=None,z=[1,2]));native.assert_called_once()
            with patch.object(verifier,'compute',return_value=dict(a=0,z=[1,2])):
                with self.assertRaisesRegex(ValueError,'JSON value'):verifier.verify_output(root)
            target.write_bytes(encode(dict(a=None,z=[1,2])))
            with patch.object(verifier,'compute')as native:
                with self.assertRaisesRegex(ValueError,'recorded bytes'):verifier.verify_output(root)
                native.assert_not_called()
    def test_inherited_producer_rejects_stale_origins_before_native_parent_work(self):
        from rebuild_inherited_full_plan_DN import configuration
        from confirm_crossview_paths import encode,sha
        with tempfile.TemporaryDirectory()as directory:
            path=Path(directory)/'origin.json';path.write_bytes(encode(dict(source_sha256='S',groups=[dict(line_F_frames=[dict(stem_handle='L')])])))
            item=dict(inputs=dict(source=dict(sha256='S')),inherited_annotation_inputs=dict(F_origin=dict(path=str(path),sha256=sha(path))))
            self.assertEqual(configuration(item)['line_F_frames'],[dict(stem_handle='L')])
            path.write_bytes(encode(dict(source_sha256='other',groups=[])))
            with self.assertRaises(ValueError):configuration(item)
    def test_inherited_gate_requires_previous_complete_local_scope_contract(self):
        from test_full_plan_DN_gate import fixture
        from inherited_full_plan_DN_gate import check
        d=fixture();d.update(previous_mode=d['mode'],mode='complete_local_plan_native_DN_inherited_annotations_v2',historical_native_implementations_or_globals_changed=False)
        d['floors']['1']['inherited_annotation_readers_applied']=['ordered_native_F']
        self.assertEqual(check(d)['known_plan_DN_edges'],1)
        d['historical_native_implementations_or_globals_changed']=True
        with self.assertRaises(ValueError):check(d)
    def test_native_ordered_F_is_applied_on_the_complete_plan_under_rotation_and_mirror(self):
        for angle,mirror,negative,reversed_stem in [(0,1,False,False),(90,1,False,True),(180,-1,True,False),(270,-1,True,True)]:
            doc,g,frame=NativeLineFTests().fixture(angle,mirror,negative,reversed_stem)
            g['metadata']=dict(source_sha256='S');g['nodes']=[]
            for edge in g['edges']:
                a,b=edge['attribute_paths'][0];names=[edge['edge_id']+'-A',edge['edge_id']+'-B']
                for nid,p in zip(names,(a,b)):g['nodes'].append(dict(node_id=nid,node_type='virtual_equipment',x=p[0],y=p[1]))
                edge.update(start_node_id=names[0],end_node_id=names[1])
            before=copy.deepcopy(g)
            with self.subTest(angle=angle,mirror=mirror,negative=negative):
                r=collect(doc,g,'S','G',annotation_config=dict(line_F_frames=[frame]))
                self.assertEqual({x['edge_id']:x['nominal_mm']for x in r['records']},{'supply':80,'return':100})
                self.assertEqual(g,before);self.assertFalse(r['annotation_barriers']);self.assertFalse(r['previous_DN_source_kernel_changed'])
                self.assertEqual(r['annotation_evidence']['inherited_consumed_stroke_handles'],sorted([frame['stem_handle']]+frame['bar_handles']))
    def test_changed_calibration_controls_are_excluded_by_geometry_without_filtering_side_or_DN(self):
        doc,original,policy=CalibratedDirectDNTests().fixture();space=doc.modelspace()
        line=space.add_line((2000,0),(2100,0),dxfattribs={'layer':'空调冷冻水供水'})
        text=space.add_text('DN80',dxfattribs={'layer':'空调平面','height':1,'insert':(2050,.5)})
        original['edges'].append(dict(edge_id='C5',system='supply',source_handles=[line.dxf.handle],attribute_paths=[[[2000,0],[2100,0]]]))
        policy['controls'].append(dict(text_handle=text.dxf.handle,expected_text='DN80',edge_id='C5',source_line_handle=line.dxf.handle))
        current=copy.deepcopy(original);current['edges'][0]['attribute_paths'][0][-1]=[110,0]
        config=dict(original_graph=original,original_graph_sha256='G',policy=policy)
        r=current_calibration(doc,current,config,'S','CURRENT')
        self.assertEqual([(x['edge_id'],x['nominal_mm'])for x in r['observations']],[('PS',150),('PR',80)])
        self.assertEqual(len(r['ineligible_original_controls']),1);self.assertFalse(r['controls_filtered_by_DN_or_normal_side'])
        current['edges'][1]['attribute_paths'][0][-1]=[110,200]
        with self.assertRaises(ValueError):current_calibration(doc,current,config,'S','CURRENT')
    def test_changed_target_never_inherits_the_original_control_scope_exception(self):
        doc,old,policy=CalibratedDirectDNTests().fixture();current=copy.deepcopy(old)
        current['edges'][-1]['source_handles']=['other']
        with self.assertRaisesRegex(ValueError,'Changed target'):current_calibration(doc,current,dict(original_graph=old,original_graph_sha256='G',policy=policy),'S','CURRENT')


if __name__=='__main__':unittest.main()
