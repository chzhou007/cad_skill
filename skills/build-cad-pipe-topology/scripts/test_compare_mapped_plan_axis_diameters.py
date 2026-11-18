import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from confirm_crossview_paths import sha
from test_native_repeated_branch_DN_layout import fixture
from native_repeated_branch_DN_layout import collect
from match_source_checked_crossview_paths import selected_snapshot
from compare_mapped_plan_axis_diameters import compare,compute,check_result,ATTRIBUTE_MODE,BATCH_SCHEMA


def scenario():
    doc,axis,targets,_=fixture();ownership=collect(doc,axis,targets,'S','G');rows=[];values=[]
    for i,(eid,system,kind) in enumerate([('supply4','supply','equipment_branch'),('return4','return','equipment_branch'),('supply0','supply','main_between_equipment_branches')]):
        row=dict(mapping_id='M'+str(i),group_id='A',kind=kind,floor=2,system=system,plan_edges=['P'+str(i)],iso_edges=[eid],iso_snapshot=selected_snapshot(axis,[eid]))
        rows.append(row);values.append(dict(row,diameter=dict(edge_id='P'+str(i),system=system,nominal_mm=150,lineage=[dict(source='native-plan-T-seed')])))
    mapping=dict(mode=BATCH_SCHEMA,records=rows,plan_graph_sha256='PG',iso_graph_sha256='G',source_sha256=dict(plan='PS',iso='S'))
    attributes=dict(mode=ATTRIBUTE_MODE,records=values,graph_sha256='PG',iso_graph_sha256='G',source_sha256='PS',physical_values_fused=False,human_accepted=False)
    return mapping,attributes,axis,ownership


class Tests(unittest.TestCase):
    def test_native_independent_layout_exposes_differences_without_proving_equal_extents(self):
        args=scenario();before=copy.deepcopy(args);out=compare(*args)
        self.assertEqual(args,before);self.assertEqual(out['difference_paths'],2);self.assertEqual(out['annotated_paths'],2)
        self.assertEqual(out['paths_without_selected_axis_annotations'],1)
        self.assertEqual(out['DN_fusion_blocked_mapping_ids'],['M0','M1'])
        self.assertFalse(out['source_contradictions_confirmed']);self.assertFalse(out['physical_values_fused'])
        self.assertEqual(out['records'][2]['status'],'no_selected_native_axis_annotation_not_an_agreement')
        self.assertTrue(all(r['physical_length_mm'] is None and not r['whole_axis_DN_selected'] for r in out['records']))

    def test_matching_numeric_DN_does_not_prove_matching_segment_extents(self):
        args=list(scenario());args[1]['records'][0]['diameter']['nominal_mm']=80;result=compare(*args)
        self.assertEqual(result['difference_paths'],1)
        self.assertEqual(result['records'][0]['status'],'same_local_values_extents_still_unproven')
        self.assertFalse(result['records'][0]['equal_segment_extents_proved'])

    def test_comparison_gate_preserves_unexamined_scope_and_detects_false_resolution(self):
        result=compare(*scenario());result.update(mapping_sha256='M',attributes_sha256='A')
        checked=check_result(result);self.assertEqual(checked['DN_difference_paths'],2);self.assertEqual(checked['paths_without_selected_axis_annotations'],1)
        for case in ('claimed','counts','length'):
            changed=copy.deepcopy(result)
            if case=='claimed':changed['source_contradictions_confirmed']=True
            elif case=='counts':changed['difference_paths']=0
            else:changed['records'][0]['physical_length_mm']=100
            with self.subTest(case=case),self.assertRaises(ValueError):check_result(changed)

    def test_stale_snapshots_ownership_reused_targets_mixed_systems_or_missing_controls_fail(self):
        for case in ('plan_hash','axis_hash','source','snapshot','controls','self_control','owner','system','duplicate','missing_value'):
            with self.subTest(case=case):
                args=list(scenario());mapping,attributes,axis,ownership=args;proof=ownership['records'][0]
                if case=='plan_hash':attributes['graph_sha256']='old'
                elif case=='axis_hash':ownership['graph_sha256']='old'
                elif case=='source':ownership['source_sha256']='other'
                elif case=='snapshot':axis['edges'][-2]['attribute_paths'][0][0][0]+=1
                elif case=='controls':proof['independent_control_roots']=proof['independent_control_roots'][:3]
                elif case=='self_control':proof['independent_control_text_handles'].append(ownership['records'][1]['source_text']['handle'])
                elif case=='owner':proof['native_binding']['current_graph_owners'].append('competing')
                elif case=='system':proof['native_binding']['layer']='other-system'
                elif case=='duplicate':ownership['records'].append(copy.deepcopy(proof))
                else:attributes['records'].pop()
                with self.assertRaises(ValueError):compare(*args)

    def test_entry_requires_complete_current_attribute_owner_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);paths=dict(attributes=root/'wave-plan-attributes.json',attribute_receipt=root/'wave-plan-attribute-receipt.json')
            for path in paths.values():path.write_text('{}','utf8')
            policy={key+'_sha256':sha(path) for key,path in paths.items()}
            with patch('compare_mapped_plan_axis_diameters.verify_attributes',side_effect=ValueError('native attributes changed')),self.assertRaisesRegex(ValueError,'native attributes changed'):
                compute(paths,policy)


if __name__=='__main__':unittest.main()
