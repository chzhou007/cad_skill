import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import match_known_junction_direct_mains as owner


def fixture(system='supply', suffix=''):
    graphs={};records=[]
    for view,prefix in [('plan','P'),('iso','I')]:
        def nid(value):return prefix+value+suffix
        ns=[dict(node_id=nid('T'+str(i)),node_type='tee',floor=2,x=i*100,y=0) for i in (1,2)]
        ns += [dict(node_id=nid(kind+str(i)),node_type='equipment' if kind=='D' else 'virtual_equipment',floor=2,x=i*100,y=10)
               for kind in ('D','U') for i in (1,2)]
        es=[]
        for i in (1,2):
            for kind in ('D','U'):
                es.append(dict(edge_id=nid(kind+'B'+str(i)),start_node_id=nid('T'+str(i)),end_node_id=nid(kind+str(i)),
                    system=system,attribute_paths=[[[i*100,0],[i*100,10]]]))
        es.append(dict(edge_id=nid('MAIN'),start_node_id=nid('T1'),end_node_id=nid('T2'),system=system,
                       attribute_paths=[[[100,0],[200,0]]]))
        graphs[view]=dict(nodes=ns,edges=es)
    for i in (1,2):
        row=dict(mapping_id='A'+str(i)+suffix,floor=2,system=system,kind='equipment_branch')
        for view,prefix in [('plan','P'),('iso','I')]:
            row[view+'_edges']=[prefix+'DB'+str(i)+suffix]
            row[view+'_start']=prefix+'T'+str(i)+suffix;row[view+'_end']=prefix+'D'+str(i)+suffix
            row[view+'_snapshot']=owner.selected_snapshot(graphs[view],row[view+'_edges'])
        records.append(row)
    return graphs,records


