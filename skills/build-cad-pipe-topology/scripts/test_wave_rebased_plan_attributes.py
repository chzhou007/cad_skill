import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from confirm_crossview_paths import encode,sha
from test_inherited_circle_plan_attributes import fixture
from wave_rebased_plan_attributes import BATCH_SCHEMA,attribute_groups,configuration,compute,check_result


def scenario(folder):
    doc,graph,mapping,scope,calibration,metric,sh,gh=fixture(folder)
    old=copy.deepcopy(calibration);old['graph_sha256']='old-native-parent'
    cp=folder/'calibration.json';mp=folder/'metric.json';cp.write_bytes(encode(old));mp.write_bytes(encode(metric))
    mapping.update(group_id='A',historical_mapping_lineage=[dict(previous_mapping_id=r['mapping_id'],current_mapping_id=r['mapping_id'],human_confirmation_transferred=False) for r in mapping['records']])
    batch=dict(mode=BATCH_SCHEMA,plan_graph_sha256=gh,iso_graph_sha256=mapping['iso_graph_sha256'],source_sha256=dict(plan=sh),
        physical_values_assigned=0,local_graphs_mutated=False,human_accepted=False,groups=[mapping],
        records=[dict(r,group_id='A') for r in mapping['records']],equipment_scope=mapping['equipment_scope'],
        evidence=dict(native_wave_inventory_rebase=dict(old_plan_graph_sha256='old-native-parent')))
    spec=dict(group_id='A',scope=scope,calibration_origin=dict(path=str(cp),sha256=sha(cp)),metric_origin=dict(path=str(mp),sha256=sha(mp)))
    return doc,graph,batch,dict(groups=[spec]),sh,gh


class Tests(unittest.TestCase):
    def test_native_recomputation_preserves_source_multiplicity_unknowns_and_branch_override(self):
        with tempfile.TemporaryDirectory() as temp:
            args=scenario(Path(temp));doc,graph,batch,policy,sh,gh=args;before=copy.deepcopy(graph)
            doc.modelspace().add_text('DN65',dxfattribs=dict(layer='AN',height=.2,rotation=0,insert=(-5,20.12)))
            result=attribute_groups(*args);rows={r['plan_edges'][0]:r for r in result['records']}
            self.assertEqual(graph,before);self.assertEqual(len(rows),10)
            self.assertEqual(rows['supplyB1']['diameter']['nominal_mm'],65)
            self.assertEqual(rows['supplyM1']['diameter']['nominal_mm'],150)
            self.assertFalse(result['old_calibration_acceptance_reused']);self.assertFalse(result['axis_conflicts_resolved'])
            self.assertEqual(result['whole_axis_DN_assigned'],0)
            self.assertTrue(all(r['whole_axis_physical_length_mm'] is None for r in result['records']))
            for state in result['groups'][0]['topology_contract']['source_main_projections'].values():
                self.assertEqual(len(state['canonical_source_projection']['source_entities']),2)

    def test_calibration_origin_and_explicit_seed_cannot_be_relabelled_as_acceptance(self):
        for case in ('file','source','parent','seed','component'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                _,_,_,policy,sh,gh=scenario(Path(temp));spec=policy['groups'][0];parent='old-native-parent'
                if case=='file':Path(spec['calibration_origin']['path']).write_text('{}','utf8')
                elif case=='source':sh='other-source'
                elif case=='parent':parent='other-parent'
                elif case=='seed':spec['scope']['seeds'][0]['expected_text']='DN900'
                else:spec['scope']['qualified_component_DN']={'labels':[]}
                with self.assertRaises(ValueError):configuration(spec,sh,gh,parent)

    def test_stale_scope_missing_corridor_flattening_or_physical_claim_blocks(self):
        for case in ('graph','source','group','records','physical','accepted'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(scenario(Path(temp)));batch=args[2]
                if case=='graph':batch['plan_graph_sha256']='stale'
                elif case=='source':batch['source_sha256']['plan']='stale'
                elif case=='group':args[3]['groups']=[]
                elif case=='records':batch['records'].pop()
                elif case=='physical':batch['physical_values_assigned']=1
                else:batch['human_accepted']=True
                with self.assertRaises(ValueError):attribute_groups(*args)

    def test_independent_corridors_must_not_write_same_plan_edges_twice(self):
        with tempfile.TemporaryDirectory() as temp:
            args=list(scenario(Path(temp)));batch=args[2];second=copy.deepcopy(batch['groups'][0]);second['group_id']='B'
            for row in second['records']:row['mapping_id']='B-'+row['mapping_id']
            batch['groups'].append(second);batch['records']=[dict(r,group_id=g['group_id']) for g in batch['groups'] for r in g['records']]
            spec=copy.deepcopy(args[3]['groups'][0]);spec['group_id']='B';args[3]['groups'].append(spec)
            with self.assertRaisesRegex(ValueError,'writer overlaps'):attribute_groups(*args)

    def test_entry_replays_mapping_owner_before_using_local_payload(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);paths=dict(mapping=root/'mapping.json',mapping_receipt=root/'source-mapping-receipt.json')
            for p in paths.values():p.write_text('{}','utf8')
            policy={k+'_sha256':sha(v) for k,v in paths.items()}
            with patch('wave_rebased_plan_attributes.verify_mapping',side_effect=ValueError('native mapping changed')),self.assertRaisesRegex(ValueError,'native mapping changed'):
                compute(paths,policy)
            policy['mapping_sha256']='stale'
            with self.assertRaisesRegex(ValueError,'input changed mapping'):compute(paths,policy)

    def test_result_gate_keeps_conflicts_pending_and_rejects_whole_edge_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            result=attribute_groups(*scenario(Path(temp)));result['mapping_sha256']='current-mapping'
            checked=check_result(result)
            self.assertEqual(checked['mapped_DN_XY_scopes'],10);self.assertFalse(checked['hil_ready'])
            changed=copy.deepcopy(result);changed['groups'][0]['records'][0]['horizontal_projection']['installed_whole_edge_length_mm']=10
            with self.assertRaisesRegex(ValueError,'escaped its source DN/XY'):check_result(changed)
            changed=copy.deepcopy(result);changed['axis_conflicts_resolved']=True
            with self.assertRaisesRegex(ValueError,'source-only state'):check_result(changed)


if __name__=='__main__':unittest.main()
