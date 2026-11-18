import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf
from native_line_path_evidence import LAYERS
from crossview_equipment_branch_inventory import service_route
from match_paired_service_crossview_paths import pair_paths,compute,verify_output,implementation_hashes,MODE
from confirm_crossview_paths import load,sha,encode


def fixture(reverse=False,interior=False,subdivision=False):
    doc=ezdxf.new();nodes=[];edges=[]
    def node(nid,x,y,kind):
        nodes.append(dict(node_id=nid,x=x,y=y,node_type=kind,floor=2));return nid
    def edge(eid,a,b,system):
        points={n['node_id']:[n['x'],n['y']] for n in nodes}
        edges.append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system=system,attribute_paths=[[points[a],points[b]]]))
    xs=[20,0] if reverse else [0,20]
    for did,x in zip(('D0','D1'),xs):node(did,x,20,'equipment');doc.modelspace().add_text(did,dxfattribs=dict(insert=(x,20)))
    for system,y in [('supply',0),('return',-30)]:
        doc.modelspace().add_line((-10,y),(30,y),dxfattribs=dict(layer=LAYERS[system]))
        ordered=[]
        for i,x in enumerate(xs):
            nid=node(system+str(i),x,y,'tee');ordered.append((x,nid))
            doc.modelspace().add_line((x,20),(x,y),dxfattribs=dict(layer=LAYERS[system]));edge(system+'B'+str(i),'D'+str(i),nid,system)
        for x,role in [(-10,'L'),(30,'R')]:ordered.append((x,node(system+role,x,y,'virtual_equipment')))
        if interior:
            nid=node(system+'I',10,y,'tee');ordered.append((10,nid));other=node(system+'X',10,y-10,'virtual_equipment');edge(system+'X',nid,other,system)
            doc.modelspace().add_line((10,y),(10,y-10),dxfattribs=dict(layer=LAYERS[system]))
        elif subdivision:ordered.append((10,node(system+'I',10,y,'physical_junction')))
        ordered.sort()
        for i,((_,a),(_,b)) in enumerate(zip(ordered,ordered[1:])):edge(system+'M'+str(i),a,b,system)
    graph=dict(nodes=nodes,edges=edges);rows={}
    for did in ('D0','D1'):
        services={s:dict(ready_for_mapping_comparison=True,trace=service_route(graph,did,s)) for s in ('supply','return')}
        rows[did]=dict(equipment_id=did,floor=2,ready_for_mapping_comparison=True,views={v:dict(services=copy.deepcopy(services)) for v in ('plan','iso')})
    return doc,graph,rows


