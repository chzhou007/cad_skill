import copy,unittest
from unittest.mock import patch
from native_modelspace_paired_main_seeds import seeds,collect,reader
from axis_unbranched_vertical_DN import native_items
from native_line_path_evidence import LAYERS
from test_native_paired_caption_geometry import fixture
from test_native_multiline_main_T_DN import scene

def paired_scene(angle=0):
    doc,s,r,t1,t2,p=fixture(angle);m=doc.modelspace();t1.dxf.text='DN80(7.000)';t2.dxf.text='DN250(8.000)';sh='a'*64;gh='b'*64
    coords={'S0':p(0,0),'T':p(5000,0),'S1':p(8000,0),'B':p(5000,-2000),'R0':p(0,400),'R1':p(8000,400)};m.add_line(coords['T'],coords['B'],dxfattribs={'layer':LAYERS['supply']});branch=list(m.query('LINE'))[-1]
    nodes=[dict(node_id=n,node_type='physical_junction'if n=='T'else'virtual_equipment',x=q[0],y=q[1])for n,q in coords.items()];edges=[];rows=[]
    for eid,a,b,source,system in [('SL','S0','T',s,'supply'),('SR','T','S1',s,'supply'),('B','T','B',branch,'supply'),('R','R0','R1',r,'return')]:
        points=[list(coords[a]),list(coords[b])];edges.append(dict(edge_id=eid,start_node_id=a,end_node_id=b,system=system,source_insert_handle=None,attribute_paths=[points]));rows.append(dict(edge_id=eid,path_index=0,segment_index=0,scope_points=points,system=system,direction_class='vertical'if abs(points[0][0]-points[1][0])<.05 else'horizontal',floor_start=1,floor_end=1,native_source_status='single_source_line_covers',native_witnesses=[dict(scope='modelspace',source_handle=source.dxf.handle)]))
    graph=dict(metadata=dict(source_sha256=sh),nodes=nodes,edges=edges);route=dict(inputs=dict(source=dict(sha256=sh),graph=dict(sha256=gh)),records=rows);parent=dict(counts=dict(current_known=sum(v['direction_class']=='vertical'for v in rows)-1),pending=[dict(edge_id='B',path_index=0,segment_index=0,original_reason='no_qualified_axis_annotation_on_this_vertical_segment')]);return doc,graph,route,parent,sh,gh
def run(a):d,g,r,p,sh,gh=a;return collect(d,g,r,p,native_items(d,g),sh,gh)

