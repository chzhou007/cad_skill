import copy,unittest
import ezdxf
from compound_carrier_members import carrier_risks,member

def fixture():
    nodes=[dict(node_id='P'+str(i),node_type='tee',floor=3,system='supply',x=x,y=0)for i,x in enumerate((0,1000))]
    edge=dict(edge_id='PE',start_node_id='P0',end_node_id='P1',system='supply',start_floor=3,end_floor=3,attribute_paths=[[[1000,0],[0,0]]])
    waves=[dict(tee_id='P'+str(i),equipment_id='DEVICE-'+str(i),system='supply',target=dict(source_handle='PL'),branch_edge='BR'+str(i),wave=dict(wave_handle='W'+str(i)))for i in(0,1)]
    plan=dict(nodes=nodes,edges=[edge],sourceWaveMainCohort=dict(records=waves));axis=copy.deepcopy(plan)
    for n in axis['nodes']:n['node_id']=n['node_id'].replace('P','A');n['node_type']='physical_junction'
    axis['edges']=[dict(edge,edge_id='AE',start_node_id='A0',end_node_id='A1')]
    row=dict(kind='same_floor_T_to_T_main',floor=3,system='supply',plan_edges=['PE'],iso_edges=['AE'],plan_start='P0',plan_end='P1',iso_start='A0',iso_end='A1',mapping_id='M')
    corridor=dict(source_LINE='PL',system='supply',declarations=[dict(handle='C1',members=[dict(declaration_index=0,nominal_mm=300,source_level_text='3.600'),dict(declaration_index=1,nominal_mm=200,source_level_text='3.000')])])
    caption=dict(text=dict(nominal_mm=200,source_level_text='3.0',literal_level_key='3'),native_pipe=dict(source_LINE='AL',system='supply'))
    native={view:dict(coverage=dict(edges=[dict(edge_id=eid,segments=[dict(status='single_source_line_covers',witnesses=[dict(scope='modelspace',source_handle=handle)])])]),junctions={prefix+'0':dict(verified=True),prefix+'1':dict(verified=True)})for view,eid,handle,prefix in(('plan','PE','PL','P'),('iso','AE','AL','A'))}
    metric=dict(value_mm=1000,installed_whole_edge_length_mm=None,pieces=[dict(plan_edge='PE',path_index=0,segment_index=0,source_line_handle='PL',points=[[1000,0],[0,0]],length_mm=1000)])
    return row,plan,axis,'PL','AL',corridor,caption,native,metric

class Tests(unittest.TestCase):
    def test_LINE_lineage_barrier_survives_edge_split_and_ignores_other_LINE(self):
        d=ezdxf.new('R2013');m=d.modelspace();line=m.add_line((0,0),(2000,0),dxfattribs={'layer':'空调冷冻水供水'});other=m.add_line((0,500),(2000,500),dxfattribs={'layer':'空调冷冻水供水'})
        m.add_text('DN300(3.600)/DN200(3.000)',dxfattribs={'insert':(200,50),'height':40,'layer':'空调平面'})
        graph=dict(edges=[dict(edge_id='E1',system='supply',source_handles=[line.dxf.handle],attribute_paths=[[[0,0],[1000,0]]]),dict(edge_id='E2',system='supply',source_handles=[line.dxf.handle],attribute_paths=[[[2000,0],[1000,0]]]),dict(edge_id='UNRELATED',system='supply',source_handles=[other.dxf.handle],attribute_paths=[[[0,500],[2000,500]]])])
        r=carrier_risks(d,graph,'s'*64);self.assertEqual(len(r['corridors']),1)
        self.assertEqual({r['edge_id']for r in r['corridors'][0]['edges']},{'E1','E2'});self.assertFalse(r['scalar_DN_allowed_without_member_proof'])

    def test_member_uses_plan_DN_literal_level_and_keeps_original_path_order(self):
        args=fixture();args[1]['edges'][0]['diameter_nominal_mm']=300;before=copy.deepcopy(args);r=member(*args)
        self.assertEqual(r['nominal_mm'],200);self.assertEqual(r['plan_run_centerline_mm'],1000);self.assertEqual(r['plan_attribute_paths'],[[[1000,0],[0,0]]])
        self.assertEqual(args,before);self.assertFalse(r['DN_used_for_mapping']);self.assertIsNone(r['physical_elevation_mm']);self.assertIsNone(r['installed_whole_length_mm'])
        self.assertEqual(r['plan_declarations'][0]['member']['declaration_index'],1);self.assertFalse(r['other_member_connections_inferred'])

    def test_missing_level_cannot_be_selected_by_equal_DN(self):
        args=list(fixture());args[6]['text']['literal_level_key']='unknown'
        with self.assertRaisesRegex(ValueError,'literal source level'):member(*args)

    def test_conflicting_plan_declarations_axis_crosscheck_and_service_fail(self):
        args=list(fixture());args[5]['declarations'].append(dict(handle='CONFLICT',members=[dict(nominal_mm=250,source_level_text='3.000')]))
        with self.assertRaisesRegex(ValueError,'declarations conflict'):member(*args)
        args=list(fixture());args[6]['text']['nominal_mm']=300
        with self.assertRaisesRegex(ValueError,'axis cross-check'):member(*args)
        args=list(fixture());args[6]['native_pipe']['system']='return'
        with self.assertRaisesRegex(ValueError,'service differs'):member(*args)

    def test_fake_T_anchor_mixed_carrier_and_altered_metric_fail(self):
        args=list(fixture());args[1]['sourceWaveMainCohort']['records'].pop()
        with self.assertRaisesRegex(ValueError,'branch anchors'):member(*args)
        args=list(fixture());args[7]['iso']['coverage']['edges'][0]['segments'][0]['witnesses'][0]['source_handle']='OTHER'
        with self.assertRaisesRegex(ValueError,'mixed or ambiguous'):member(*args)
        args=list(fixture());args[8]['pieces'][0]['points']=[[1,0],[1001,0]]
        with self.assertRaisesRegex(ValueError,'native points differ'):member(*args)
if __name__=='__main__':unittest.main()
