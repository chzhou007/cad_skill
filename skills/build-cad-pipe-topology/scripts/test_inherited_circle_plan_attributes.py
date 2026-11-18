import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_match_inherited_circle_crossview_paths import fixture as mapping_fixture
from match_inherited_circle_crossview_paths import correspond
from native_line_path_evidence import LAYERS
from inherited_circle_plan_attributes import attribute,compute,coverage_reader,implementation_hashes
from confirm_crossview_paths import sha


def fixture(folder):
    args=mapping_fixture(folder);docs,graphs,inventory,_,_,hashes=args;doc=docs['plan'];graph=graphs['plan'];m=doc.modelspace();doc.header['$INSUNITS']=4
    controls=[]
    for i,(system,start,end,pos,angle) in enumerate([
        ('supply',(100,-50),(120,-50),(110,-49.88),0),('return',(100,-30),(120,-30),(110,-29.88),0),
        ('supply',(130,-50),(130,-30),(129.88,-40),90),('return',(150,-50),(150,-30),(149.88,-40),90)]):
        eid='CONTROL'+str(i);line=m.add_line(start,end,dxfattribs=dict(layer=LAYERS[system]));text=m.add_text('DN100',dxfattribs=dict(insert=pos,layer='AN',height=.2,rotation=angle))
        for j,point in enumerate((start,end)):graph['nodes'].append(dict(node_id=eid+str(j),node_type='virtual_equipment',system=system,floor=3,x=point[0],y=point[1]))
        graph['edges'].append(dict(edge_id=eid,start_node_id=eid+'0',end_node_id=eid+'1',system=system,source_handles=[line.dxf.handle],attribute_paths=[[list(start),list(end)]]))
        controls.append(dict(text_handle=text.dxf.handle,edge_id=eid,source_line_handle=line.dxf.handle,expected_text='DN100'))
    seeds=[]
    for system,x in [('supply',0),('return',30)]:
        text=m.add_text('DN150(3.200)',dxfattribs=dict(insert=(x-.12,50),layer='AN',height=.2,rotation=90))
        line=args[4]['source_main_families']['plan'][system]['canonical_source_handle']
        seeds.append(dict(text_handle=text.dxf.handle,edge_id=system+'M3',source_line_handle=line,expected_text=text.plain_text()))
    title=m.add_text('三层顶部水管平面图',dxfattribs=dict(insert=(-25,-25),height=1));dimensions=[]
    for start,end,angle in [((0,-100),(200,-100),0),((180,-100),(180,50),90)]:
        drawing=m.add_linear_dim(base=(250,150),p1=start,p2=end,angle=angle);drawing.render();dim=drawing.dimension
        text=next(t for t in doc.blocks[dim.dxf.geometry] if t.dxftype() in ('TEXT','MTEXT'))
        dimensions.append(dict(handle=dim.dxf.handle,text_handle=text.dxf.handle,text=text.plain_text()))
    mapping=correspond(*args)
    policy=dict(group_id='test',seeds=seeds,expert_T_inheritance_rule='same-system through-T then explicit branch override')
    calibration=dict(source_sha256=hashes['plan']['source_sha256'],graph_sha256=hashes['plan']['graph_sha256'],text_layers=['AN'],controls=controls,selections=seeds)
    metric=dict(view_kind='floor_plan',plan_window=[-100,300,-200,200],floor_title_handle=title.dxf.handle,floor_title=title.plain_text(),unit_dimensions=dimensions)
    return doc,graph,mapping,policy,calibration,metric,hashes['plan']['source_sha256'],hashes['plan']['graph_sha256']