class PairMainSeedTests(unittest.TestCase):
    def test_mixed_edge_keeps_horizontal_and_vertical_diameter_domains_separate(self):
        a=list(paired_scene());d,g,route,parent,sh,gh=a;m=d.modelspace();list(m.query('TEXT'))[0].dxf.text='DN300(7.000)';nodes={n['node_id']:n for n in g['nodes']};nodes['B'].update(node_type='physical_junction',x=7000,y=-2000);g['edges'][2]['attribute_paths'][0]=copy.deepcopy(g['edges'][2]['attribute_paths'][0]);g['edges'][2]['attribute_paths'][0].append([7000,-2000]);low=m.add_line((5000,-2000),(9000,-2000),dxfattribs={'layer':LAYERS['supply']});up=m.add_line((7000,-2000),(7000,-1000),dxfattribs={'layer':LAYERS['supply']});m.add_text('DN200',dxfattribs={'insert':(8000,-1980),'height':20,'layer':'DN'});g['nodes'] += [dict(node_id='C',node_type='virtual_equipment',x=9000,y=-2000),dict(node_id='U',node_type='virtual_equipment',x=7000,y=-1000)]
        for eid,start,end,points,source,index in [('B','T','B',[[5000,-2000],[7000,-2000]],low,1),('LOWER_R','B','C',[[7000,-2000],[9000,-2000]],low,0),('LOWER_U','B','U',[[7000,-2000],[7000,-1000]],up,0)]:
            if eid!='B':g['edges'].append(dict(edge_id=eid,start_node_id=start,end_node_id=end,system='supply',source_insert_handle=None,attribute_paths=[points]))
            route['records'].append(dict(edge_id=eid,path_index=0,segment_index=index,scope_points=points,system='supply',direction_class='vertical'if eid=='LOWER_U'else'horizontal',floor_start=1,floor_end=1,native_source_status='single_source_line_covers',native_witnesses=[dict(scope='modelspace',source_handle=source.dxf.handle)]))
        parent['counts']['current_known']+=1;result=run(a);self.assertEqual(result['records'][0]['nominal_mm'],300);horizontal=[s for s in result['seeds']['records']if(s['edge_id'],s['path_index'],s['segment_index'])==('B',0,1)];self.assertEqual({s['nominal_mm']for s in horizontal},{200});self.assertIsNone(result['records'][0]['physical_length_mm']);self.assertFalse(result['records'][0]['whole_edge_DN_assigned'])
    def test_old_geometric_pair_enters_original_T_reader(self):
        a=paired_scene();before=copy.deepcopy(a[1:]);r=run(a);self.assertEqual(r['counts']['new_known'],1);self.assertEqual(r['records'][0]['nominal_mm'],80);self.assertIsNone(r['records'][0]['physical_length_mm']);self.assertEqual(a[1:],before);self.assertTrue(r['source_local_seed_priority_applied'])
    def test_pair_geometry_is_value_independent_and_rotates(self):
        for angle in(0,90,180,270):
            d,g,r,p,sh,gh=paired_scene(angle);result=seeds(d,g,r,sh,gh);observed={(s['system'],s['nominal_mm'])for s in result['records']};self.assertIn(('supply',80),observed);self.assertIn(('return',250),observed)
    def test_duplicate_or_intervening_pipe_does_not_gain_pair_supply_seed(self):
        for kind in('third','duplicate'):
            a=paired_scene();d=a[0]
            if kind=='third':d.modelspace().add_line((0,200),(8000,200),dxfattribs={'layer':LAYERS['supply']})
            else:d.modelspace().add_entity(list(d.modelspace().query('LINE'))[0].copy())
            self.assertFalse(run(a)['records'])
    def test_new_branch_caption_source_Z_and_mirror_still_hold(self):
        for kind in('DN','Z','mirror'):
            a=paired_scene();d=a[0];m=d.modelspace()
            if kind=='DN':m.add_text('DN50',dxfattribs={'insert':(5010,-1500),'height':20,'rotation':90,'layer':'DN'})
            elif kind=='Z':
                branch=list(m.query('LINE'))[-1];branch.dxf.start=(5000,0,10);branch.dxf.end=(5000,-2000,10)
            else:list(m.query('TEXT'))[0].dxf.text_generation_flag=2
            self.assertFalse(run(a)['records'])
    def test_local_actual_LINE_caption_precedes_remote_bent_edge_caption(self):
        a=scene();m=a[0].modelspace();lines=list(m.query('LINE'));main=lines[2];other=lines[3];main.dxf.end=(200,0,0);m.delete_entity(other);a[2]['records'][3]['native_witnesses'][0]['source_handle']=main.dxf.handle;m.add_text('DN200',dxfattribs={'insert':(120,10),'height':10,'rotation':0});r=run(a);self.assertEqual(r['counts']['new_known'],2);self.assertEqual({s['nominal_mm']for s in r['records']},{200})
    def test_unowned_other_arm_caption_and_changed_upstream_seam_fail_closed(self):
        a=paired_scene();a[0].modelspace().add_text('DN300/DN200',dxfattribs={'insert':(7000,20),'height':20,'layer':'DN'});self.assertFalse(run(a)['records'])
        with patch('native_modelspace_paired_main_seeds.inspect.getsource',return_value='def collect():\n return []\n'):
            with self.assertRaisesRegex(ValueError,'seam changed'):reader()

if __name__=='__main__':unittest.main()
