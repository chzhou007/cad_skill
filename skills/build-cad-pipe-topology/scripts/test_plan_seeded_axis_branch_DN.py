import copy,math,unittest
from ezdxf.math import Matrix44
from test_inherited_marker_and_crossover_evidence import marker_scene
from inherited_exploded_ball_profiles import owner
from axis_unbranched_vertical_DN import native_items
from native_line_path_evidence import LAYERS
from plan_seeded_axis_branch_DN import collect,main_endpoint_support

def scene(angle=0,mirror=False):
    doc,g,marker=marker_scene();m=doc.modelspace();old={e['system']:e for e in g['edges']};nodes={n['node_id']:n for n in g['nodes']}
    for line in list(m.query('LINE')):m.delete_entity(line)
    main=[];records=[];scopes=[]
    for system,prefix in [('supply','S'),('return','R')]:
        branch=old[system];tip=branch['attribute_paths'][0][1];at=branch['attribute_paths'][0][0];sign=-1 if system=='supply'else 1
        bend=[at[0]+40*sign,at[1]-190]
        path=[at,[at[0],at[1]-150],bend,[bend[0],tip[1]],tip,branch['attribute_paths'][0][-1]]
        branch['attribute_paths']=[path];branch.update(floor_start=3,floor_end=3)
        for i,(a,b)in enumerate(zip(path,path[1:])):
            line=None if i==len(path)-2 else m.add_line(a,b,dxfattribs={'layer':LAYERS[system]})
            scopes.append(dict(edge_id=branch['edge_id'],path_index=0,segment_index=i,scope_points=copy.deepcopy([a,b]),system=system,
                floor_start=3,floor_end=3,direction_class='vertical'if abs(a[0]-b[0])<.05 else'horizontal',
                native_source_status='no_witness_in_scoped_search'if line is None else'single_source_line_covers',
                native_witnesses=[]if line is None else[dict(scope='modelspace',source_handle=line.dxf.handle)]))
        left=[at[0]-300,at[1]];right=[at[0]+300,at[1]]
        source=m.add_line(left,right,dxfattribs={'layer':LAYERS[system]})
        for side,a,b,sn,en in [('L',left,at,prefix+'L',prefix),('R',at,right,prefix,prefix+'R')]:
            nid=prefix+side
            nodes[nid]=dict(node_id=nid,node_type='virtual_equipment',floor=3,x=(a if side=='L'else b)[0],y=(a if side=='L'else b)[1])
            edge=dict(edge_id=prefix+side,system=system,start_node_id=sn,end_node_id=en,attribute_paths=[[a,b]],floor_start=3,floor_end=3)
            main.append(edge);s=dict(edge_id=edge['edge_id'],path_index=0,segment_index=0,scope_points=copy.deepcopy([a,b]),system=system,
                direction_class='horizontal',floor_start=3,floor_end=3,native_source_status='single_source_line_covers',
                native_witnesses=[dict(scope='modelspace',source_handle=source.dxf.handle)])
            scopes.append(s);records.append(dict(axis_edge_id=edge['edge_id'],axis_nodes=[sn,en],axis_attribute_paths=copy.deepcopy(edge['attribute_paths']),
                source_scope_id='PLAN-'+system,nominal_mm=200 if system=='supply'else 250,floor=3,system=system,horizontal_segment_domains=[copy.deepcopy(s)]))
    g['nodes']=list(nodes.values());g['edges']+=main
    if angle or mirror:
        matrix=Matrix44.scale(-1 if mirror else 1,1,1)@Matrix44.z_rotate(math.radians(angle))
        def xy(p):q=matrix.transform((*p,0));return[q.x,q.y]
        for e in m:
            if e.dxftype()=='LWPOLYLINE':e.set_points([xy(list(p))for p in e.get_points('xy')],format='xy')
            else:e.transform(matrix)
        for n in g['nodes']:
            n['x'],n['y']=xy([n['x'],n['y']])
            for p in n.get('ports',[]):p['x'],p['y']=xy([p['x'],p['y']])
        for e in g['edges']:e['attribute_paths']=[[xy(p)for p in path]for path in e['attribute_paths']]
        for s in scopes:s['scope_points']=[xy(p)for p in s['scope_points']]
        for r in records:
            r['axis_attribute_paths']=[[xy(p)for p in path]for path in r['axis_attribute_paths']]
            for s in r['horizontal_segment_domains']:s['scope_points']=[xy(p)for p in s['scope_points']]
        centre=list(owner().equipment_graph.polyline_center(list(marker.get_points('xy'))))
        node=next(n for n in g['nodes']if n['node_id']=='V');node['x'],node['y']=centre
        for edge in old.values():
            edge['attribute_paths'][0][-1]=centre
            next(s for s in scopes if s['edge_id']==edge['edge_id']and s['segment_index']==len(edge['attribute_paths'][0])-2)['scope_points'][1]=centre
    route=dict(inputs=dict(source=dict(sha256='S'),graph=dict(sha256='G')),records=scopes)
    return doc,g,route,records,{e['edge_id']:dict(diameter_nominal_mm=None)for e in g['edges']}

def run(args):
    doc,g,route,mains,values=args
    return collect(doc,g,route,mains,values,native_items(doc,g),'S','G')

