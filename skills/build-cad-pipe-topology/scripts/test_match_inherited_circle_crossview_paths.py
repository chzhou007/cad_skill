import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf
from confirm_crossview_paths import sha,encode
from native_line_path_evidence import LAYERS
from native_inherited_duplicate_circle_evidence import collect
from crossview_equipment_branch_inventory import native_tee,service_route
from match_inherited_circle_crossview_paths import correspond,compute,implementation_hashes


def fixture(folder):
    source='a'*64;gh='b'*64;doc=ezdxf.new();m=doc.modelspace();nodes=[dict(node_id='D'+str(i),node_type='equipment',floor=3,x=-15,y=20*i+10) for i in range(3)]
    edges=[];expert=dict(confirmed_by='expert',question='source connection?',answer='confirmed connection')
    technical=dict(confirmed_by='technical_calibration',question='same full native shape?',answer='yes',human_accepted=False)
    def root(confirmation):return dict(source_sha256=source,input_graph_sha256='c'*64,screen_sha256='d'*64,confirmation=confirmation,
        records=[],physical_length='unknown',supply_return_independent=True)
    graph=dict(nodes=nodes,edges=edges,metadata=dict(source_sha256=source),expertConfirmedCircleJunctionRepair=root(expert),sourceCalibratedDuplicateCircleRepair=root(technical))
    families={}
    for system,x in [('supply',0),('return',30)]:
        mains=[m.add_line((x,-10,0),(x,60,0),dxfattribs=dict(layer=LAYERS[system])) for _ in range(2)];handles=[e.dxf.handle for e in mains]
        families[system]=dict(canonical_source_handle=handles[0],coincident_source_family=handles)
        ordered=[(-10,system+'L')];nodes.append(dict(node_id=system+'L',node_type='virtual_equipment',floor=3,system=system,x=x,y=-10))
        control=None
        for i,y in enumerate([0,20,40]):
            nid=system+str(i);eid=system+'B'+str(i);circle=m.add_circle((x,y,0),1,dxfattribs=dict(layer=LAYERS[system]));line=m.add_line((x-10,y,0),(x-1,y,0),dxfattribs=dict(layer=LAYERS[system]))
            meta=dict(circle_handle=circle.dxf.handle,circle_layer=LAYERS[system],line_system=system,center=[x,y],source_rim=[x-1,y],
                circle_z=0,main_z_at_center=0,branch_z_at_rim=0,source_graph_sha256='c'*64,screen_sha256='d'*64,
                graphic_radius_is_physical_length=False,physical_length='unknown',coincident_native_main_handles=handles,physical_main_identity='unresolved')
            node=dict(node_id=nid,node_type='tee',floor=3,system=system,x=x,y=y)
            record=dict(tee=nid,circle_handle=circle.dxf.handle,branch_edge=eid,system=system)
            if i==0:
                path=folder/(system+'.json');path.write_bytes(encode(dict(sourceHashes=dict(main_dxf=source),issue=dict(id=system,note=expert['answer'],edges=[eid],sourceBounds=[x-2,-2,4,4]))))
                meta.update(confirmation=expert,expert_issue_evidence=dict(issue=str(path),issue_sha256=sha(path),issue_id=system));node['expert_confirmed_circle']=meta
                graph['expertConfirmedCircleJunctionRepair']['records'].append(record);control=circle.dxf.handle
            else:
                meta.update(confirmation=technical,expert_control_circle=control,human_accepted=False);node['calibrated_duplicate_circle']=meta
                graph['sourceCalibratedDuplicateCircleRepair']['records'].append(record)
            nodes.append(node);ordered.append((y,nid));edges.append(dict(edge_id=eid,start_node_id='D'+str(i),end_node_id=nid,system=system,
                attribute_paths=[[[x-10,y],[x-1,y]]],source_handles=[line.dxf.handle]))
        nodes.append(dict(node_id=system+'R',node_type='virtual_equipment',floor=3,system=system,x=x,y=60));ordered.append((60,system+'R'))
        for i,((a,u),(b,v)) in enumerate(zip(ordered,ordered[1:])):edges.append(dict(edge_id=system+'M'+str(i),start_node_id=u,end_node_id=v,system=system,
            attribute_paths=[[[x,a],[x,b]]],source_handles=[handles[0]]))
    iso=ezdxf.new();im=iso.modelspace();ig=dict(nodes=[dict(node_id='D'+str(i),node_type='equipment',floor=3,x=20*i,y=100) for i in range(3)],edges=[],metadata=dict(source_sha256='e'*64));ifamilies={}
    for system,y in [('supply',0),('return',-30)]:
        main=im.add_line((-10,y),(50,y),dxfattribs=dict(layer=LAYERS[system]));ifamilies[system]=dict(canonical_source_handle=main.dxf.handle,coincident_source_family=[main.dxf.handle]);ordered=[]
        for name,x,kind in [(system+'L',-10,'virtual_equipment')]+[(system+str(i),20*i,'tee') for i in range(3)]+[(system+'R',50,'virtual_equipment')]:
            ig['nodes'].append(dict(node_id=name,node_type=kind,floor=3,system=system,x=x,y=y));ordered.append((x,name))
        for i in range(3):
            line=im.add_line((20*i,100),(20*i,y),dxfattribs=dict(layer=LAYERS[system]));ig['edges'].append(dict(edge_id=system+'B'+str(i),start_node_id='D'+str(i),end_node_id=system+str(i),
                system=system,attribute_paths=[[[20*i,100],[20*i,y]]],source_handles=[line.dxf.handle]))
        for i,((a,u),(b,v)) in enumerate(zip(ordered,ordered[1:])):ig['edges'].append(dict(edge_id=system+'M'+str(i),start_node_id=u,end_node_id=v,system=system,
            attribute_paths=[[[a,y],[b,y]]],source_handles=[main.dxf.handle]))
    docs=dict(plan=doc,iso=iso);graphs=dict(plan=graph,iso=ig);hashes=dict(plan=dict(source_sha256=source,graph_sha256=gh),iso=dict(source_sha256='e'*64,graph_sha256='f'*64))
    inventory=dict(records=[])
    for i in range(3):
        did='D'+str(i);row=dict(equipment_id=did,floor=3,ready_for_mapping_comparison=True,views={})
        for view in graphs:
            services={}
            for system in ('supply','return'):
                trace=service_route(graphs[view],did,system);h=hashes[view]
                proof=collect(docs[view],graphs[view],trace['tee'],h['source_sha256'],h['graph_sha256']) if view=='plan' else native_tee(docs[view],graphs[view],trace['tee'],h['source_sha256'],h['graph_sha256'])
                services[system]=dict(trace=trace,ready_for_mapping_comparison=True,junction_evidence=proof)
            row['views'][view]=dict(services=services)
        inventory['records'].append(row)
    policy=dict(equipment_ids=['D0','D1','D2'],floor=3,mapping_prefix='TEST',source_main_families=dict(plan=families,iso=ifamilies))
    return docs,graphs,inventory,{},policy,hashes


