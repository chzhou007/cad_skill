import copy,unittest
from test_reconstruct_sideview_equipment_ownership import case,POLICY
from reconstruct_sideview_equipment_ownership import apply
from native_sideview_equipment_branch_evidence import collect,validate_owner

class SideviewBranchEvidenceTests(unittest.TestCase):
    def built(self,boundary=False):
        d,g,e=case(boundary=boundary);out,_=apply(g,e,POLICY,'S','CURRENT');return d,out

    def test_node_and_non_node_origins_use_the_same_native_T_and_unknown_port_contract(self):
        for boundary in (False,True):
            doc,g=self.built(boundary);before=copy.deepcopy(g)
            for record in g['sourceSideviewEquipmentOwnership']['records']:
                edge=next(x for x in g['edges'] if x['edge_id']==record['edge_id']);validate_owner(g,edge,'S')
                tee=record['source_alias']['native_detail_tee']['tee'];e=collect(doc,g,tee,'S','DERIVED')
                self.assertEqual(len(e['junctions'][0]['source_rays']),3);self.assertFalse(e['physical_ports_verified']);self.assertIsNone(e['physical_length_mm'])
                self.assertEqual(e['source_view_domain'],'detail_drawing_only_not_plan_metric_proof')
            self.assertEqual(g,before)

    def test_stale_owner_alias_snapshot_and_metric_promotion_rejected(self):
        for mode in ('owner','alias','snapshot','physical','metric','floor','confirmation'):
            d,g=self.built();root=g['sourceSideviewEquipmentOwnership'];r=root['records'][0];edge=next(x for x in g['edges'] if x['edge_id']==r['edge_id'])
            if mode=='owner':edge['end_node_id']='another'
            if mode=='alias':root['node_aliases'][r['original_canonical_interface_id']]='another'
            if mode=='snapshot':edge['attribute_paths'][0][1][0]+=.1
            if mode=='physical':r['physical_port_verified']=True
            if mode=='metric':edge['source_view_context']['metric_verified_by_this_stage']=True
            if mode=='floor':r['endpoint_floor_evidence']['floor']=2
            if mode=='confirmation':g['confirmedSideviewCanonicalization']['records'][0]['answer']['decision']='未确认'
            with self.subTest(mode=mode),self.assertRaises((ValueError,KeyError)):validate_owner(g,edge,'S')

    def test_unproven_fourway_and_native_duplicate_source_are_not_accepted(self):
        for mode in ('fourway','native'):
            d,g=self.built();r=g['sourceSideviewEquipmentOwnership']['records'][0];tee=r['source_alias']['native_detail_tee']['tee'];edge=next(x for x in g['edges'] if x['edge_id']==r['edge_id'])
            if mode=='fourway':g['edges'].append(dict(edge,edge_id='EXTRA'))
            else:
                line=d.entitydb[edge['source_handles'][0]];d.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(d,g,tee,'S','DERIVED')

if __name__=='__main__':unittest.main()
