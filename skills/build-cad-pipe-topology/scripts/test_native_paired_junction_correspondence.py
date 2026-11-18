import copy,math,unittest
from ezdxf.math import Matrix44
import test_match_paired_service_crossview_paths as fixtures
from match_paired_service_crossview_paths import pair_paths,MODE
from crossview_equipment_branch_inventory import service_route
from native_paired_junction_correspondence import collect
from native_line_path_evidence import LAYERS


def fixture(angle=0):
    doc,g,_=fixtures.fixture(interior=True);m=doc.modelspace();nodes={n['node_id']:n for n in g['nodes']}
    for did,y in [('D2',-25),('D3',-35)]:
        n=dict(node_id=did,node_type='equipment',floor=2,x=25.,y=float(y));g['nodes'].append(n);nodes[did]=n;m.add_text(did,dxfattribs=dict(insert=(25,y)))
    for system,y in [('supply',0),('return',-30)]:
        lines=[e for e in m.query('LINE') if e.dxf.layer==LAYERS[system] and list(e.dxf.start)[:2]==[10,y] and list(e.dxf.end)[:2]==[10,y-10]]
        assert len(lines)==1;lines[0].dxf.end=(10,y-40,0)
        first=nodes[system+'X'];first['node_type']='tee';second=dict(node_id=system+'C3',node_type='tee',floor=2,x=10.,y=float(y-20));tail=dict(node_id=system+'Tail',node_type='virtual_equipment',floor=2,x=10.,y=float(y-40));g['nodes']+=[second,tail]
        for n in (second,tail):nodes[n['node_id']]=n
        def edge(eid,a,b,path):g['edges'].append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system=system,attribute_paths=[path]))
        edge(system+'C0',first['node_id'],second['node_id'],[[10.,float(y-10)],[10.,float(y-20)]])
        edge(system+'C1',second['node_id'],tail['node_id'],[[10.,float(y-20)],[10.,float(y-40)]])
        for did,n in [('D2',first),('D3',second)]:
            p=[n['x'],n['y']];q=[15.,n['y']];m.add_line(p,q,dxfattribs=dict(layer=LAYERS[system]));edge(system+did,n['node_id'],did,[p,q])
    if angle:
        matrix=Matrix44.z_rotate(math.radians(angle))
        for e in m:e.transform(matrix)
        for n in g['nodes']:
            p=matrix.transform((n['x'],n['y'],0));n.update(x=p.x,y=p.y)
        for e in g['edges']:
            e['attribute_paths']=[[[matrix.transform((*p,0)).x,matrix.transform((*p,0)).y] for p in path] for path in e['attribute_paths']]
    hashes={v:dict(source_sha256='S',graph_sha256='G') for v in ('plan','iso')};rows={}
    for did in ('D0','D1','D2','D3'):
        services={s:dict(ready_for_mapping_comparison=True,trace=service_route(g,did,s)) for s in ('supply','return')}
        rows[did]=dict(equipment_id=did,floor=2,ready_for_mapping_comparison=True,views={v:dict(services=copy.deepcopy(services)) for v in hashes})
    docs={v:doc for v in hashes};graphs={v:g for v in hashes};pairs=[]
    for pid,devices in [('P01',['D0','D1']),('P02',['D2','D3'])]:pairs.append(dict(pair_id=pid,equipment_ids=devices,services=pair_paths(docs,graphs,rows,devices,2,hashes)))
    mapping=dict(mode=MODE,floor=2,local_graphs_mutated=False,human_accepted=False,evidence=dict(paired_services=pairs))
    return docs,graphs,mapping,hashes