class Tests(unittest.TestCase):
    def test_three_paired_anchors_correlate_paths_without_resolving_source_multiplicity_or_values(self):
        with tempfile.TemporaryDirectory() as temp:
            args=fixture(Path(temp));before=copy.deepcopy(args[1:3]);result=correspond(*args)
            self.assertEqual(args[1:3],before);self.assertEqual(len(result['records']),10)
            self.assertEqual(sum(r['kind']=='equipment_branch' for r in result['records']),6)
            self.assertFalse(result['physical_source_identity_resolved']);self.assertEqual(result['physical_values_assigned'],0)
            for row in result['records']:self.assertFalse(row['physical_ports_verified']);self.assertFalse(row['human_accepted'])
            for system in ('supply','return'):
                self.assertEqual(len(result['evidence']['main_topology'][system]['adjacent']),2)
                manifest=result['evidence']['main_coverage'][system]['plan']['canonical_source_projection']
                self.assertEqual(len(manifest['source_entities']),2);self.assertFalse(manifest['source_entities_deleted'])

    def test_missing_service_wrong_owner_scope_source_or_implicit_family_cannot_map(self):
        for case in ('unready','one_service','trace','floor','two_anchors','duplicate','prefix','family','wrong_Z','stale_proof','physical_claim'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(fixture(Path(temp)));docs,graphs,inventory,ip,policy,hashes=args;row=inventory['records'][0]
                if case=='unready':row['ready_for_mapping_comparison']=False
                elif case=='one_service':row['views']['plan']['services']['return']['ready_for_mapping_comparison']=False
                elif case=='trace':row['views']['iso']['services']['return']['trace']=copy.deepcopy(inventory['records'][1]['views']['iso']['services']['return']['trace'])
                elif case=='floor':row['floor']=2
                elif case=='two_anchors':policy['equipment_ids'].pop()
                elif case=='duplicate':policy['equipment_ids'].append('D0')
                elif case=='prefix':policy['mapping_prefix']='invalid prefix'
                elif case=='family':policy['source_main_families']['plan']['supply']['coincident_source_family'].pop()
                elif case=='wrong_Z':docs['plan'].entitydb[policy['source_main_families']['plan']['supply']['coincident_source_family'][1]].dxf.end=(0,60,1)
                elif case=='stale_proof':row['views']['plan']['services']['supply']['junction_evidence']['graph_sha256']='stale'
                else:row['views']['plan']['services']['supply']['junction_evidence']['physical_source_identity_resolved']=True
                with self.assertRaises(ValueError):correspond(*args)

    def test_unexpected_native_main_not_explicitly_covered_by_replayed_family_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            args=list(fixture(Path(temp)));args[0]['plan'].modelspace().add_line((0,-20),(0,80),dxfattribs=dict(layer=LAYERS['supply']))
            with self.assertRaises(ValueError):correspond(*args)

    def refresh(self,args,view,system):
        docs,graphs,inventory,ip,policy,hashes=args;h=hashes[view]
        for row in inventory['records']:
            trace=service_route(graphs[view],row['equipment_id'],system)
            proof=collect(docs[view],graphs[view],trace['tee'],h['source_sha256'],h['graph_sha256'],ip) if view=='plan' else native_tee(docs[view],graphs[view],trace['tee'],h['source_sha256'],h['graph_sha256'])
            row['views'][view]['services'][system].update(trace=trace,junction_evidence=proof)

    def test_extra_actual_branch_returns_to_source_comparison_instead_of_name_only_mapping(self):
        with tempfile.TemporaryDirectory() as temp:
            args=list(fixture(Path(temp)));graph=args[1]['plan'];main=next(e for e in graph['edges'] if e['edge_id']=='supplyM1');canonical=main['source_handles'][0]
            main.update(end_node_id='EXTRA',attribute_paths=[[[0,0],[0,10]]])
            graph['nodes']+= [dict(node_id='EXTRA',node_type='tee',floor=3,system='supply',x=0,y=10),dict(node_id='OUT',node_type='virtual_equipment',floor=3,x=-10,y=10)]
            line=args[0]['plan'].modelspace().add_line((-10,10),(-1,10),dxfattribs=dict(layer=LAYERS['supply']))
            graph['edges']+=[dict(edge_id='EXTRA-MAIN',start_node_id='EXTRA',end_node_id='supply1',system='supply',source_handles=[canonical],attribute_paths=[[[0,10],[0,20]]]),
                dict(edge_id='EXTRA-BRANCH',start_node_id='EXTRA',end_node_id='OUT',system='supply',source_handles=[line.dxf.handle],attribute_paths=[[[-1,10],[-10,10]]])]
            self.refresh(args,'plan','supply')
            with self.assertRaisesRegex(ValueError,'unmatched interior main branches'):correspond(*args)

    def test_native_common_anchor_order_disagreement_is_not_repaired_by_equipment_names(self):
        with tempfile.TemporaryDirectory() as temp:
            args=list(fixture(Path(temp)));graph=args[1]['iso'];rename={'D1':'D2','D2':'D1'}
            for node in graph['nodes']:node['node_id']=rename.get(node['node_id'],node['node_id'])
            for edge in graph['edges']:
                for k in ('start_node_id','end_node_id'):edge[k]=rename.get(edge[k],edge[k])
            for system in ('supply','return'):self.refresh(args,'iso',system)
            with self.assertRaisesRegex(ValueError,'different native main branch order'):correspond(*args)

    def test_entry_requires_native_inventory_replay_and_hash_bound_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);ip=root/'inventory.json';rp=root/'inventory-receipt.json';ip.write_text('{}','utf8');rp.write_text('{}','utf8')
            paths=dict(inventory=ip,inventory_receipt=rp);policy={k+'_sha256':sha(v) for k,v in paths.items()}
            with patch('match_inherited_circle_crossview_paths.verify_inventory',side_effect=ValueError('native parent changed')),self.assertRaisesRegex(ValueError,'native parent changed'):compute(paths,policy)
            policy['inventory_sha256']='wrong'
            with self.assertRaisesRegex(ValueError,'input changed'):compute(paths,policy)
        for name in ('native_canonical_main_family_view.py','inherited_circle_branch_inventory.py','match_source_checked_crossview_paths.py','native_path_coverage_audit.py'):
            self.assertIn(name,implementation_hashes())


if __name__=='__main__':unittest.main()
