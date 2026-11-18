import copy,unittest
import ezdxf
from compound_member_interfaces import group
from native_paired_caption_geometry import collect

def fixture():
    p=ezdxf.new('R2013');a=ezdxf.new('R2013');pm=p.modelspace();am=a.modelspace();layer='空调冷冻水供水';rlayer='空调冷冻水回水'
    pl=pm.add_line((0,0),(6000,0),dxfattribs={'layer':layer})
    circles=[pm.add_circle((x,0),100,dxfattribs={'layer':layer}) for x in (1000,5000)]
    al=am.add_line((1000,0),(5000,0),dxfattribs={'layer':layer})
    am.add_line((1000,400),(5400,400),dxfattribs={'layer':rlayer})
    upper=am.add_line((0,2000),(6000,2000),dxfattribs={'layer':layer});am.add_line((0,2400),(6000,2400),dxfattribs={'layer':rlayer})
    vertical=[am.add_line((x,0),(x,2000),dxfattribs={'layer':layer}) for x in (1000,5000)]
    branches=[am.add_line((x,0),(x,-1000),dxfattribs={'layer':layer}) for x in (2000,4000)]
    for text,pos in [('DN200(3.000)',(5500,-380)),('DN200(3.000)',(5500,290)),('DN300(3.600)',(3000,1615)),('DN300(3.600)',(3483,2494))]:am.add_text(text,dxfattribs={'insert':pos,'height':350,'layer':'DN'})
    def node(n,x,y,kind='tee'):return dict(node_id=n,x=x,y=y,node_type=kind,floor=3,system='supply',review_required=False)
    plan=dict(nodes=[node('P1',2000,0),node('P2',4000,0)],edges=[])
    axis=dict(nodes=[node('T1',2000,0),node('T2',4000,0),node('U1',1000,2000),node('U2',5000,2000),node('LEFT',0,2000,'boundary'),node('RIGHT',6000,2000,'boundary'),node('D1',2000,-1000,'equipment'),node('D2',4000,-1000,'equipment')],edges=[])
    def edge(eid,start,end,points,handle):return dict(edge_id=eid,start_node_id=start,end_node_id=end,attribute_paths=[points],source_handles=[handle],system='supply',floor_start=3,floor_end=3,connection_mode='continuous_original_cad_pipe')
    axis['edges']=[edge('LOWER','T1','T2',[[2000,0],[4000,0]],al.dxf.handle),edge('MAIN','U1','U2',[[1000,2000],[5000,2000]],upper.dxf.handle),
        edge('APP1','T1','U1',[[2000,0],[1000,0],[1000,2000]],al.dxf.handle),edge('APP2','T2','U2',[[4000,0],[5000,0],[5000,2000]],al.dxf.handle),
        edge('OUT1','LEFT','U1',[[0,2000],[1000,2000]],upper.dxf.handle),edge('OUT2','U2','RIGHT',[[5000,2000],[6000,2000]],upper.dxf.handle),
        edge('BR1','D1','T1',[[2000,-1000],[2000,0]],branches[0].dxf.handle),edge('BR2','D2','T2',[[4000,-1000],[4000,0]],branches[1].dxf.handle)]
    captions=collect(a);old=next(o for pair in captions['pairs'] for o in pair['observations'] if o['native_pipe']['source_LINE']==al.dxf.handle)
    declarations=[dict(handle='PLAN-TEXT',members=[dict(nominal_mm=200,source_level_text='3.000'),dict(nominal_mm=300,source_level_text='3.600')])]
    rows=[dict(member_scope_id='LOWER',system='supply',floor=3,plan_LINE=pl.dxf.handle,axis_LINE=al.dxf.handle,nominal_mm=200,literal_level_key='3',mapping_id='M0',axis_edge_id='LOWER',
        anchors=[dict(plan_T='P1',axis_T='T1',equipment_id='D1',plan_branch='PB1'),dict(plan_T='P2',axis_T='T2',equipment_id='D2',plan_branch='PB2')],axis_caption_crosscheck=old,plan_declarations=[dict(text_handle='PLAN-TEXT',member=declarations[0]['members'][0])])]
    corridor=dict(declarations=declarations)
    units=dict(plan_window=[-100,6100,-1500,3000])
    hashes=dict(plan_source='p'*64,axis_source='a'*64,plan_graph='g'*64,axis_graph='h'*64)
    return [p,a,plan,axis,rows,corridor,captions,units,[0,45,135],hashes],circles,pl