class Tests(unittest.TestCase):
    def test_through_inheritance_source_multiplicity_and_projected_lengths_remain_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            args=fixture(Path(temp));before=copy.deepcopy(args[1]);result=attribute(*args)
            self.assertEqual(args[1],before);self.assertEqual(len(result['records']),10)
            self.assertEqual({r['diameter']['nominal_mm'] for r in result['records']},{150})
            self.assertEqual({r['horizontal_projection']['value_mm'] for r in result['records']},{9,20})
            for row in result['records']:
                self.assertIsNone(row['whole_axis_physical_length_mm']);self.assertFalse(row['whole_axis_DN_selected'])
                self.assertFalse(row['physical_source_identity_resolved']);self.assertFalse(row['physical_ports_verified'])
            for state in result['topology_contract']['source_main_projections'].values():
                self.assertEqual(len(state['canonical_source_projection']['source_entities']),2)
            self.assertTrue(all(not x['whole_original_edge_value_assigned'] for x in result['diameter_scope']['frontier_fragments']))

    def test_explicit_branch_override_does_not_change_main_and_conflicting_change_does_not_get_published(self):
        for conflict in (False,True):
            with self.subTest(conflict=conflict),tempfile.TemporaryDirectory() as temp:
                args=list(fixture(Path(temp)));doc=args[0]
                if conflict:
                    doc.modelspace().add_text('DN125',dxfattribs=dict(layer='AN',height=.2,rotation=90,insert=(-.12,10)))
                    with self.assertRaises(ValueError):attribute(*args)
                else:
                    doc.modelspace().add_text('DN65',dxfattribs=dict(layer='AN',height=.2,rotation=0,insert=(-5,20.12)))
                    result=attribute(*args);values={r['plan_edges'][0]:r['diameter']['nominal_mm'] for r in result['records']}
                    self.assertEqual(values['supplyB1'],65);self.assertEqual(values['supplyM1'],150);self.assertEqual(values['supplyM2'],150)

    def test_unexplained_native_duplicate_stale_scope_floor_or_physical_claim_fails(self):
        for case in ('duplicate','stale','floor','ports','identity','missing_service','seed','units'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(fixture(Path(temp)))
                if case=='duplicate':args[0].modelspace().add_line((0,-10),(0,60),dxfattribs=dict(layer=LAYERS['supply']))
                elif case=='stale':args[1]['edges'][0]['attribute_paths'][0][0][0]-=1
                elif case=='floor':args[2]['records'][0]['floor']=2
                elif case=='ports':args[2]['records'][0]['physical_ports_verified']=True
                elif case=='identity':args[2]['physical_source_identity_resolved']=True
                elif case=='missing_service':args[2]['records'].pop()
                elif case=='seed':args[3]['seeds']=args[3]['seeds'][:1]
                else:args[0].header['$INSUNITS']=0
                with self.assertRaises(ValueError):attribute(*args)

    def test_DN_frontier_projection_cannot_rewrite_source_branch_or_reuse_stale_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            doc,g,_,_,_,_,sh,gh=fixture(Path(temp));reader=coverage_reader(g,['supplyB0'],gh);current=copy.deepcopy(g)
            current['edges'][0]['attribute_paths'][0][0][0]-=1
            with self.assertRaisesRegex(ValueError,'changed a source-checked'):reader(doc,current,dict(edges=['supplyB0'],source_sha256=sh,graph_sha256='P'),sh,'P')
            with self.assertRaises(ValueError):reader(doc,g,dict(edges=['supplyB0'],source_sha256=sh,graph_sha256='stale'),sh,'P')

    def test_actual_entry_requires_complete_mapping_native_replay_and_input_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);paths={k:root/('mapping.json' if k=='mapping' else 'source-mapping-receipt.json' if k=='mapping_receipt' else k+'.json') for k in ('source','graph','mapping','mapping_receipt','calibration_policy','metric_policy')}
            for p in paths.values():p.write_text('{}','utf8')
            policy={k+'_sha256':sha(v) for k,v in paths.items()}
            with patch('inherited_circle_plan_attributes.verify_mapping',side_effect=ValueError('native correspondence changed')),self.assertRaisesRegex(ValueError,'native correspondence changed'):compute(paths,policy)
            policy['source_sha256']='stale'
            with self.assertRaisesRegex(ValueError,'input changed source'):compute(paths,policy)
        for name in ('native_canonical_main_family_view.py','checked_plan_DN_scope_attributes.py','calibrated_direct_dn_evidence.py','native_plan_projection_lengths.py'):
            self.assertIn(name,implementation_hashes())


if __name__=='__main__':unittest.main()
