import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from confirm_crossview_paths import sha
from test_inherited_circle_plan_attributes import fixture
from inherited_circle_plan_attributes import attribute
from adopt_wave_rebased_plan_scopes import adopt,partial_attribute,compute,ROOT


def scenario(folder):
    args=fixture(folder);plan=args[1];mapping=args[2];values=attribute(*args);mapping=copy.deepcopy(mapping)
    raw_edges={};raw_nodes={}
    for row in mapping['records']:
        for edge in row['iso_snapshot']['edges']:raw_edges[edge['edge_id']]=copy.deepcopy(edge)
        for node in row['iso_snapshot']['nodes']:raw_nodes[node['node_id']]=copy.deepcopy(node)
    local=dict(nodes=list(raw_nodes.values()),edges=list(raw_edges.values()),metadata=dict(source_sha256=mapping['source_sha256']['iso']))
    extra=copy.deepcopy(local['edges'][0]);extra.update(edge_id='UNRELATED',equipment_counts={'valve':2});local['edges'].append(extra)
    parent=copy.deepcopy(local);parent['sourceLowerFloorPlanSegmentAttributes']={'records':['retained-floor1-proof']};parent['sourceAxisRiserSegmentAttributes']={'records':['retained-vertical-proof']}
    parent['edges'][-1]['axis_riser_attributes']=[dict(nominal_mm=450,physical_length_mm=None)]
    hashes=dict(mapping='a'*64,attributes='b'*64,comparison='c'*64,parent_graph='d'*64)
    values.update(mapping_sha256=hashes['mapping'],iso_graph_sha256=mapping['iso_graph_sha256'])
    mapping['evidence']['native_wave_inventory_rebase']={'old_plan_graph_sha256':'OLD-PLAN'}
    pe={e['edge_id']:e for e in parent['edges']};sources=dict(plan=mapping['source_sha256']['plan'],isometric=mapping['source_sha256']['iso'],plan_graph='OLD-PLAN',local_iso_graph=mapping['iso_graph_sha256']);old=[]
    by={r['mapping_id']:r for r in values['records']}
    for index,row in enumerate(mapping['records'][:2]):
        c=partial_attribute(row,by[row['mapping_id']],sources,'e'*64,'f'*64);c['mapping_id']='HIST'+str(index);old.append(c['mapping_id']);pe[row['iso_edges'][0]]['cross_view_attributes']=c
    comparison=dict(mapping_sha256=hashes['mapping'],attributes_sha256=hashes['attributes'],plan_graph_sha256=mapping['plan_graph_sha256'],iso_graph_sha256=mapping['iso_graph_sha256'],
        physical_values_fused=False,source_contradictions_confirmed=False,human_accepted=False,
        records=[dict(row,whole_axis_DN_fusion_blocked=False) for row in mapping['records']])
    domains=dict(graph_sha256=mapping['iso_graph_sha256'],source_sha256=mapping['source_sha256']['iso'],graph_mutated=False,physical_values_assigned=0,records=[])
    return parent,local,plan,mapping,values,comparison,domains,dict(retained_historical_mapping_ids=old),hashes


class Tests(unittest.TestCase):
    def test_old_provenance_is_retained_and_fresh_child_proof_adds_only_partial_scopes(self):
        with tempfile.TemporaryDirectory() as temp:
            args=scenario(Path(temp));before=copy.deepcopy(args);out,proof=adopt(*args);self.assertEqual(args,before)
            self.assertEqual(proof['retained_historical_attributes'],2);self.assertEqual(proof['added_partial_attributes'],8)
            self.assertEqual(out['nodes'],args[0]['nodes']);self.assertEqual(out['edges'][-1],args[0]['edges'][-1])
            self.assertEqual(out['sourceLowerFloorPlanSegmentAttributes'],args[0]['sourceLowerFloorPlanSegmentAttributes']);self.assertEqual(out['sourceAxisRiserSegmentAttributes'],args[0]['sourceAxisRiserSegmentAttributes'])
            old={e['edge_id']:e for e in args[0]['edges']}
            for edge in out['edges']:
                current=edge.get('cross_view_attributes')
                if not current:continue
                if 'cross_view_attributes' in old[edge['edge_id']]:
                    self.assertEqual({k:v for k,v in current.items() if k!='current_plan_scope_evidence'},old[edge['edge_id']]['cross_view_attributes'])
                    self.assertEqual(current['source_hashes']['plan_graph'],'OLD-PLAN')
                self.assertEqual(current['current_plan_scope_evidence']['plan_graph_sha256'],args[3]['plan_graph_sha256'])
                self.assertIsNone(current['whole_edge_physical_length_mm']);self.assertIsNone(current['diameter']['nominal_mm'])
                self.assertFalse(current['current_plan_scope_evidence']['related_HIL_confirmation_inherited'])
            self.assertEqual(proof['whole_DN_or_lengths_added'],0);self.assertFalse(out['metadata']['hil_ready'])

    def test_changed_old_DN_metric_or_source_and_lost_historical_scope_block_adoption(self):
        for case in ('DN','metric','source','history','whole'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(scenario(Path(temp)));row=args[3]['records'][0];eid=row['iso_edges'][0];edge=next(e for e in args[0]['edges'] if e['edge_id']==eid);c=edge['cross_view_attributes']
                if case=='DN':c['diameter']['plan_drawn_nominal_mm']=125
                elif case=='metric':c['horizontal_projection']['pieces'][0]['points'][0][0]+=1
                elif case=='source':c['source_hashes']['plan_graph']='fake-current'
                elif case=='history':args[7]['retained_historical_mapping_ids'].pop()
                else:
                    c['diameter']['selected_physical_diameter']=True;args[5]['records'][0]['whole_axis_DN_fusion_blocked']=True
                with self.assertRaises(ValueError):adopt(*args)

    def test_stale_current_scope_local_geometry_components_or_competing_writer_fail(self):
        for case in ('attribute','comparison','component','node','local_path','duplicate'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(scenario(Path(temp)))
                if case=='attribute':args[4]['mapping_sha256']='old'
                elif case=='comparison':args[5]['attributes_sha256']='old'
                elif case=='component':args[0]['edges'][-1]['equipment_counts']['valve']=1
                elif case=='node':args[0]['nodes'][0]['x']+=1
                elif case=='local_path':args[3]['records'][0]['plan_snapshot']['edges'][0]['attribute_paths'][0][0][0]+=1
                else:args[3]['records'].append(copy.deepcopy(args[3]['records'][0]))
                with self.assertRaises(ValueError):adopt(*args)

    def test_entry_replays_complete_current_comparison_before_parent_adoption(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);paths=dict(parent_graph=folder/'graph.json',devices=folder/'devices.csv',comparison=folder/'DN-comparison.json',comparison_receipt=folder/'DN-comparison-receipt.json')
            for path in paths.values():path.write_text('{}','utf8')
            policy={key+'_sha256':sha(path) for key,path in paths.items()}
            with patch('compare_mapped_plan_axis_diameters.verify_output',side_effect=ValueError('native comparison changed')),self.assertRaisesRegex(ValueError,'native comparison changed'):
                compute(paths,policy)


if __name__=='__main__':unittest.main()
