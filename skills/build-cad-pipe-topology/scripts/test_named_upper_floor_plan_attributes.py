import copy,unittest
from test_match_named_riser_floor_segments import fixture as segment_fixture
from match_named_riser_floor_segments import correspond,MODE as MAPPING_MODE
from native_named_riser_evidence import collect as collect_names
from native_touching_plan_path_chunks import collect as collect_touching
from native_line_path_evidence import LAYERS,_on
from named_upper_floor_plan_attributes import attribute,implementation_hashes


def fixture():
    args=list(segment_fixture());docs,graphs,inventory,names,riser,touching,removed,policy,hashes=args
    doc=docs['plan'];graph=graphs['plan'];m=doc.modelspace();name_specs=[];seeds=[];branch_labels=[]
    for system,identifier,y in [('supply','CHWS1',0),('return','CHWR1',50)]:
        node=next(n for n in graph['nodes'] if n['node_id']==system+'R')
        circle=m.add_circle((0,y),1,dxfattribs=dict(layer=LAYERS[system]));node.update(system=system,subtype='out_of_plane_riser',source_handle=circle.dxf.handle)
        text=m.add_text(identifier+' DN450',dxfattribs=dict(insert=(-5,y+5),height=1,layer='ANNOTATION'))
        under=m.add_line((-6,y+4.8),(-1,y+4.8),dxfattribs=dict(layer='ANNOTATION'))
        leader=m.add_line((-1,y+4.8),(0,y),dxfattribs=dict(layer='ANNOTATION'))
        name_specs.append(dict(text_handle=text.dxf.handle,expected_text=text.plain_text(),underline_handle=under.dxf.handle,leader_handle=leader.dxf.handle,
            target=dict(kind='plan_riser_circle',node_id=node['node_id'],circle_handle=circle.dxf.handle)))
        main=m.add_text('DN250(3.200)',dxfattribs=dict(insert=(9.2,y+2.5),height=1,rotation=90,layer='ANNOTATION'))
        branch_labels.append(m.add_text('DN300(3.200)',dxfattribs=dict(insert=(5,y+.8),height=1,layer='ANNOTATION')))
        line=next(e for e in m.query('LINE') if e.dxf.layer==LAYERS[system] and e.dxf.start.x==e.dxf.end.x==10)
        seeds.append(dict(text_handle=main.dxf.handle,edge_id=system+'BRIDGE',source_line_handle=line.dxf.handle,expected_text=main.plain_text()))
    for edge in graph['edges']:
        edge['source_handles']=sorted({line.dxf.handle for line in m.query('LINE') if line.dxf.layer==LAYERS[edge['system']]
            and any(_on(a,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05) and _on(b,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)
                    for path in edge['attribute_paths'] for a,b in zip(path,path[1:]))})
    names['plan']=collect_names(doc,graph,dict(source_sha256='plan',graph_sha256='plan-graph',text_layers=['ANNOTATION'],leader_layers=['ANNOTATION'],selections=name_specs),'plan','plan-graph')
    ids=['supplyRIF','supplyBRIDGE','returnRIF','returnBRIDGE']
    args[5]=collect_touching(doc,graph,dict(view_kind='floor_plan',floor=3,edges=ids,**hashes['plan']),'plan','plan-graph')
    mapping=correspond(*args);mapping.update(mode=MAPPING_MODE,floor=3,source_sha256={v:h['source_sha256'] for v,h in hashes.items()},graph_sha256={v:h['graph_sha256'] for v,h in hashes.items()})
    return doc,graph,mapping,dict(seeds=seeds),branch_labels


class Tests(unittest.TestCase):
    def test_direct_branch_DN300_does_not_backflow_into_through_DN250(self):
        doc,graph,mapping,policy,labels=fixture();before=copy.deepcopy(graph)
        result,proof=attribute(doc,graph,mapping,policy,'plan','plan-graph');rows={r['edge_id']:r for r in result['records']}
        for system in ('supply','return'):
            self.assertEqual(rows[system+'BRIDGE']['nominal_mm'],250);self.assertEqual(rows[system+'RIF']['nominal_mm'],300)
            self.assertEqual(rows[system+'RIF']['status'],'direct_branch_DN_override');self.assertEqual(rows[system+'EQ']['nominal_mm'],250)
        self.assertEqual(len(result['records']),6);self.assertEqual(graph,before);self.assertFalse(result['graph_mutated'])
    def test_new_direct_branch_value_stays_on_its_own_service_branch(self):
        doc,graph,mapping,policy,labels=fixture();labels[0].dxf.text='DN400(3.200)'
        result,_=attribute(doc,graph,mapping,policy,'plan','plan-graph');rows={r['edge_id']:r for r in result['records']}
        self.assertEqual(rows['supplyRIF']['nominal_mm'],400);self.assertEqual(rows['returnRIF']['nominal_mm'],300)
        self.assertEqual(rows['supplyBRIDGE']['nominal_mm'],250);self.assertEqual(rows['returnBRIDGE']['nominal_mm'],250)
    def test_gaps_unclassified_compound_DN_and_changed_named_target_block(self):
        for case in ('gap','compound','name','role'):
            doc,graph,mapping,policy,labels=fixture()
            if case=='gap':next(e for e in graph['edges'] if e['edge_id']=='supplyBRIDGE')['attribute_paths'][1][0][0]+=.001
            elif case=='compound':labels[0].dxf.text='DN300/DN250'
            elif case=='name':doc.entitydb[next(n for n in graph['nodes'] if n['node_id']=='supplyR')['source_handle']].dxf.center=(1,0)
            else:mapping['floor_interface_correspondences'][0]['native_roles']['plan']['network']['off_edge']='supplyLOW'
            with self.subTest(case=case),self.assertRaises(ValueError):attribute(doc,graph,mapping,policy,'plan','plan-graph')
    def test_dependency_closure_contains_existing_DN_and_new_geometry_rules(self):
        for name in ('checked_plan_DN_scope_attributes.py','diameter_tee_inheritance.py','touching_plan_path_coverage.py','match_named_riser_floor_segments.py'):
            self.assertIn(name,implementation_hashes())


if __name__=='__main__':unittest.main()