class DirectMainTests(unittest.TestCase):
    def test_existing_endpoint_identity_adds_only_missing_direct_main(self):
        gs,parents=fixture();before=copy.deepcopy((gs,parents))
        rows,pending=owner.discover(gs,parents,2)
        self.assertEqual([(r['plan_edges'],r['iso_edges']) for r in rows],[(['PMAIN'],['IMAIN'])])
        self.assertEqual(pending,[]);self.assertFalse(rows[0]['human_accepted'])
        self.assertFalse(rows[0]['shortest_path_or_nearest_geometry_used'])
        self.assertEqual((gs,parents),before)

    def test_reversed_axis_storage_keeps_the_parent_endpoint_correspondence(self):
        gs,parents=fixture();e=gs['iso']['edges'][-1]
        e['start_node_id'],e['end_node_id']=e['end_node_id'],e['start_node_id']
        e['attribute_paths'][0].reverse()
        rows,_=owner.discover(gs,parents,2)
        self.assertEqual((rows[0]['iso_start'],rows[0]['iso_end']),('IT1','IT2'))

    def test_same_source_positions_do_not_mix_supply_and_return(self):
        gs,parents=fixture();other,extra=fixture('return','R')
        for view in gs:
            gs[view]['nodes']+=other[view]['nodes'];gs[view]['edges']+=other[view]['edges']
        rows,pending=owner.discover(gs,parents+extra,2)
        self.assertEqual({(r['system'],r['plan_edges'][0],r['iso_edges'][0]) for r in rows},
                         {('supply','PMAIN','IMAIN'),('return','PMAINR','IMAINR')})
        self.assertEqual(pending,[])

    def test_parent_labels_cannot_override_the_actual_branch_endpoint(self):
        gs,parents=fixture();parents[0]['iso_start']='IT2'
        with self.assertRaisesRegex(ValueError,'order or service'):
            owner.discover(gs,parents,2)

    def test_parent_path_snapshot_change_blocks(self):
        gs,parents=fixture();gs['plan']['edges'][0]['attribute_paths'][0][1][0]+=1
        with self.assertRaisesRegex(ValueError,'snapshot'):
            owner.discover(gs,parents,2)

    def test_repeated_parent_mapping_identity_blocks(self):
        gs,parents=fixture();parents.append(copy.deepcopy(parents[0]))
        with self.assertRaisesRegex(ValueError,'unique mapping'):
            owner.discover(gs,parents,2)

    def test_repeated_parent_local_writer_blocks(self):
        gs,parents=fixture();row=copy.deepcopy(parents[0]);row['mapping_id']='OTHER';parents.append(row)
        with self.assertRaisesRegex(ValueError,'writer repeated'):
            owner.discover(gs,parents,2)

    def test_missing_axis_edge_remains_unpaired(self):
        gs,parents=fixture();gs['iso']['edges'].pop()
        rows,pending=owner.discover(gs,parents,2)
        self.assertEqual(rows,[]);self.assertTrue(pending)

    def test_parallel_edges_do_not_select_the_closest_or_first(self):
        gs,parents=fixture();e=copy.deepcopy(gs['iso']['edges'][-1]);e['edge_id']='PARALLEL';gs['iso']['edges'].append(e)
        with self.assertRaisesRegex(ValueError,'qualified'):
            owner.discover(gs,parents,2)

    def test_system_conflict_blocks_a_degree_three_contact(self):
        gs,parents=fixture();gs['iso']['edges'][-1]['system']='return'
        rows,pending=owner.discover(gs,parents,2)
        self.assertEqual(rows,[]);self.assertTrue(pending)

    def test_same_labels_on_wrong_floor_cannot_seed_mapping(self):
        gs,parents=fixture()
        for n in gs['iso']['nodes']:n['floor']=3
        with self.assertRaisesRegex(ValueError,'snapshot'):
            owner.discover(gs,parents,2)

    def test_equipment_to_equipment_edge_is_not_a_direct_main(self):
        gs,parents=fixture()
        for view,prefix in [('plan','P'),('iso','I')]:
            gs[view]['edges'][-1].update(start_node_id=prefix+'D1',end_node_id=prefix+'D2')
        rows,_=owner.discover(gs,parents,2);self.assertEqual(rows,[])

    def test_bool_is_not_an_explicit_floor(self):
        gs,parents=fixture()
        with self.assertRaisesRegex(ValueError,'floor'):
            owner.discover(gs,parents,True)

    def test_ambiguous_native_pipe_witness_cannot_be_promoted(self):
        gs,parents=fixture();rows,_=owner.discover(gs,parents,2)
        local={v+'_'+key:dict(path='unused',sha256=key) for v in gs for key in ('source','graph')}
        origin=dict(confirmation_basis='source_geometry_calibrated',expert_evidence='actual pinned source')
        bad=dict(edges=[dict(segments=[dict(status='ambiguous_multiple_witnesses')])])
        with patch.object(owner,'native_tee',return_value={}),patch.object(owner,'line_coverage',return_value=bad):
            with self.assertRaisesRegex(ValueError,'unique native pipe'):
                owner.read_paths(dict(plan=None,iso=None),gs,rows,local,origin)

    def test_source_junction_failure_blocks_even_when_graphs_look_identical(self):
        gs,parents=fixture();rows,_=owner.discover(gs,parents,2)
        local={v+'_'+key:dict(path='unused',sha256=key) for v in gs for key in ('source','graph')}
        origin=dict(confirmation_basis='source_geometry_calibrated',expert_evidence='actual pinned source')
        with patch.object(owner,'native_tee',side_effect=ValueError('missing native rays')):
            with self.assertRaisesRegex(ValueError,'native rays'):
                owner.read_paths(dict(plan=None,iso=None),gs,rows,local,origin)

    def test_changed_input_hash_fails_before_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'mapping.json';p.write_text('{}',encoding='utf-8')
            with patch.object(owner,'verify_parent') as replay:
                with self.assertRaisesRegex(ValueError,'dependency changed'):
                    owner.compute(dict(paired=p),dict(paired_sha256='wrong'))
                replay.assert_not_called()

    def test_technical_mapping_does_not_accept_floor_or_human_review(self):
        gs,parents=fixture();rows,_=owner.discover(gs,parents,2);rows[0]['mapping_id']='NEW-1'
        data=dict(mode=owner.MODE,status='native_direct_known_junction_mains_attributes_pending',records=rows,
            local_graphs_mutated=False,physical_values_fused=False,whole_floor_connectivity_confirmed=False,human_accepted=False,hil_ready=False)
        self.assertEqual(owner.check_result(data)['source_replay'],'passed')
        for key in ('physical_values_fused','whole_floor_connectivity_confirmed','human_accepted','hil_ready'):
            altered=copy.deepcopy(data);altered[key]=True
            with self.subTest(key=key),self.assertRaises(ValueError):owner.check_result(altered)


if __name__=='__main__':unittest.main()