class PlanSeededNativeBranches(unittest.TestCase):
    def test_plan_DN_reaches_each_native_branch_without_device_pairing_or_axis_seed(self):
        for angle,mirror in [(0,False),(37,True),(90,False)]:
            args=scene(angle,mirror);before=copy.deepcopy(args[1:]);r=run(args)
            self.assertEqual(r['counts']['qualified_branches'],2,r['pending']);self.assertEqual(args[1:],before)
            self.assertEqual({x['system']:x['nominal_mm']for x in r['records']},{'supply':200,'return':250})
            for row in r['records']:
                self.assertIsNone(row['physical_length_mm']);self.assertEqual(row['vertical_values_assigned'],0)
                self.assertFalse(row['whole_axis_DN_assigned']);self.assertTrue(row['axis_labels_validation_only'])
                self.assertFalse(row['internal_device_identities_assigned'])
                self.assertTrue(all(s['direction_class']=='horizontal'and s['segment_index']!=row['excluded_marker_display_segment']for s in row['horizontal_segment_domains']))

    def test_both_plan_main_arms_and_their_exact_endpoint_domains_are_required(self):
        for defect in('missing','other_scope','different_DN','wrong_endpoint','vertical','wrong_floor'):
            args=scene();owner=next(r for r in args[3]if r['axis_edge_id']=='SL')
            if defect=='missing':args[3].remove(owner)
            elif defect=='other_scope':owner['source_scope_id']='OTHER'
            elif defect=='different_DN':owner['nominal_mm']=300
            elif defect=='wrong_endpoint':owner['horizontal_segment_domains'][0]['scope_points']=[[0,0],[1,1]]
            elif defect=='vertical':owner['horizontal_segment_domains'][0]['direction_class']='vertical'
            else:owner['floor']=2
            r=run(args);self.assertNotIn('ES',{x['axis_edge_id']for x in r['records']},defect)
            self.assertIn('ES',{x['axis_edge_id']for x in r['pending']},defect)

    def test_downstream_new_or_composite_DN_blocks_the_entire_branch(self):
        for text in('DN80','DN300/DN200'):
            args=scene();edge=next(e for e in args[1]['edges']if e['edge_id']=='ES');a,b=edge['attribute_paths'][0][2:4]
            args[0].modelspace().add_text(text,dxfattribs={'insert':(a[0]+5,(a[1]+b[1])/2),'height':5,'rotation':90})
            r=run(args);self.assertNotIn('ES',{x['axis_edge_id']for x in r['records']})
            self.assertTrue(any(x['axis_edge_id']=='ES'and' DN' in x['reason']for x in r['pending']))

    def test_old_conflicting_scalar_source_Z_extra_ray_and_direction_stay_held(self):
        for defect in('old_DN','Z','extra_ray','direction','source'):
            args=scene();doc,g,route,owners,values=args;edge=next(e for e in g['edges']if e['edge_id']=='ES')
            if defect=='old_DN':values['ES']['diameter_nominal_mm']=80
            elif defect=='Z':
                s=next(s for s in route['records']if s['edge_id']=='ES'and s['segment_index']==0);line=doc.entitydb[s['native_witnesses'][0]['source_handle']]
                line.dxf.start=(*list(line.dxf.start)[:2],10);line.dxf.end=(*list(line.dxf.end)[:2],10)
            elif defect=='extra_ray':
                p=edge['attribute_paths'][0][0];doc.modelspace().add_line(p,(p[0]+100,p[1]+100),dxfattribs={'layer':LAYERS['supply']})
            elif defect=='direction':next(s for s in route['records']if s['edge_id']=='ES'and s['segment_index']==1)['direction_class']='unresolved'
            else:route['inputs']['source']['sha256']='OTHER'
            if defect=='source':
                with self.assertRaisesRegex(ValueError,'bindings'):run(args)
            else:self.assertNotIn('ES',{x['axis_edge_id']for x in run(args)['records']},defect)

    def test_missing_native_pipe_and_corrupted_Chinese_are_not_hidden(self):
        args=scene();s=next(s for s in args[2]['records']if s['edge_id']=='ES'and s['segment_index']==1)
        args[0].modelspace().delete_entity(args[0].entitydb[s['native_witnesses'][0]['source_handle']])
        self.assertNotIn('ES',{x['axis_edge_id']for x in run(args)['records']})
        args=scene();args[0].modelspace().add_text('管径\ufffd')
        with self.assertRaisesRegex(ValueError,'unreadable'):run(args)

    def test_F_leader_blocks_even_when_its_two_values_equal_the_main(self):
        args=scene();edge=next(e for e in args[1]['edges']if e['edge_id']=='ES');a,b=edge['attribute_paths'][0][3:5]
        x=(a[0]+b[0])/2;y=a[1]-36;m=args[0].modelspace()
        m.add_lwpolyline([(x,y+30),(x,y+40),(x+20,y+40)],dxfattribs={'layer':'DN'})
        m.add_lwpolyline([(x,y),(x,y+30),(x+20,y+30)],dxfattribs={'layer':'DN'})
        for offset in(31,41):m.add_text('DN200',dxfattribs={'insert':(x+2,y+offset),'height':4,'layer':'DN'})
        result=run(args)
        self.assertNotIn('ES',{x['axis_edge_id']for x in result['records']})
        self.assertTrue(any(x['axis_edge_id']=='ES'and'F' in x['reason']for x in result['pending']),result['pending'])

if __name__=='__main__':unittest.main()
