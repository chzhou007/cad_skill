import copy,unittest
from unittest.mock import patch
import ezdxf
import confirmed_member_plan_paths as owner

def fixture():
    doc=ezdxf.new();ms=doc.modelspace();source='a'*64;graph_hash='b'*64
    for name in owner.LAYERS.values():doc.layers.new(name)
    graph=dict(metadata=dict(source_sha256=source),nodes=[],edges=[],confirmedSideviewCanonicalization=dict(records=[]))
    labels=[];projections={};equipment=['A','B','C']
    for n in equipment:graph['nodes'].append(dict(node_id=n,node_type='equipment',floor=2,x=0,y=0))
    by_system={}
    for system,y in (('supply',0),('return',-600)):
        line=ms.add_line((0,y),(10000,y),dxfattribs=dict(layer=owner.LAYERS[system]))
        label=ms.add_text('DN300(3.600)/DN200(3.000)',dxfattribs=dict(insert=(5000,y+132),height=350))
        labels.append(dict(handle=label.dxf.handle,source_LINE_membership_confirmed=False,members=[dict(role='other_lane_separated_in_axis_view',nominal_mm=300),dict(role='sideview_network_lane',nominal_mm=200,declaration_slot_id=system)]))
        by_system[system]=label.dxf.handle
        for i,name in enumerate(equipment):
            tee=system+name;eid='BRANCH-'+tee;x=1000+i*4000;node=dict(node_id=tee,x=i*10000,y=y-20000,node_type='tee',floor=2,system=system)
            graph['nodes'].append(node);graph['edges'].append(dict(edge_id=eid,system=system,source_sideview_equipment_interface=dict(equipment_id=name)))
            relation=dict(canonical_edge=eid,system=system,question_id=tee);graph['confirmedSideviewCanonicalization']['records'].append(relation)
            projections[eid]=dict(equipment_id=name,system=system,canonical_tee=tee,question_id=tee,plan_main_hit=dict(source_handle=line.dxf.handle,point=[x,y]))
        for a,b in zip(equipment,equipment[1:]):
            graph['edges'].append(dict(edge_id=system+a+b,system=system,start_node_id=system+a,end_node_id=system+b,start_floor=2,end_floor=2,
                attribute_paths=[[[0,y-20000],[10000,y-20000]]],equipment_names=['DETAIL-VALVE-'+system+a+b]))
    lanes=dict(source_sha256=source,records=labels);policy=dict(groups=[dict(group_id='G',equipment_ids=equipment,compound_text_by_system=by_system,floor=2)])
    units=dict(status='native_mm_units_corroborated_not_pipe_dimension_assignment',plan_window=[-100,11000,-1000,1000])
    return doc,graph,lanes,policy,units,projections,source,graph_hash

class Tests(unittest.TestCase):
    def run_collect(self,values,components=None):
        doc,graph,lanes,policy,units,projections,source,gh=values
        with patch.object(owner,'projection',side_effect=lambda d,g,r,*args:copy.deepcopy(projections[r['canonical_edge']])):
            return owner.collect(doc,graph,components or [],lanes,policy,units,source,gh)
    def test_same_projected_carrier_does_not_duplicate_Ts_or_use_detail_span(self):
        values=fixture();before=copy.deepcopy(values[1]);r=self.run_collect(values)
        self.assertEqual(r['counts'],dict(groups=1,anchors=6,member_main_edges=4,run_centerline_ready=4,net_pipe_cut_lengths_assigned=0))
        self.assertEqual({x['horizontal_plan_run_centerline_mm']for x in r['records']},{4000})
        self.assertEqual({x['nominal_mm']for x in r['records']},{200});self.assertEqual(values[1],before)
        self.assertFalse(r['other_member_connections_inferred']);self.assertFalse(r['physical_pipe_count_inferred'])
        for row in r['records']:
            self.assertIsNone(row['installed_whole_edge_length_mm']);self.assertIsNone(row['net_pipe_cut_length_mm']);self.assertIsNone(row['canonical_component_plan_stations_mm'])
            self.assertFalse(row['detail_inline_positions_scaled_to_plan']);self.assertTrue(row['canonical_detail_inline_components'])
    def test_projected_component_keeps_member_allocation_unknown_without_changing_route_extent(self):
        r=self.run_collect(fixture(),[dict(device_name='AMBIGUOUS-VALVE',x='3000',y='0')])
        changed=[x for x in r['records']if x['projected_inline_components']]
        self.assertEqual(len(changed),1);self.assertEqual(changed[0]['projected_component_member_allocation'],'unresolved')
        self.assertEqual(changed[0]['horizontal_plan_run_centerline_mm'],4000);self.assertIsNone(changed[0]['net_pipe_cut_length_mm'])
    def test_competing_native_source_line_is_rejected(self):
        values=fixture();values[0].modelspace().add_line((0,0),(10000,0),dxfattribs=dict(layer=owner.LAYERS['supply']))
        with self.assertRaisesRegex(ValueError,'competing native LINEs'):self.run_collect(values)
    def test_incomplete_or_cross_service_topology_and_moved_label_do_not_pass(self):
        for defect in ('missing_main','mixed_service','wrong_floor','label_outside','label_rotation','duplicate_group','wrong_source','wrong_units'):
            with self.subTest(defect=defect):
                v=fixture();doc,g,lanes,policy,units,_,_,_=v
                if defect=='missing_main':g['edges']=[e for e in g['edges']if e['edge_id']!='supplyAB']
                elif defect=='mixed_service':next(e for e in g['edges']if e['edge_id']=='supplyAB')['system']='return'
                elif defect=='wrong_floor':g['nodes'][0]['floor']=3
                elif defect=='label_outside':doc.entitydb[policy['groups'][0]['compound_text_by_system']['supply']].dxf.insert=(20000,132)
                elif defect=='label_rotation':doc.entitydb[policy['groups'][0]['compound_text_by_system']['supply']].dxf.rotation=90
                elif defect=='duplicate_group':policy['groups']*=2
                elif defect=='wrong_source':lanes['source_sha256']='c'*64
                elif defect=='wrong_units':units['status']='detail_units'
                with self.assertRaises(ValueError):self.run_collect(v)

if __name__=='__main__':unittest.main()