class Tests(unittest.TestCase):
    def test_two_members_rebuilt_main_metric_complete_approach_local_rise_unknown(self):
        args,_,_=fixture();before=(copy.deepcopy(args[2]),copy.deepcopy(args[3]),copy.deepcopy(args[4]));r=group(*args)
        self.assertEqual(len(r['new_member_nodes']),2);self.assertEqual(len(r['new_member_edges']),3);self.assertEqual(len(r['external_ports']),2)
        main=next(x for x in r['records'] if x['kind']=='primary_member_main');approaches=[x for x in r['records'] if x['kind']!='primary_member_main']
        self.assertEqual(main['nominal_mm'],300);self.assertEqual(main['complete_horizontal_centerline_route_mm'],4000)
        self.assertEqual({x['nominal_mm'] for x in approaches},{200});self.assertEqual([x['plan_projection']['value_mm'] for x in approaches],[1000,1000])
        self.assertTrue(all(x['complete_horizontal_centerline_route_mm'] is None and x['local_rise_length_mm'] is None and not x['level_difference_used_as_length'] for x in approaches))
        self.assertTrue(all(x['installed_whole_length_mm'] is None and x['net_pipe_cut_length_mm'] is None and not x['DN_used_for_mapping'] for x in r['records']))
        self.assertEqual((args[2],args[3],args[4]),before)
    def test_native_line_direction_does_not_change_member_ids(self):
        args,_,line=fixture();r=group(*args);start,end=line.dxf.start,line.dxf.end;line.dxf.start=end;line.dxf.end=start
        other=group(*args);self.assertEqual({e['edge_id'] for e in r['new_member_edges']},{e['edge_id'] for e in other['new_member_edges']})
        self.assertEqual({x['axis_edge_id']:x['nominal_mm'] for x in r['records']},{x['axis_edge_id']:x['nominal_mm'] for x in other['records']})
    def test_missing_circle_ordinary_crossing_and_inner_circle_do_not_infer_connection(self):
        for kind in ('missing','ordinary','interior'):
            args,circles,_=fixture();m=args[0].modelspace()
            if kind in ('missing','ordinary'):
                for c in (circles[:1] if kind=='missing' else circles):m.delete_entity(c)
            else:m.add_circle((3000,0),100,dxfattribs={'layer':'空调冷冻水供水'})
            with self.assertRaises(ValueError):group(*args)
    def test_new_native_DN_stops_inheritance_and_level_tokens_are_not_measurements(self):
        args,_,_=fixture();args[1].modelspace().add_text('DN150',dxfattribs={'insert':(980,1000),'height':40,'rotation':90,'layer':'DN'})
        with self.assertRaisesRegex(ValueError,'DN changes'):group(*args)
        args,_,_=fixture();args[1].modelspace().add_text('DN200',dxfattribs={'insert':(980,1000),'height':40,'rotation':90,'text_generation_flag':2,'layer':'DN'})
        with self.assertRaisesRegex(ValueError,'unsupported native DN'):group(*args)
        args,_,_=fixture();args[5]['declarations'][0]['members'][1]['source_level_text']='3.000'
        with self.assertRaisesRegex(ValueError,'literal member level'):group(*args)
    def test_conflicting_axis_caption_or_disconnected_chain_cannot_choose_by_DN(self):
        args,_,_=fixture();args[6]['pairs']=[copy.deepcopy(x) for x in args[6]['pairs']]
        for pair in args[6]['pairs']:
            for o in pair['observations']:
                if o['text']['literal_level_key']=='3.6':o['text']['nominal_mm']=250
        with self.assertRaisesRegex(ValueError,'cross-check'):group(*args)
        args,_,_=fixture();args[4].append(copy.deepcopy(args[4][0]))
        with self.assertRaisesRegex(ValueError,'chain'):group(*args)
    def test_nested_or_MTEXT_annotation_cannot_be_silently_ignored(self):
        for kind in ('nested','mtext'):
            args,_,_=fixture();d=args[1]
            if kind=='nested':
                block=d.blocks.new('NESTED-DN');block.add_text('DN150',dxfattribs={'height':40,'rotation':90});d.modelspace().add_blockref('NESTED-DN',(980,1000))
            else:d.modelspace().add_mtext('DN150',dxfattribs={'insert':(980,1000),'char_height':40})
            with self.assertRaisesRegex(ValueError,'original.*annotation reader'):group(*args)

if __name__=='__main__':unittest.main()
