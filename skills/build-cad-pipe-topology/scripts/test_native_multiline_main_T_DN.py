import copy,unittest
import ezdxf
from native_multiline_main_T_DN import collect,source_path_chain
from axis_unbranched_vertical_DN import native_items,source_key
from native_line_path_evidence import LAYERS

def scene():
    doc=ezdxf.new('R2013');m=doc.modelspace();layer=LAYERS['supply'];sh='a'*64;gh='b'*64
    paths={'L':[[-400,50],[-250,50],[-200,0],[0,0]],'R':[[0,0],[200,0]],'B':[[0,0],[0,-50],[30,-80],[30,-200]]};source={}
    for eid,p in paths.items():
        for i,(a,b)in enumerate(zip(p,p[1:])):source[eid,i]=m.add_line(a,b,dxfattribs={'layer':layer})
    m.add_text('DN300',dxfattribs={'insert':(-350,60),'height':10,'rotation':0})
    nodes=[dict(node_id=n,node_type='physical_junction'if n=='T'else'virtual_equipment',x=p[0],y=p[1])for n,p in [('T',[0,0]),('L',[-400,50]),('R',[200,0]),('V',[30,-200])]]
    edges=[dict(edge_id=eid,system='supply',start_node_id=a,end_node_id=b,source_insert_handle=None,attribute_paths=[paths[eid]])for eid,a,b in [('L','L','T'),('R','T','R'),('B','T','V')]];g=dict(metadata=dict(source_sha256=sh),nodes=nodes,edges=edges);rows=[]
    for edge in edges:
        for i,(a,b)in enumerate(zip(edge['attribute_paths'][0],edge['attribute_paths'][0][1:])):rows.append(dict(edge_id=edge['edge_id'],path_index=0,segment_index=i,scope_points=[a,b],system='supply',direction_class='vertical'if abs(a[0]-b[0])<.05 else'horizontal',floor_start=1,floor_end=1,native_source_status='single_source_line_covers',native_witnesses=[dict(scope='modelspace',source_handle=source[edge['edge_id'],i].dxf.handle)]))
    route=dict(inputs=dict(source=dict(sha256=sh),graph=dict(sha256=gh)),records=rows);parent=dict(counts=dict(current_known=0),pending=[dict(edge_id='B',path_index=0,segment_index=i,original_reason='no_qualified_axis_annotation_on_this_vertical_segment')for i in(0,2)]);return doc,g,route,parent,sh,gh
def run(a):doc,g,route,parent,sh,gh=a;return collect(doc,g,route,parent,native_items(doc,g),sh,gh)

