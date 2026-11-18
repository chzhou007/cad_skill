import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from source_stable_junction_reapplication import unchanged_star,prepare,transition,CONFIG_ERROR
from confirm_crossview_paths import sha,encode

def fixture(angle=0,mirror=1):
    import math
    def point(x,y):
        a=math.radians(angle);return [mirror*x*math.cos(a)-y*math.sin(a),mirror*x*math.sin(a)+y*math.cos(a)]
    nodes=[];edges=[]
    for nid,xy in [('T',(0,0)),('L',(-10,0)),('R',(10,0)),('B',(0,10))]:
        p=point(*xy);nodes.append(dict(node_id=nid,node_type='tee',system='supply',floor=2,x=p[0],y=p[1]))
        if nid!='T':edges.append(dict(edge_id=nid,start_node_id='T',end_node_id=nid,system='supply',attribute_paths=[[point(0,0),p]],source_handles=['源线-'+nid]))
    return dict(metadata=dict(source_sha256='S'),nodes=nodes,edges=edges)

class Tests(unittest.TestCase):
    def pin(self,root,name,value):
        p=root/name;p.write_bytes(encode(value));return dict(path=str(p),sha256=sha(p))

    def test_exact_local_scope_supports_rotation_mirror_and_Chinese_sources(self):
        for angle,mirror in[(0,1),(90,1),(180,-1),(270,-1)]:
            before=fixture(angle,mirror);current=copy.deepcopy(before);current['unrelated_owner']={'new':'设备归属'}
            proof=unchanged_star(before,current,'T');self.assertEqual(proof['incident_edges'],['B','L','R']);self.assertEqual(current['edges'],before['edges'])

    def test_neighbor_incidence_source_or_submillimeter_geometry_change_requires_requalification(self):
        original=fixture()
        for change in('source','system','neighbor','path','new_arm','node_review'):
            current=copy.deepcopy(original)
            if change=='source':current['metadata']['source_sha256']='OTHER'
            elif change=='system':current['edges'][0]['system']='return'
            elif change=='neighbor':current['nodes'][1]['node_type']='virtual_equipment'
            elif change=='path':current['edges'][0]['attribute_paths'][0][1][0]+=.001
            elif change=='new_arm':current['edges'].append(dict(current['edges'][0],edge_id='FOURTH'))
            else:current['nodes'][0]['review_required']=True
            with self.subTest(change=change),self.assertRaises(ValueError):unchanged_star(original,current,'T')

    def test_guarded_reader_replays_both_native_roles_and_keeps_actual_current_hash(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);source=self.pin(root,'source.json',{});old=fixture();old['metadata']['source_sha256']=source['sha256'];previous=self.pin(root,'old.json',old);current=copy.deepcopy(old);current['owner_extension']={'proof':'新设备'};gs=self.pin(root,'new.json',current);config=dict(plans=[dict(inputs=dict(source=source,graph=previous))]);derived=copy.deepcopy(config);derived['plans'][0]['inputs']['graph']=gs
            rays=dict(junctions=[dict(node_id='T',source_rays=[dict(handle=n)for n in('A','B','C')])],graph_sha256=gs['sha256'])
            direct=lambda *args:(_ for _ in()).throw(ValueError(CONFIG_ERROR))
            old_reader=lambda *args:dict(rays,graph_sha256=previous['sha256'])
            new_reader=lambda *args:copy.deepcopy(rays)
            binding=dict(original_graph=previous,current_graph=gs,native_owner_replayed=True)
            with patch('source_stable_junction_reapplication.current_plan_reader',side_effect=[direct,old_reader]),patch('source_stable_junction_reapplication.transition',return_value=(config['plans'][0],derived,binding))as replay,patch('source_stable_junction_reapplication.make_reader',return_value=new_reader):
                reader=prepare(config,source,gs,current,{'path':'audit'});result=reader(None,current,'T',source['sha256'],gs['sha256']);self.assertEqual(result['graph_sha256'],gs['sha256']);self.assertTrue(result['native_prior_and_current_rays_equal']);self.assertEqual(result['physical_values_assigned'],0);replay.assert_called_once()
                with self.assertRaisesRegex(ValueError,'escaped'):reader(None,current,'T',source['sha256'],previous['sha256'])
            with patch('source_stable_junction_reapplication.current_plan_reader',return_value=direct),patch('source_stable_junction_reapplication.transition',return_value=(config['plans'][0],derived,binding)),patch('source_stable_junction_reapplication.make_reader',return_value=lambda *args:dict(junctions=[])):
                with patch('source_stable_junction_reapplication.current_plan_reader',side_effect=[direct,old_reader]):
                    reader=prepare(config,source,gs,current,{'path':'audit'})
                    with self.assertRaisesRegex(ValueError,'rays changed'):reader(None,current,'T',source['sha256'],gs['sha256'])

    def test_geometry_errors_never_trigger_configuration_fallback(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);source=self.pin(root,'source.json',{});graph=fixture();gs=self.pin(root,'graph.json',graph)
            with patch('source_stable_junction_reapplication.current_plan_reader',return_value=lambda *args:(_ for _ in()).throw(ValueError('ambiguous native ray'))),patch('source_stable_junction_reapplication.transition')as replay:
                reader=prepare({'plans':[]},source,gs,graph)
                with self.assertRaisesRegex(ValueError,'ambiguous'):reader(None,graph,'T',source['sha256'],gs['sha256'])
                replay.assert_not_called()

    def test_transition_requires_native_owner_parent_and_conserved_component_inventory(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);source=self.pin(root,'source.json',{});old=self.pin(root,'old.json',fixture());new=self.pin(root,'graph_with_edges.json',dict(fixture(),new_owner=True));devices=self.pin(root,'devices.json',{});m=self.pin(root,'manifest.json',dict(inputs=dict(graph=old,source=source,devices=devices)));audit=self.pin(root,'ordered-owner-audit.json',dict(mode='complete_native_row_order_sideview_ownership_v1',manifest=m,output_graph_sha256=new['sha256'],output_devices_sha256=devices['sha256']));config=dict(plans=[dict(inputs=dict(graph=old,source=source,devices=devices))]);before=copy.deepcopy(config)
            with patch('source_stable_junction_reapplication.verify_once',return_value=dict(output_graph_sha256=new['sha256']))as replay:
                _,derived,binding=transition(config,source,new,audit);self.assertEqual(config,before);self.assertEqual(derived['plans'][0]['inputs']['graph'],new);self.assertTrue(binding['native_owner_replayed']);replay.assert_called_once()
                with self.assertRaisesRegex(ValueError,'produce current'):transition(config,source,dict(new,sha256='WRONG'),audit)
            Path(devices['path']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'component inventory'):transition(config,source,new,audit)

if __name__=='__main__':unittest.main()
