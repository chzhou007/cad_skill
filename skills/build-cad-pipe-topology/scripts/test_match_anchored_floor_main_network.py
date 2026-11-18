import copy,tempfile,unittest
from pathlib import Path
from test_match_inherited_circle_crossview_paths import fixture
from crossview_equipment_branch_inventory import service_route
from match_anchored_floor_main_network import match_structure,historical_lineage,protected_floor_attributes,compute
from confirm_crossview_paths import encode,sha

class Tests(unittest.TestCase):
    def setup(self,folder):
        docs,graphs,inventory,ip,policy,hashes=fixture(folder)
        return graphs,inventory,hashes
    def test_geometry_and_local_IDs_are_not_correspondence_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            graphs,inventory,_=self.setup(Path(temp));before=copy.deepcopy(graphs)
            iso=graphs['iso'];rename={n['node_id']:'OTHER-'+n['node_id'] for n in iso['nodes'] if n['node_type']=='tee'}
            for n in iso['nodes']:n['node_id']=rename.get(n['node_id'],n['node_id'])
            for e in iso['edges']:
                for k in ('start_node_id','end_node_id'):e[k]=rename.get(e[k],e[k])
            for r in inventory['records']:
                for s in ('supply','return'):r['views']['iso']['services'][s]['trace']=service_route(iso,r['equipment_id'],s)
            snapshot=copy.deepcopy(graphs);result=match_structure(graphs,inventory,3,['D0','D1','D2'])
            self.assertEqual(graphs,snapshot);self.assertEqual(len(result['pairs']),4);self.assertEqual(len(result['node_mapping']),6)
            self.assertTrue(all(v==rename[k] for k,v in result['node_mapping'].items()));self.assertFalse(result['physical_direction_inferred'])
    def test_wrong_order_system_floor_unready_or_shared_service_is_blocking(self):
        for case in ('order','system','floor','unready','shared'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                graphs,inv,_=self.setup(Path(temp));iso=graphs['iso']
                if case=='order':
                    a=next(e for e in iso['edges'] if e['edge_id']=='supplyB0');b=next(e for e in iso['edges'] if e['edge_id']=='supplyB1')
                    a['start_node_id'],b['start_node_id']=b['start_node_id'],a['start_node_id']
                    for r in inv['records']:r['views']['iso']['services']['supply']['trace']=service_route(iso,r['equipment_id'],'supply')
                elif case=='system':iso['edges'][0]['system']='return'
                elif case=='floor':next(n for n in iso['nodes'] if n['node_id']=='supply1')['floor']=2
                elif case=='unready':inv['records'][0]['ready_for_mapping_comparison']=False
                else:inv['records'][1]['views']['plan']['services']['supply']['trace']=inv['records'][0]['views']['plan']['services']['supply']['trace']
                with self.assertRaises(ValueError):match_structure(graphs,inv,3,['D0','D1','D2'])
    def test_unanchored_component_or_unresolved_symmetry_is_not_guessed(self):
        for case in ('unanchored','symmetric'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                graphs,inv,_=self.setup(Path(temp))
                for g in graphs.values():
                    for nid in ['A','B','U','V']:g['nodes'].append(dict(node_id=nid,node_type='tee',floor=3,x=0,y=0))
                    if case=='unanchored':pairs=[('A','B'),('A','U'),('A','V'),('B','U'),('B','V'),('U','V')]
                    else:
                        e=next(e for e in g['edges'] if e['edge_id']=='supplyM1');g['edges'].remove(e)
                        pairs=[(e['start_node_id'],'A'),(e['end_node_id'],'B'),('A','U'),('A','V'),('B','U'),('B','V'),('U','X'),('V','Y')]
                        for nid in ['X','Y']:g['nodes'].append(dict(node_id=nid,node_type='virtual_equipment',floor=3,x=0,y=0))
                    for i,(a,b) in enumerate(pairs):g['edges'].append(dict(edge_id='EXTRA'+str(i),start_node_id=a,end_node_id=b,system='supply'))
                with self.assertRaises(ValueError):match_structure(graphs,inv,3,['D0','D1','D2'])
    def test_count_equality_does_not_hide_changed_network_adjacency(self):
        with tempfile.TemporaryDirectory() as temp:
            graphs,inv,_=self.setup(Path(temp));e=next(e for e in graphs['iso']['edges'] if e['edge_id']=='supplyM1');e['end_node_id']='supply2'
            with self.assertRaises(ValueError):match_structure(graphs,inv,3,['D0','D1','D2'])
    def test_changed_dependency_fails_before_native_inventory_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'inventory.json';p.write_bytes(encode({}))
            with self.assertRaisesRegex(ValueError,'dependency changed inventory'):compute(dict(inventory=p),dict(inventory_sha256='stale'))
    def test_named_segment_history_is_preserved_and_must_agree_with_the_network(self):
        for case in ('valid','node','points','missing'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp);graphs,inv,hashes=self.setup(folder);structure=match_structure(graphs,inv,3,['D0','D1','D2']);pair=structure['pairs'][0]
                records=[dict(mapping_id='M'+str(i),plan_edges=[r['plan_edge']],iso_edges=[r['iso_edge']]) for i,r in enumerate(structure['pairs'])]
                axis=next(e for e in graphs['iso']['edges'] if e['edge_id']==pair['iso_edge'])
                attr=dict(mapping_id='NAMED',floor=3,edge_id=pair['iso_edge'],plan_network_T=pair['plan_start'],axis_network_T=pair['iso_start'],plan_edges=[pair['plan_edge']],
                    path_index=0,segment_indices=[0],scope_points=copy.deepcopy(axis['attribute_paths'][0]),whole_local_edge=True,nominal_mm=200,physical_length_mm=None)
                cross=dict(floor=3,source_scope_mapping_id='G01-SC',source_hashes=dict(plan_graph=hashes['plan']['graph_sha256'],local_iso_graph=hashes['iso']['graph_sha256']))
                data=dict(provenance=dict(sha256=hashes['iso']['source_sha256']),edges=[dict(edge_id=axis['edge_id'],cross_view_attributes=cross,plan_segment_attributes=[attr])])
                if case=='node':attr['axis_network_T']='WRONG'
                elif case=='points':attr['scope_points'][0][0]-=1
                elif case=='missing':data['edges'][0].pop('cross_view_attributes')
                p=folder/'protected.json';p.write_bytes(encode(data));spec=dict(path=str(p),sha256=sha(p));lineage=[dict(group_id='G01',previous_mapping_id='SC')]
                if case=='valid':
                    result=protected_floor_attributes(p,spec,graphs,structure,lineage,records,hashes)
                    self.assertEqual(result['old_group_attributes_preserved'],1);self.assertEqual(result['named_segment_snapshots'],[attr]);self.assertFalse(result['attributes_rewritten'])
                else:
                    with self.assertRaises(ValueError):protected_floor_attributes(p,spec,graphs,structure,lineage,records,hashes)

if __name__=='__main__':unittest.main()
