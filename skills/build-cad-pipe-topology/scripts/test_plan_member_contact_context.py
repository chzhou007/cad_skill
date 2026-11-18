import copy,math,unittest
from test_native_ball_contact_reapplication import fixture
from native_ball_contact_reapplication import footprint
from native_flange_contact_ownership import flange_contacts
from native_line_path_evidence import LAYERS
from plan_member_contact_context import VIEW,projected_contacts,projected_plan_owners,contact_scope,bounded_plan_profiles

class Tests(unittest.TestCase):
    def planar(self,rotation=0,mirror=1,extrusion=(0,0,1)):
        doc,graph,insert,pipe,row=fixture(rotation,mirror,extrusion)
        insert.dxf.insert=(insert.dxf.insert.x,insert.dxf.insert.y,-.4598153620504775)
        row['edge_id']='MAIN';geometry=footprint(insert)
        return doc,graph,insert,pipe,row,geometry
    def test_rotated_mirrored_and_OCS_plan_contacts_keep_raw_Z_and_axis_guard(self):
        for angle in [0,37,90,180,270]:
            for mirror in [-1,1]:
                for extrusion in [(0,0,1),(0,0,-1)]:
                    doc,g,ins,line,row,geo=self.planar(angle,mirror,extrusion);before=copy.deepcopy(geo);a,b=list(line.dxf.start),list(line.dxf.end)
                    self.assertIsNone(flange_contacts(geo,a,b))
                    c=projected_contacts(geo,a,b,view=VIEW);self.assertEqual(len(c),2);self.assertEqual(geo,before)
                    self.assertAlmostEqual(c[0]['source_XYZ_separation'],abs(geo['flanges_WCS'][0][0][2]-a[2]))
                    self.assertEqual(c[0]['source_flange_WCS'],list(geo['flanges_WCS'][0]));self.assertFalse(c[0]['raw_3D_contact_proved'])
                    self.assertIsNone(flange_contacts(geo,a,b))
    def test_wrong_view_tilt_and_changed_tolerance_do_not_relax_3D_rule(self):
        _,_,_,line,_,geo=self.planar();a,b=list(line.dxf.start),list(line.dxf.end)
        for view in ['axis','generic','']:
            with self.assertRaises(ValueError):projected_contacts(geo,a,b,view=view)
        with self.assertRaises(ValueError):projected_contacts(geo,a,b,.5,view=VIEW)
        b[2]=1
        with self.assertRaises(ValueError):projected_contacts(geo,a,b,view=VIEW)
        b[2]=0;geo['flanges_WCS'][0][0][2]+=1
        with self.assertRaises(ValueError):projected_contacts(geo,a,b,view=VIEW)
    def test_both_native_finite_flange_contacts_still_required(self):
        _,_,_,line,_,geo=self.planar();a,b=list(line.dxf.start),list(line.dxf.end);ports=geo['ports_WCS']
        middle=[(ports[0][i]+ports[1][i])/2 for i in range(3)];middle[2]=0
        self.assertIsNone(projected_contacts(geo,a,middle,view=VIEW))
    def test_duplicate_projected_pipes_and_source_owner_conflicts_stay_ambiguous(self):
        doc,g,_,line,_,geo=self.planar();p=list(doc.modelspace().query('LINE'));native,owners=projected_plan_owners(geo,p,g);self.assertEqual(len(native),len(owners));self.assertEqual(len(native),1)
        doc.modelspace().add_line((line.dxf.start.x,line.dxf.start.y,10),(line.dxf.end.x,line.dxf.end.y,10),dxfattribs=dict(layer=LAYERS['return']))
        native,owners=projected_plan_owners(geo,list(doc.modelspace().query('LINE')),g);self.assertEqual(len(native),2);self.assertEqual(owners,[])
    def test_profile_scope_preserves_source_graph_inventory_and_unknown_parameters(self):
        doc,g,ins,line,row,geo=self.planar();before=copy.deepcopy(g);old=copy.deepcopy(row);profile=bounded_plan_profiles(doc,g,[row],{'MAIN':g['edges'][0]['attribute_paths']},None)
        self.assertEqual(profile['profiles']['MAIN'],{'ball_valve':1});self.assertEqual(g,before);self.assertEqual(row,old);self.assertIsNone(profile['records'][0]['original_instance']['resistance'])
        self.assertTrue(profile['raw_source_Z_preserved']);self.assertFalse(profile['raw_3D_contact_proved'])
    def test_outside_component_is_audited_and_cut_or_enclosing_scope_rejected(self):
        doc,g,_,line,row,geo=self.planar();a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2];p,q=[x['point_WCS'][:2]for x in projected_contacts(geo,list(line.dxf.start),list(line.dxf.end),view=VIEW)];small=[[a,[(a[i]+p[i])/2 for i in range(2)]]]
        profile=bounded_plan_profiles(doc,g,[row],{'MAIN':small},None);self.assertEqual(profile['records'],[]);self.assertEqual(profile['source_component_scope_audit'][0]['scope'],'excluded_outside_external_route_original_owner_retained')
        mid=[(p[i]+q[i])/2 for i in range(2)]
        for paths in [[[a,mid]],[[[(p[i]+mid[i])/2 for i in range(2)],[(q[i]+mid[i])/2 for i in range(2)]]]]:
            with self.assertRaises(ValueError):bounded_plan_profiles(doc,g,[row],{'MAIN':paths},None)
    def test_prior_duplicate_missing_source_or_new_fragment_are_not_hidden_by_clipping(self):
        doc,g,_,_,row,_=self.planar();scopes={'MAIN':g['edges'][0]['attribute_paths']}
        for rows in [[row,copy.deepcopy(row)],[dict(row,source_top_handle='MISSING')]]:
            with self.assertRaises(ValueError):bounded_plan_profiles(doc,g,rows,scopes,None)
        with self.assertRaises(ValueError):bounded_plan_profiles(doc,g,[row],{'MAIN':[[[0,0],[1,0]]]},None)

if __name__=='__main__':unittest.main()
