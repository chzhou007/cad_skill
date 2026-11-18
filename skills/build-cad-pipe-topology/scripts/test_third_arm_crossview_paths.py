import copy,unittest
import ezdxf
from third_arm_crossview_paths import discover,prove,native_component_profiles
from rebuild_third_arm_crossview_batch import inherit
from native_line_path_evidence import LAYERS

def fixture():
    docs={};graphs={};hashes={}
    for view,prefix,iso in [('plan','P',False),('iso','I',True)]:
        positions={'A':(0,0),'U':(100,100)if iso else(0,100),'L':(-100,0),'R':(100,0),'UL':(0,100)if iso else(-100,100),'UR':(200,100)if iso else(100,100)}
        doc=ezdxf.new();edges=[];nodes=[dict(node_id=prefix+n,node_type='tee'if n in('A','U')else'virtual_equipment',floor=2,system='supply',x=p[0],y=p[1])for n,p in positions.items()]
        for j,(a,b)in enumerate([('A','U'),('A','L'),('A','R'),('U','UL'),('U','UR')]):
            line=doc.modelspace().add_line(positions[a],positions[b],dxfattribs={'layer':LAYERS['supply']})
            edges.append(dict(edge_id=prefix+str(j),start_node_id=prefix+a,end_node_id=prefix+b,system='supply',floor_start=2,floor_end=2,attribute_paths=[[list(positions[a]),list(positions[b])]],source_handles=[line.dxf.handle],connection_mode='continuous_original_cad_pipe'))
        source=('a'if view=='plan'else'b')*64
        graphs[view]=dict(nodes=nodes,edges=edges,metadata=dict(source_sha256=source));docs[view]=doc;hashes[view]=dict(source_sha256=source,graph_sha256='c'*64)
    rows=[]
    for j in range(5):
        obs=[dict(provider='old_native',domain='ordinary_local_graph',mapping_id='K'+str(j),floor=2,plan_edges=['P'+str(j)],grouped_axis_edges=['I'+str(j)])]if j in(1,2)else[]
        rows.append(dict(edge_id='I'+str(j),classification='horizontal_only',has_existing_correspondence=bool(obs),correspondence_observations=obs))
    provider=dict(records=rows,ordinary_junction_mappings={'2':{'PA':'IA'}},member_domain_observations=[dict(id='MEMBER:keep')],current_component_inventory=dict(count=9,unknown=['keep']),remaining_horizontal_attributes=[dict(edge_id='I0',floor=2,next_scope='apply_existing_native_crossview_discovery_to_unmatched_horizontal_path',known_whole_DN=None,complete_centerline=False)],current_horizontal_frontier={},counts={})
    return docs,graphs,hashes,provider,dict(plan=[],iso=[])

class Tests(unittest.TestCase):
    def test_native_three_ray_paths_infer_remaining_arm_preserve_every_parent(self):
        docs,g,h,p,c=fixture();before=copy.deepcopy((g,p,c));good,held=discover(g,p,2,c)
        self.assertEqual(len(good),1)
        record=prove(good[0],g,docs,p,h,{},c,[0,45,135],None)
        result=inherit(p,[record]);self.assertEqual(result['ordinary_junction_mappings']['2']['PU'],'IU')
        self.assertEqual(result['counts']['existing_correspondence_edges'],3)
        self.assertEqual(result['member_domain_observations'],p['member_domain_observations'])
        self.assertEqual(result['current_component_inventory'],p['current_component_inventory'])
        self.assertEqual((g,p,c),before);self.assertFalse(record['DN_used_for_matching']);self.assertEqual(record['physical_values_assigned'],0)

    def test_existing_member_remote_conflict_mixed_scope_and_fragmented_carrier_are_held(self):
        for mode in('member','endpoint','mixed','fragments','review'):
            docs,g,h,p,c=fixture()
            if mode=='member':p['records'][0].update(has_existing_correspondence=True,correspondence_observations=[dict(provider='member',domain='physical_member_graph',mapping_id='M',plan_edges=['MEMBER:PATH'])])
            elif mode=='endpoint':
                p['ordinary_junction_mappings']['2']['PU']='OTHER'
                g['iso']['nodes'].append(dict(node_id='OTHER',node_type='tee',floor=2,system='supply',x=999,y=999))
            elif mode=='mixed':p['records'][0]['classification']='mixed_horizontal_vertical'
            elif mode=='fragments':g['plan']['edges'][0]['attribute_paths']=[[[0,0],[0,40]],[[0,60],[0,100]]]
            else:next(n for n in g['plan']['nodes']if n['node_id']=='PU')['review_required']=True
            with self.subTest(mode=mode):self.assertFalse(discover(g,p,2,c)[0])

    def test_DN_and_lengths_do_not_choose_the_topology(self):
        docs,g,h,p,c=fixture();first=discover(g,p,2,c)[0]
        for v in g:
            for edge in g[v]['edges']:edge.update(nominal_mm=999 if v=='plan'else 1,physical_length_mm=None)
        self.assertEqual(discover(g,p,2,c)[0],first)

    def test_material_difference_without_source_audit_is_not_accepted(self):
        docs,g,h,p,c=fixture();c['plan']=[dict(edge_id='P0',equipment_type='ball_valve')]
        good,_=discover(g,p,2,c);self.assertEqual(len(good),1)
        with self.assertRaisesRegex(ValueError,'primitive source replay'):prove(good[0],g,docs,p,h,{},c,[0,45,135],None)

    def test_plan_schema_contact_audit_reuses_WCS_and_preserves_component_metadata(self):
        from test_native_ball_contact_reapplication import fixture as ball_fixture
        for mirror,extrusion in[(1,(0,0,1)),(-1,(0,0,-1))]:
            doc,g,insert,line,row=ball_fixture(45,mirror,extrusion);row.update(edge_id='MAIN',source_handle=insert.dxf.handle);row.pop('source_top_handle')
            for edge in g['edges']:edge.pop('connection_mode')
            before=copy.deepcopy((g,row));result=native_component_profiles(doc,g,[row],['MAIN'],'plan')
            self.assertEqual(result['profiles']['MAIN'],{'ball_valve':1});self.assertEqual((g,row),before)
            self.assertIsNone(result['records'][0]['original_instance']['resistance'])
            doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            with self.assertRaises(ValueError):native_component_profiles(doc,g,[row],['MAIN'],'plan')

if __name__=='__main__':unittest.main()