class MultilineMainTests(unittest.TestCase):
    def test_unqualified_caption_on_other_root_main_arm_blocks(self):
        for text in('DN300/DN200','DN200'):
            a=scene();m=a[0].modelspace();m.add_text(text,dxfattribs={'insert':(120,10),'height':10,'rotation':0})
            if text=='DN200':m.add_line((50,20),(180,20),dxfattribs={'layer':LAYERS['supply']})
            self.assertFalse(run(a)['records'])
    def split_main_scene(self):
        a=list(scene());doc,g,route,parent,sh,gh=a;m=doc.modelspace();source=next(l for l in m.query('LINE')if list(l.dxf.start)[:2]==[-200.,0.]);g['nodes'] += [dict(node_id='Q',node_type='physical_junction',x=-100,y=0),dict(node_id='S',node_type='virtual_equipment',x=-100,y=100)]
        left=g['edges'][0];left.update(start_node_id='Q',attribute_paths=[[[-100,0],[0,0]]]);extra=m.add_line((-100,0),(-100,100),dxfattribs={'layer':LAYERS['supply']});g['edges'] += [dict(edge_id='REMOTE',system='supply',start_node_id='L',end_node_id='Q',source_insert_handle=None,attribute_paths=[[[-400,50],[-250,50],[-200,0],[-100,0]]]),dict(edge_id='SIDE',system='supply',start_node_id='Q',end_node_id='S',source_insert_handle=None,attribute_paths=[[[-100,0],[-100,100]]])]
        original=[copy.deepcopy(s)for s in route['records']if s['edge_id']=='L'];route['records']=[s for s in route['records']if s['edge_id']!='L'];template=copy.deepcopy(original[-1]);template.update(segment_index=0,scope_points=[[-100,0],[0,0]]);route['records'].append(template)
        for s in original:s['edge_id']='REMOTE'
        original[-1]['scope_points']=[[-200,0],[-100,0]];route['records']+=original;template=copy.deepcopy(template);template.update(edge_id='SIDE',scope_points=[[-100,0],[-100,100]],direction_class='vertical',native_witnesses=[dict(scope='modelspace',source_handle=extra.dxf.handle)]);route['records'].append(template);parent['counts']['current_known']=1;return a
    def test_intermediate_T_follows_only_through_arm(self):
        a=self.split_main_scene();r=run(a);self.assertEqual(r['counts']['new_known'],2);self.assertTrue(any(len(c['junctions'])==2 for row in r['records']for c in row['candidate_evidence']))
        a=self.split_main_scene();a[0].modelspace().delete_entity(list(a[0].modelspace().query('TEXT'))[0]);a[0].modelspace().add_text('DN80',dxfattribs={'insert':(-90,50),'height':10,'rotation':90});self.assertFalse(run(a)['records'])
    def test_caption_around_original_main_bends_reaches_branch(self):
        a=scene();before=copy.deepcopy(a[1:]);r=run(a);self.assertEqual(r['counts']['new_known'],2);self.assertEqual({x['nominal_mm']for x in r['records']},{300});self.assertEqual(a[1:],before)
        for row in r['records']:self.assertIsNone(row['physical_length_mm']);self.assertFalse(row['whole_edge_DN_assigned']);self.assertEqual(row['candidate_evidence'][0]['branch']['actual_native_source_root'],None)
    def test_omission_glyph_handle_does_not_select_pipe_root(self):
        a=scene();edge=a[1]['edges'][-1];edge['source_insert_handle']='glyph-only';nodes={n['node_id']:n for n in a[1]['nodes']};rows={source_key(s):s for s in a[2]['records']};native= native_items(a[0],dict(a[1],edges=[dict(e,source_insert_handle=None)for e in a[1]['edges']]))
        scopes,proof=source_path_chain(edge,'T',nodes,rows,native,rows['B',0,2]);self.assertIsNone(proof['actual_native_source_root']);self.assertEqual(len(scopes),3)
    def test_downstream_new_or_compound_caption_blocks_whole_branch(self):
        for text in('DN80','DN300/DN200'):
            a=scene();a[0].modelspace().add_text(text,dxfattribs={'insert':(40,-150),'height':10,'rotation':90});self.assertFalse(run(a)['records'])
    def test_source_Z_extra_branch_and_duplicate_geometry_block(self):
        for kind in('Z','branch','duplicate'):
            a=scene();m=a[0].modelspace()
            if kind=='Z':
                for l in list(m.query('LINE'))[-3:]:l.dxf.start=(l.dxf.start.x,l.dxf.start.y,10);l.dxf.end=(l.dxf.end.x,l.dxf.end.y,10)
            elif kind=='branch':m.add_line((-200,0),(-200,-50),dxfattribs={'layer':LAYERS['supply']})
            else:m.add_line((-200,0),(0,0),dxfattribs={'layer':LAYERS['supply']})
            self.assertFalse(run(a)['records'])
    def test_branch_caption_never_seeds_parent_main(self):
        a=scene();a[0].modelspace().delete_entity(list(a[0].modelspace().query('TEXT'))[0]);a[0].modelspace().add_text('DN80',dxfattribs={'insert':(40,-150),'height':10,'rotation':90});self.assertFalse(run(a)['records'])
    def test_opposite_system_crossing_does_not_join(self):
        a=scene();a[0].modelspace().add_line((-200,-50),(-200,50),dxfattribs={'layer':LAYERS['return']});self.assertEqual(run(a)['counts']['new_known'],2)
    def test_unknown_scope_and_changed_route_rejected(self):
        a=scene();a[2]['records'][-1]['native_source_status']='no_witness';r=run(a);self.assertEqual(r['counts']['new_known'],1);a=scene();a[2]['inputs']['source']['sha256']='changed'
        with self.assertRaises(ValueError):run(a)
    def test_conflicting_main_seed_directions_do_not_pick_nearest(self):
        a=scene();a[0].modelspace().add_text('DN200',dxfattribs={'insert':(120,10),'height':10,'rotation':0});self.assertFalse(run(a)['records'])

if __name__=='__main__':unittest.main()
