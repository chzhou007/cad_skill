import copy,unittest
import ezdxf
from native_axis_main_T_DN import collect
from axis_unbranched_vertical_DN import native_items
from native_line_path_evidence import LAYERS

def scene():
    doc=ezdxf.new('R2013');m=doc.modelspace();layer=LAYERS['supply'];main=m.add_line((-200,0,0),(200,0,0),dxfattribs={'layer':layer});path=[[0,0],[0,-50],[30,-80],[30,-200]];children=[m.add_line(a,b,dxfattribs={'layer':layer})for a,b in zip(path,path[1:])];m.add_text('DN300',dxfattribs={'insert':(-150,10),'height':10,'rotation':0})
    sh='a'*64;gh='b'*64;nodes=[dict(node_id=n,node_type='physical_junction'if n=='T'else'virtual_equipment',x=p[0],y=p[1])for n,p in [('T',[0,0]),('L',[-200,0]),('R',[200,0]),('V',[30,-200])]]
    edges=[dict(edge_id='L',system='supply',start_node_id='L',end_node_id='T',source_insert_handle=None,attribute_paths=[[[-200,0],[0,0]]]),dict(edge_id='R',system='supply',start_node_id='T',end_node_id='R',source_insert_handle=None,attribute_paths=[[[0,0],[200,0]]]),dict(edge_id='B',system='supply',start_node_id='T',end_node_id='V',source_insert_handle=None,attribute_paths=[path])];g=dict(metadata=dict(source_sha256=sh),nodes=nodes,edges=edges);scopes=[]
    for edge in edges:
        for i,(a,b)in enumerate(zip(edge['attribute_paths'][0],edge['attribute_paths'][0][1:])):
            source=main if edge['edge_id']!='B'else children[i]
            scopes.append(dict(edge_id=edge['edge_id'],path_index=0,segment_index=i,scope_points=[a,b],system='supply',direction_class='vertical'if abs(a[0]-b[0])<.05 else'horizontal',floor_start=1,floor_end=1,native_source_status='single_source_line_covers',native_witnesses=[dict(scope='modelspace',source_handle=source.dxf.handle)]))
    route=dict(inputs=dict(source=dict(sha256=sh),graph=dict(sha256=gh)),records=scopes);prior=dict(counts=dict(current_known=0),pending=[dict(edge_id='B',path_index=0,segment_index=i,original_reason='no_qualified_axis_annotation_on_this_vertical_segment')for i in(0,2)])
    return doc,g,route,prior,sh,gh

def run(a):doc,g,route,prior,sh,gh=a;return collect(doc,g,route,prior,native_items(doc,g),sh,gh)

class MainTInheritanceTests(unittest.TestCase):
    def test_main_caption_reaches_unlabelled_branch_through_real_T_and_bends(self):
        a=scene();before=copy.deepcopy(a[1:]);r=run(a);self.assertEqual(r['counts']['new_known'],2);self.assertEqual(r['counts']['remaining_unknown'],0);self.assertEqual({x['nominal_mm']for x in r['records']},{300});self.assertEqual(a[1:],before)
        for row in r['records']:self.assertIsNone(row['physical_length_mm']);self.assertFalse(row['whole_edge_DN_assigned']);self.assertEqual(row['candidate_evidence'][0]['root_T']['junctions'][0]['node_id'],'T')

    def test_downstream_branch_label_blocks_inheritance_even_before_that_label(self):
        for text in('DN80','DN300/DN200'):
            a=scene();a[0].modelspace().add_text(text,dxfattribs={'insert':(40,-150),'height':10,'rotation':90});r=run(a);self.assertFalse(r['records']);self.assertEqual(len(r['pending']),2);self.assertTrue(any('in-scope DN'in f['reason']for d in r['diagnostics']for f in d['failures']))

    def test_label_on_another_omission_path_still_blocks_main_DN(self):
        a=list(scene());path=[[100,-300],[100,-400]];line=a[0].modelspace().add_line(*path,dxfattribs={'layer':LAYERS['supply']});a[1]['edges'][-1]['attribute_paths'].append(path);a[2]['records'].append(dict(edge_id='B',path_index=1,segment_index=0,scope_points=path,system='supply',direction_class='vertical',floor_start=1,floor_end=1,native_source_status='single_source_line_covers',native_witnesses=[dict(scope='modelspace',source_handle=line.dxf.handle)]));a[3]['counts']['current_known']=1;a[0].modelspace().add_text('DN80',dxfattribs={'insert':(110,-350),'height':10,'rotation':90});r=run(a);self.assertFalse(r['records'])

    def test_branch_caption_never_becomes_main_seed(self):
        a=scene();a[0].modelspace().delete_entity(list(a[0].modelspace().query('TEXT'))[0]);a[0].modelspace().add_text('DN80',dxfattribs={'insert':(40,-150),'height':10,'rotation':90});r=run(a);self.assertFalse(r['records']);self.assertTrue(r['branch_DN_never_used_as_main_seed'])

    def test_extra_same_system_source_ray_and_native_Z_disagreement_hold(self):
        for kind in('extra','Z'):
            a=scene()
            if kind=='extra':a[0].modelspace().add_line((0,0),(0,50),dxfattribs={'layer':LAYERS['supply']})
            else:
                for e in list(a[0].modelspace().query('LINE'))[1:]:e.dxf.start=(e.dxf.start.x,e.dxf.start.y,10);e.dxf.end=(e.dxf.end.x,e.dxf.end.y,10)
            self.assertFalse(run(a)['records'])

    def test_opposite_service_crossing_never_connects_or_changes_target_DN(self):
        a=scene();a[0].modelspace().add_line((0,0),(0,50),dxfattribs={'layer':LAYERS['return']});r=run(a);self.assertEqual(len(r['records']),2);self.assertTrue(all(x['system']=='supply'for x in r['records']))

    def test_unwitnessed_target_and_source_identity_change_are_rejected(self):
        a=scene();a[2]['records'][2]['native_source_status']='no_witness';self.assertFalse(run(a)['records']);a=scene();a[2]['inputs']['source']['sha256']='changed'
        with self.assertRaisesRegex(ValueError,'identities'):run(a)

if __name__=='__main__':unittest.main()
