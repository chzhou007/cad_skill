import copy,unittest
import ezdxf
from anchored_terminal_branch_reapplication import discover,source_terminal_outward,terminal_geometry
from test_ceiling_interface_glyph import NearbyOppositeGlyphTest

def fixture(angle=0,mirror=False):
    c,lines=NearbyOppositeGlyphTest().scene(angle,mirror);doc=ezdxf.new();ms=doc.modelspace()
    circle=ms.add_circle(c['center'],80,dxfattribs={'layer':'空调冷冻水供水'})
    glyph=[ms.add_line(x['a'],x['b'],dxfattribs={'layer':'空调立管、水平支管'})for x in lines[:4]]
    def node(n,x,y,kind='tee',**kw):return dict(node_id=n,x=x,y=y,node_type=kind,floor=3,system='supply',**kw)
    v=node('V',*c['center'],kind='virtual_equipment',subtype='out_of_plane_interface',source_handle=circle.dxf.handle,source_handles=[circle.dxf.handle,*[x.dxf.handle for x in glyph]])
    graph=dict(nodes=[node('P',500,2000),node('L',500,1500),node('R',500,2500),v],edges=[])
    for eid,a,b in [('M1','L','P'),('M2','P','R'),('B','P','V')]:graph['edges'].append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system='supply',floor_start=3,floor_end=3))
    return doc,graph,v,glyph

class BranchReuse(unittest.TestCase):
    def test_native_complete_glyph_rotation_mirror_and_reading_projection_preserve_graph(self):
        for angle in (0,37,90,270):
            for mirror in (False,True):
                doc,g,v,_=fixture(angle,mirror);old=copy.deepcopy(g)
                route,proof,projection=source_terminal_outward(doc,g,'P',{'M1','M2'},'supply',3)
                self.assertEqual(route['edges'],['B']);self.assertEqual(g,old)
                self.assertFalse(proof['physical_port_verified']);self.assertFalse(proof['remote_equipment_identity_inferred'])
                self.assertEqual(projection['original_subtype'],'out_of_plane_interface')
    def test_wrong_system_incomplete_glyph_and_unknown_terminal_do_not_get_projected(self):
        for mutation in ('system','glyph','unknown','review'):
            doc,g,v,glyph=fixture()
            if mutation=='system':doc.entitydb[v['source_handle']].dxf.layer='空调冷冻水回水'
            elif mutation=='glyph':v['source_handles'].pop()
            elif mutation=='unknown':v['subtype']='unresolved_source_terminal'
            else:v['review_required']=True
            with self.assertRaises(ValueError):source_terminal_outward(doc,g,'P',{'M1','M2'},'supply',3)
    def discovery(self):
        _,g,_,_=fixture();axis=copy.deepcopy(g)
        for n in axis['nodes']:n['node_id']='A'+n['node_id']
        for e in axis['edges']:
            e['edge_id']='A'+e['edge_id'];e['start_node_id']='A'+e['start_node_id'];e['end_node_id']='A'+e['end_node_id']
        records=[dict(floor=3,system='supply',mapping_id='C'+str(i),plan_edge_id=e,axis_edge_id='A'+e,original_correspondence=dict(ordinary_endpoint_pairs=pairs))for i,e,pairs in [(1,'M1',[['L','AL'],['P','AP']]),(2,'M2',[['P','AP'],['R','AR']])]]
        parent=dict(complete_corrected_parent_replayed=True,all_historical_main_roles_reapplied=True,records=records)
        provider=dict(ordinary_junction_mappings={'3':{'L':'AL','P':'AP','R':'AR'}},records=[dict(edge_id='A'+e,has_existing_correspondence=e!='B',correspondence_observations=[]if e=='B'else[dict(mapping_id='C'+str(i),plan_edges=[e],floor=3)])for i,e in enumerate(['M1','M2','B'],1)])
        return parent,provider,dict(plan=g,iso=axis)
    def test_two_independently_adopted_arms_constrain_drawing_branch_without_endpoint_identity(self):
        p,v,g=self.discovery();a,h=discover(p,v,g);self.assertEqual(len(a),1);self.assertFalse(h);self.assertEqual(a[0]['axis_edge_id'],'AB')
    def test_missing_second_adopted_arm_or_existing_provider_stops_reuse(self):
        p,v,g=self.discovery();v['records'][1]['correspondence_observations']=[]
        a,h=discover(p,v,g);self.assertFalse(a);self.assertIn('independently adopted',h[0]['reason'])
        p,v,g=self.discovery();v['records'][2]['has_existing_correspondence']=True
        a,h=discover(p,v,g);self.assertFalse(a);self.assertIn('old axis',h[0]['reason'])
    def test_plan_writer_overlap_and_anchor_alias_collapse_do_not_escape_guards(self):
        p,v,g=self.discovery();v['records'][0]['correspondence_observations'].append(dict(mapping_id='OLD',plan_edges=['B'],floor=3))
        self.assertIn('old plan',discover(p,v,g)[1][0]['reason'])
        p,v,g=self.discovery();v['ordinary_junction_mappings']['3']['L']='AP'
        with self.assertRaisesRegex(ValueError,'identities collapse'):discover(p,v,g)
if __name__=='__main__':unittest.main()
