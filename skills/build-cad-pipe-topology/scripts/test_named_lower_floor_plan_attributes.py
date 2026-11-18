import copy,unittest
from test_match_named_riser_lower_floor_segments import fixture as lower_fixture
from match_named_riser_lower_floor_segments import correspond,MODE as MAPPING_MODE
from native_named_riser_evidence import collect as collect_names
from native_line_path_evidence import LAYERS,_on
from named_lower_floor_plan_attributes import attribute,implementation_hashes


def fixture():
    docs,graphs,inventory,names,riser,policy,hashes=lower_fixture();doc=docs['plan'];graph=graphs['plan'];m=doc.modelspace();specs=[];seeds=[]
    for system,identifier,y in [('supply','CHWS1',0),('return','CHWR1',50)]:
        node=next(n for n in graph['nodes'] if n['node_id']==system+'R');circle=m.add_circle((0,y),1,dxfattribs=dict(layer=LAYERS[system]))
        node.update(system=system,subtype='out_of_plane_riser',source_handle=circle.dxf.handle)
        text=m.add_text(identifier+' DN450',dxfattribs=dict(insert=(-5,y+5),height=1,layer='ANNOTATION'))
        underline=m.add_line((-6,y+4.8),(-1,y+4.8),dxfattribs=dict(layer='ANNOTATION'));leader=m.add_line((-1,y+4.8),(0,y),dxfattribs=dict(layer='ANNOTATION'))
        specs.append(dict(text_handle=text.dxf.handle,expected_text=text.plain_text(),underline_handle=underline.dxf.handle,leader_handle=leader.dxf.handle,
            target=dict(kind='plan_riser_circle',node_id=node['node_id'],circle_handle=circle.dxf.handle)))
        dn=m.add_text('DN200(2.900)',dxfattribs=dict(insert=(9.2,y+2.5),height=1,rotation=90,layer='ANNOTATION'))
        line=next(e for e in m.query('LINE') if e.dxf.layer==LAYERS[system] and e.dxf.start.x==e.dxf.end.x==10)
        seeds.append(dict(text_handle=dn.dxf.handle,edge_id=system+'BRIDGE',source_line_handle=line.dxf.handle,expected_text=dn.plain_text()))
    for e in graph['edges']:
        e['source_handles']=sorted({line.dxf.handle for line in m.query('LINE') if line.dxf.layer==LAYERS[e['system']]
            and any(_on(a,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05) and _on(b,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)
                    for path in e['attribute_paths'] for a,b in zip(path,path[1:]))})
    names['plan']=collect_names(doc,graph,dict(source_sha256='plan',graph_sha256='plan-graph',text_layers=['ANNOTATION'],leader_layers=['ANNOTATION'],selections=specs),'plan','plan-graph')
    mapping=correspond(docs,graphs,inventory,names,riser,policy,hashes)
    mapping.update(mode=MAPPING_MODE,floor=1,source_sha256={v:h['source_sha256'] for v,h in hashes.items()},graph_sha256={v:h['graph_sha256'] for v,h in hashes.items()})
    return doc,graph,mapping,dict(seeds=seeds)


class Tests(unittest.TestCase):
    def test_through_DN200_inherits_into_branches_without_selecting_named_vertical450(self):
        args=fixture();before=copy.deepcopy(args[1]);result,proof=attribute(*args,'plan','plan-graph')
        self.assertEqual(args[1],before);self.assertEqual(len(result['records']),6)
        for r in result['records']:self.assertEqual(r['nominal_mm'],200)
        self.assertEqual(len(proof['named_riser_annotation_domain']['consumed_text_handles']),2);self.assertFalse(result['graph_mutated'])
    def test_explicit_branch_change_stays_on_that_service_branch(self):
        doc,g,m,p=fixture();doc.modelspace().add_text('DN150(2.900)',dxfattribs=dict(insert=(5,.8),height=1,layer='ANNOTATION'))
        result,_=attribute(doc,g,m,p,'plan','plan-graph');rows={r['edge_id']:r for r in result['records']}
        self.assertEqual(rows['supplyRIF']['nominal_mm'],150);self.assertEqual(rows['supplyBRIDGE']['nominal_mm'],200)
        self.assertEqual(rows['returnRIF']['nominal_mm'],200)
    def test_upper_mode_changed_role_name_and_real_gap_cannot_be_consumed(self):
        for case in ('mode','role','name','gap'):
            doc,g,m,p=fixture()
            if case=='mode':m['mode']='source_checked_named_upper_floor_segment_paths_v1'
            elif case=='role':m['floor_interface_correspondences'][0]['native_roles']['plan']['network']['off_edge']='other'
            elif case=='name':doc.entitydb[next(n for n in g['nodes'] if n['node_id']=='supplyR')['source_handle']].dxf.center=(1,0)
            else:next(e for e in g['edges'] if e['edge_id']=='supplyBRIDGE')['attribute_paths'][1][0][0]+=.001
            with self.subTest(case=case),self.assertRaises(ValueError):attribute(doc,g,m,p,'plan','plan-graph')
    def test_dependencies_include_inherited_DN_and_new_lower_mapping(self):
        for name in ('diameter_tee_inheritance.py','checked_plan_DN_scope_attributes.py','match_named_riser_lower_floor_segments.py','touching_plan_path_coverage.py'):
            self.assertIn(name,implementation_hashes())


if __name__=='__main__':unittest.main()