class PairedServiceCorrespondenceTests(unittest.TestCase):
    def data(self,**kwargs):
        pd,pg,rows=fixture(**kwargs);idoc,ig,other=fixture(reverse=True,**kwargs)
        for did in rows:rows[did]['views']['iso']=other[did]['views']['iso']
        return dict(plan=pd,iso=idoc),dict(plan=pg,iso=ig),rows
    def check(self,docs,graphs,rows):return pair_paths(docs,graphs,rows,['D0','D1'],2,{v:dict(source_sha256=v,graph_sha256=v+'G') for v in docs})
    def test_two_complete_service_pairs_have_independent_native_paths(self):
        docs,graphs,rows=self.data();before=copy.deepcopy(graphs);result=self.check(docs,graphs,rows)
        self.assertEqual(set(result),{'supply','return'});self.assertEqual(graphs,before)
        for s,state in result.items():
            self.assertEqual(len(state['routes']['plan']['edges']),1);self.assertNotEqual(state['taps']['plan']['D0'],state['taps']['plan']['D1'])
            self.assertEqual(state['offcorridor_branch_correspondence'],'not_asserted')
    def test_missing_service_or_unready_owner_is_not_name_only_mapping(self):
        for case in ('unready','one_service','wrong_trace','floor','missing_owner'):
            with self.subTest(case=case):
                docs,graphs,rows=self.data()
                if case=='unready':rows['D0']['ready_for_mapping_comparison']=False
                elif case=='one_service':rows['D0']['views']['iso']['services']['return']['ready_for_mapping_comparison']=False
                elif case=='wrong_trace':rows['D0']['views']['iso']['services']['return']['trace']=copy.deepcopy(rows['D1']['views']['iso']['services']['return']['trace'])
                elif case=='floor':rows['D0']['floor']=1
                else:graphs['iso']['nodes']=[n for n in graphs['iso']['nodes'] if n['node_id']!='D0']
                with self.assertRaises((ValueError,KeyError)):self.check(docs,graphs,rows)
    def test_missing_duplicate_or_wrong_native_main_never_creates_join(self):
        for case in ('duplicate','missing','wrong_layer'):
            with self.subTest(case=case):
                docs,graphs,rows=self.data();doc=docs['iso'];line=list(doc.modelspace().query('LINE'))[0]
                if case=='duplicate':doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs=dict(layer=line.dxf.layer))
                elif case=='missing':doc.modelspace().delete_entity(line)
                else:line.dxf.layer=LAYERS['return']
                with self.assertRaises(ValueError):self.check(docs,graphs,rows)
    def test_mixed_system_and_collapsed_T_stay_unresolved(self):
        docs,graphs,rows=self.data();graphs['iso']['edges'][0]['system']='return'
        with self.assertRaises(ValueError):self.check(docs,graphs,rows)
        docs,graphs,rows=self.data();rows['D1']['views']['iso']['services']['supply']['trace']=copy.deepcopy(rows['D0']['views']['iso']['services']['supply']['trace'])
        with self.assertRaises(ValueError):self.check(docs,graphs,rows)
    def test_internal_actual_Ts_replayed_without_claiming_other_branches(self):
        docs,graphs,rows=self.data(interior=True);r=self.check(docs,graphs,rows)
        for s in ('supply','return'):
            self.assertEqual(len(r[s]['internal_native_junctions']['plan']),1)
            self.assertEqual(len(r[s]['routes']['iso']['edges']),2)
    def test_extra_interior_branch_is_a_topology_difference(self):
        pd,pg,rows=fixture();idoc,ig,other=fixture(interior=True)
        for did in rows:rows[did]['views']['iso']=other[did]['views']['iso']
        with self.assertRaisesRegex(ValueError,'branch counts disagree'):self.check(dict(plan=pd,iso=idoc),dict(plan=pg,iso=ig),rows)
    def test_source_covered_degree_two_subdivision_is_not_extra_branch(self):
        pd,pg,rows=fixture();idoc,ig,other=fixture(subdivision=True)
        for did in rows:rows[did]['views']['iso']=other[did]['views']['iso']
        r=self.check(dict(plan=pd,iso=idoc),dict(plan=pg,iso=ig),rows)
        self.assertEqual(len(r['supply']['routes']['plan']['edges']),1);self.assertEqual(len(r['supply']['routes']['iso']['edges']),2)
    def test_plain_crossing_and_unrelated_ring_do_not_join(self):
        docs,graphs,rows=self.data()
        # An opposite-service crossing is recorded by native T evidence; it is
        # never a new edge or an argument to merge the independent systems.
        docs['plan'].modelspace().add_line((10,-5),(10,5),dxfattribs=dict(layer=LAYERS['return']))
        before=copy.deepcopy(graphs);r=self.check(docs,graphs,rows);self.assertEqual(graphs,before);self.assertEqual(set(r),{'supply','return'})
    def native_files(self,root):
        docs,graphs,rows=self.data();paths={};inputs={}
        for view in ('plan','iso'):
            source=root/(view+'.dxf');docs[view].saveas(source);graph=root/(view+'.json');graph.write_bytes(encode(graphs[view]))
            for key,path in [(view+'_source',source),(view+'_graph',graph)]:paths[key]=path;inputs[key]=dict(path=str(path),sha256=sha(path))
        folder=root/'inventory';folder.mkdir();paths['inventory']=folder/'inventory.json';paths['inventory'].write_bytes(encode(dict(records=list(rows.values()))))
        paths['inventory_receipt']=folder/'inventory-receipt.json';paths['inventory_receipt'].write_bytes(encode(dict(inputs=inputs)))
        policy={k+'_sha256':sha(v) for k,v in paths.items()};policy.update(floor=2,equipment_pairs=[['D0','D1']],context_only_equipment_ids=['D1'])
        return paths,policy,dict(records=list(rows.values()))
    def test_file_entry_context_only_preserves_checks_without_branch_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            paths,policy,inventory=self.native_files(Path(folder))
            with patch('match_paired_service_crossview_paths.verify_inventory',return_value=inventory):result=compute(paths,policy)
            self.assertEqual(len(result['records']),4);self.assertEqual(result['context_only_equipment_ids'],['D1'])
            self.assertEqual([r['equipment_id'] for r in result['records'] if r['kind']=='equipment_branch'],['D0','D0'])
            self.assertEqual(len(result['evidence']['paired_services'][0]['services']),2);self.assertFalse(result['human_accepted'])
    def test_bad_pair_scope_and_stale_inputs_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            paths,policy,inventory=self.native_files(Path(folder))
            for case in ('repeated_pair','both_reference','unknown_reference','stale_input'):
                p=copy.deepcopy(policy)
                if case=='repeated_pair':p['equipment_pairs']*=2
                elif case=='both_reference':p['context_only_equipment_ids']=['D0','D1']
                elif case=='unknown_reference':p['context_only_equipment_ids']=['OTHER']
                else:p['iso_source_sha256']='wrong'
                with patch('match_paired_service_crossview_paths.verify_inventory',return_value=inventory):
                    with self.assertRaises(ValueError):compute(paths,p)
    def test_receipt_replay_recomputes_native_mapping_and_rejects_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);paths,policy,inventory=self.native_files(root);pp=root/'policy.json';pp.write_bytes(encode(policy));paths['policy']=pp
            with patch('match_paired_service_crossview_paths.verify_inventory',return_value=inventory):result=compute(paths,policy)
            output=root/'mapping';output.mkdir();(output/'mapping.json').write_bytes(encode(result))
            receipt=dict(mode=MODE,implementation_sha256=implementation_hashes(),inputs={k:dict(path=str(v),sha256=sha(v)) for k,v in paths.items()},output_sha256=sha(output/'mapping.json'))
            (output/'source-mapping-receipt.json').write_bytes(encode(receipt))
            with patch('match_paired_service_crossview_paths.verify_inventory',return_value=inventory):self.assertEqual(verify_output(output),result)
            result['human_accepted']=True;(output/'mapping.json').write_bytes(encode(result));receipt['output_sha256']=sha(output/'mapping.json');(output/'source-mapping-receipt.json').write_bytes(encode(receipt))
            with patch('match_paired_service_crossview_paths.verify_inventory',return_value=inventory):
                with self.assertRaisesRegex(ValueError,'native replay differs'):verify_output(output)


if __name__=='__main__':unittest.main()