class NativePairedJunctionTests(unittest.TestCase):
    def independent_views(self,swap_iso_targets=False):
        pd,pg,_,_=fixture();idoc,ig,_,_=fixture(90);doc=idoc['iso'];graph=ig['iso']
        if swap_iso_targets:
            rename={'D2':'D3','D3':'D2'}
            for node in graph['nodes']:node['node_id']=rename.get(node['node_id'],node['node_id'])
            for edge in graph['edges']:
                for key in ('start_node_id','end_node_id'):edge[key]=rename.get(edge[key],edge[key])
            for text in doc.modelspace().query('TEXT'):
                if text.plain_text() in rename:text.dxf.text=rename[text.plain_text()]
        docs=dict(plan=pd['plan'],iso=doc);graphs=dict(plan=pg['plan'],iso=graph)
        hashes={v:dict(source_sha256=v,graph_sha256=v+'G') for v in docs};rows={}
        for did in ('D0','D1','D2','D3'):
            rows[did]=dict(equipment_id=did,floor=2,ready_for_mapping_comparison=True,
                views={v:dict(services={s:dict(ready_for_mapping_comparison=True,trace=service_route(graphs[v],did,s)) for s in ('supply','return')}) for v in docs})
        pairs=[dict(pair_id=pid,equipment_ids=devices,services=pair_paths(docs,graphs,rows,devices,2,hashes)) for pid,devices in [('P01',['D0','D1']),('P02',['D2','D3'])]]
        mapping=dict(floor=2,local_graphs_mutated=False,human_accepted=False,evidence=dict(paired_services=pairs))
        return docs,graphs,mapping,hashes
    def test_unique_offcorridor_first_known_target_matches_both_existing_Ts(self):
        args=fixture();before=copy.deepcopy(args[1]['plan']);result=collect(*args)
        self.assertEqual(args[1]['plan'],before);self.assertEqual(len(result['records']),2)
        for row in result['records']:
            self.assertTrue(row['complete']);self.assertEqual(len(row['matches']),1);match=row['matches'][0]
            self.assertEqual(match['target_equipment_id'],'D2');self.assertEqual(match['views']['plan']['route']['edges'],[row['system']+'X'])
            self.assertNotEqual(match['target_equipment_id'],'D3')
        self.assertEqual(result['physical_lengths_assigned'],0);self.assertFalse(result['graph_mutated'])
    def test_rotation_does_not_change_the_named_branch_identity(self):
        for angle in (90,180,270):
            result=collect(*fixture(angle));self.assertTrue(all(r['complete'] for r in result['records']));self.assertEqual({m['target_equipment_id'] for r in result['records'] for m in r['matches']},{'D2'})
    def test_duplicate_caption_wrong_floor_review_or_source_change_rejected(self):
        for mode in ('caption','floor','review','source','missing_return'):
            args=fixture();doc=args[0]['plan'];g=args[1]['plan'];mapping=args[2]
            if mode=='caption':doc.modelspace().add_text('D2')
            elif mode=='floor':next(n for n in g['nodes'] if n['node_id']=='D2')['floor']=3
            elif mode=='review':next(n for n in g['nodes'] if n['node_id']=='supplyI')['review_required']=True
            elif mode=='source':
                line=next(e for e in doc.modelspace().query('LINE') if e.dxf.layer==LAYERS['supply'] and list(e.dxf.start)[:2]==[10,0] and list(e.dxf.end)[:2]==[10,-40]);doc.modelspace().delete_entity(line)
            else:mapping['evidence']['paired_services'][1]['services'].pop('return')
            with self.assertRaises(ValueError):collect(*args)
    def test_no_other_pair_does_not_invent_a_target_from_nearby_geometry(self):
        args=fixture();args[2]['evidence']['paired_services']=args[2]['evidence']['paired_services'][:1]
        result=collect(*args);self.assertTrue(all(not r['complete'] for r in result['records']));self.assertTrue(all(not r['matches'] for r in result['records']))
    def test_independent_rotated_views_preserve_branch_identity(self):
        result=collect(*self.independent_views());self.assertTrue(all(r['complete'] for r in result['records']))
        self.assertEqual({m['target_equipment_id'] for r in result['records'] for m in r['matches']},{'D2'})
    def test_same_equipment_names_with_different_first_branch_targets_do_not_self_confirm(self):
        result=collect(*self.independent_views(True));self.assertTrue(all(not r['complete'] for r in result['records']))
        self.assertTrue(all(not r['matches'] for r in result['records']));self.assertEqual(result['physical_lengths_assigned'],0)


if __name__=='__main__':unittest.main()
