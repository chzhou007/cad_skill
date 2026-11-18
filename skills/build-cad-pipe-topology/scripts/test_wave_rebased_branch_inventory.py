import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_match_inherited_circle_crossview_paths import fixture as branch_fixture
from test_inherited_wave_pair_continuity import fixture as wave_fixture
from inherited_wave_pair_continuity import inspect_pairs,reconstruct
from inherited_circle_branch_inventory import inspect as inspect_circle,MODE as CIRCLE_MODE
from wave_rebased_branch_inventory import rebuild,compute,implementation_hashes
from native_line_path_evidence import LAYERS
from confirm_crossview_paths import sha


def fixture(folder):
    args=branch_fixture(folder);docs,graphs,inventory,_,_,hashes=args;doc=docs['plan'];g=graphs['plan'];sh=hashes['plan']['source_sha256'];gh=hashes['plan']['graph_sha256'];m=doc.modelspace()
    g['sourceLayoutEquipmentOwnership']=dict(status='native_calibrated_logical_ownership_source_checked',records=[])
    selected=[]
    for row in inventory['records']:
        did=row['equipment_id'];node=next(n for n in g['nodes'] if n['node_id']==did)
        m.add_text(did,dxfattribs=dict(insert=(node['x'],node['y']),height=1))
        for system,state in row['views']['plan']['services'].items():
            eid=state['trace']['edges'][0];edge=next(e for e in g['edges'] if e['edge_id']==eid)
            owner=dict(source_sha256=sh,equipment_id=did,system=system,human_accepted=False,physical_port_verified=False,
                endpoint_snapshot={k:copy.deepcopy(edge[k]) for k in ('start_node_id','end_node_id','system','attribute_paths')})
            edge['source_layout_equipment_interface']=owner;g['sourceLayoutEquipmentOwnership']['records'].append(owner)
            selected.append(dict(equipment_id=did,system=system,edge_id=eid,node_id=state['trace']['tee']))
    block=doc.blocks.new('wave');block.add_lwpolyline([(-1,-10,-.5),(0,0,.5),(1,10,0)],format='xyb')
    waves=[m.add_blockref('wave',(1000,1000)),m.add_blockref('wave',(1102,1000))]
    for name,x in [('WX',900),('WA',1000),('WB',1100),('WY',1200)]:g['nodes'].append(dict(node_id=name,node_type='virtual_equipment',subtype='unresolved_source_terminal' if name in ('WA','WB') else 'unlocated_boundary',floor=3,system='supply',x=x,y=1000))
    for eid,a,b,coords in [('WE0','WX','WA',[[900,1000],[1000,1000]]),('WE1','WB','WY',[[1100,1000],[1200,1000]])]:
        line=m.add_line(*coords,dxfattribs=dict(layer=LAYERS['supply']))
        g['edges'].append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system='supply',path=coords,path_points=coords,attribute_paths=[coords],source_handles=[line.dxf.handle],path_length=100,equipment_names=[],equipment_counts={}))
    _,_,_,controls,wp,*_=wave_fixture();wp=dict(wp,pairs=[dict(nodes=['WA','WB'],wave_handles=[w.dxf.handle for w in waves],retained_edge='WE0')])
    proof=inspect_pairs(doc,g,controls,wp,sh,gh);after,_=reconstruct(g,[],proof,sh,gh)
    policy=dict(selections=selected)
    parent=copy.deepcopy(inventory);parent.update(status='source_comparison_inventory_not_mapping',counts=dict(equipment=3,ready_for_mapping_comparison=3),local_graphs_mutated=False,mapped_paths=0,human_accepted=False,hil_ready=False)
    extension=[]
    for row in parent['records']:
        for system in ('supply','return'):
            current=inspect_circle(doc,g,row['equipment_id'],system,sh,gh,policy);row['views']['plan']['services'][system]=current
            extension.append(dict(equipment_id=row['equipment_id'],system=system,source_evidence=copy.deepcopy(current)))
    parent['inherited_circle_branch_extension']=dict(mode=CIRCLE_MODE,records=extension)
    return doc,after,g,parent,policy,sh,gh,'N'*64


class Tests(unittest.TestCase):
    def test_fresh_plan_proofs_keep_ready_services_and_unchanged_axis_without_hash_relabel(self):
        with tempfile.TemporaryDirectory() as temp:
            args=fixture(Path(temp));old=copy.deepcopy(args[3]);result=rebuild(*args)
            self.assertEqual(args[3],old);self.assertEqual(result['counts'],dict(equipment=3,ready_for_mapping_comparison=3))
            for before,after in zip(old['records'],result['records']):
                self.assertEqual(before['views']['iso'],after['views']['iso'])
                for service in after['views']['plan']['services'].values():
                    self.assertEqual(service['junction_evidence']['graph_sha256'],'N'*64)
                    self.assertEqual(service['reviewed_circle_path_evidence']['input_graph_sha256'],'N'*64)
            for row in result['inherited_circle_branch_extension']['records']:self.assertEqual(row['source_evidence']['junction_evidence']['graph_sha256'],'N'*64)
            self.assertEqual(result['mapped_paths'],0);self.assertFalse(result['human_accepted'])

    def test_unrelated_equipment_edge_or_root_change_cannot_hide_inside_wave_adoption(self):
        for case in ('node','edge','owner','unpaired'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(fixture(Path(temp)));g=args[1]
                if case=='node':next(n for n in g['nodes'] if n['node_id']=='D0')['x']-=1
                elif case=='edge':g['edges'][0]['attribute_paths'][0][0][0]-=1
                elif case=='owner':g['sourceLayoutEquipmentOwnership']['status']='other'
                else:g['sourceInheritedWavePairContinuity']['dependent_mapping_attributes_and_HIL_invalidated']=False
                with self.assertRaises(ValueError):rebuild(*args)

    def test_previously_ready_source_branch_failure_is_blocking(self):
        with tempfile.TemporaryDirectory() as temp:
            args=fixture(Path(temp))
            with patch('wave_rebased_branch_inventory.inspect_circle',side_effect=ValueError('current native ray changed')),self.assertRaisesRegex(ValueError,'current native ray changed'):rebuild(*args)
            args=list(args);args[0].modelspace().add_text('D0',dxfattribs=dict(insert=(0,100),height=1))
            with self.assertRaisesRegex(ValueError,'previously ready equipment'):rebuild(*args)

    def test_receipt_binds_full_old_inventory_and_new_wave_native_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);parent=root/'parent';wave=root/'wave';parent.mkdir();wave.mkdir()
            paths=dict(parent_inventory=parent/'inventory.json',parent_receipt=parent/'inventory-receipt.json',wave_graph=wave/'graph_with_edges.json',wave_receipt=wave/'inherited-wave-receipt.json')
            import json
            for name,path in paths.items():path.write_text(json.dumps(dict(mode=CIRCLE_MODE)) if name=='parent_receipt' else '{}','utf8')
            policy={k+'_sha256':sha(v) for k,v in paths.items()}
            with patch('wave_rebased_branch_inventory.verify_parent',side_effect=ValueError('old native inventory changed')),self.assertRaisesRegex(ValueError,'old native inventory changed'):compute(paths,policy)
            policy['wave_graph_sha256']='stale'
            with self.assertRaisesRegex(ValueError,'dependency changed wave_graph'):compute(paths,policy)
        self.assertIn('wave_rebased_branch_inventory.py',implementation_hashes())
        self.assertIn('inherited_wave_pair_continuity.py',implementation_hashes())


if __name__=='__main__':unittest.main()
