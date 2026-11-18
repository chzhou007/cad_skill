import copy,math,unittest,os,subprocess,sys
import ezdxf
from plan_pipe_diameter_scopes import group_evidence,catalog,trim_frontier
from pipe_annotation_attributes import source_texts

class DiameterScopeTests(unittest.TestCase):
    def fixture(self,angle=0,mirror=1):
        def pt(x,y):
            a=math.radians(angle);return [mirror*x*math.cos(a)-y*math.sin(a),mirror*x*math.sin(a)+y*math.cos(a)]
        rotation=(angle+(180 if mirror<0 else 0))%360
        doc=ezdxf.new();doc.layers.new('AN');nodes=[];edges=[];branches=[];mains=[];seeds=[]
        for i in (1,2,3):
            xy=pt(i*10,10);nodes.append(dict(node_id='EQ'+str(i),node_type='equipment',floor=1,x=xy[0],y=xy[1]))
        for sys,layer,y,dn in [('supply','空调冷冻水供水',0,80),('return','空调冷冻水回水',20,100)]:
            doc.layers.new(layer);line=doc.modelspace().add_line(pt(0,y),pt(40,y),dxfattribs={'layer':layer})
            for x in (0,10,20,30,40):
                p=pt(x,y);nodes.append(dict(node_id=sys+str(x),node_type='tee' if x in (10,20,30) else 'virtual_equipment',floor=1,system=sys,x=p[0],y=p[1]))
            for i,(a,b) in enumerate([(0,10),(10,20),(20,30),(30,40)]):
                eid=sys+'M'+str(i);edges.append(dict(edge_id=eid,start_node_id=sys+str(a),end_node_id=sys+str(b),system=sys,attribute_paths=[[pt(a,y),pt(b,y)]],source_handles=[line.dxf.handle]))
                if i in (1,2):mains.append(eid)
            for i,x in enumerate((10,20,30),1):
                branch=doc.modelspace().add_line(pt(x,y),pt(x,y+5),dxfattribs={'layer':layer});eid=sys+'B'+str(i)
                edges.append(dict(edge_id=eid,start_node_id=sys+str(x),end_node_id='EQ'+str(i),system=sys,attribute_paths=[[pt(x,y),pt(x,y+5)]],source_handles=[branch.dxf.handle]))
                branches.append(dict(edge_id=eid,tee=sys+str(x),equipment_id='EQ'+str(i),system=sys))
            text=doc.modelspace().add_text('DN'+str(dn),dxfattribs={'layer':'AN','height':1,'rotation':rotation,'insert':pt(15,y+.6)})
            seeds.append(dict(text_handle=text.dxf.handle,expected_text=text.dxf.text,edge_id=sys+'M1',source_line_handle=line.dxf.handle))
        graph=dict(nodes=nodes,edges=edges,metadata=dict(source_sha256='S'))
        group=dict(group_id='G',floor=1,main_edges=mains,branches=branches,seeds=seeds)
        return doc,graph,group

    def run_group(self,doc,graph,group):return group_evidence(doc,graph,group,source_texts(doc,'test','S'),'S','G',set())

    def test_through_inheritance_rotations_mirrors_and_system_separation(self):
        for angle,mirror in [(0,1),(90,1),(180,-1),(270,-1)]:
            doc,g,p=self.fixture(angle,mirror);before=copy.deepcopy(g);result=self.run_group(doc,g,p)
            self.assertEqual(g,before);self.assertEqual(len(result['records']),10)
            self.assertEqual({r['nominal_mm'] for r in result['records'] if r['system']=='supply'},{80})
            self.assertEqual({r['nominal_mm'] for r in result['records'] if r['system']=='return'},{100})
            self.assertFalse(result['human_accepted']);self.assertFalse(result['outside_frontiers_traversed'])

    def test_independent_process_hash_seeds_preserve_frontier_receipt_and_projection_hash(self):
        code="from test_plan_pipe_diameter_scopes import DiameterScopeTests; from confirm_crossview_paths import encode; import hashlib; t=DiameterScopeTests(); print(hashlib.sha256(encode(t.run_group(*t.fixture()))).hexdigest())"
        values=[subprocess.check_output([sys.executable,'-X','utf8','-c',code],env=dict(os.environ,PYTHONHASHSEED=str(seed)),text=True).strip() for seed in (1,2,3)]
        self.assertEqual(len(set(values)),1)

    def test_branch_explicit_DN_does_not_override_through_main(self):
        doc,g,p=self.fixture();doc.modelspace().add_text('DN65',dxfattribs={'layer':'AN','height':.3,'rotation':90,'insert':(20.4,1.5)})
        records={r['edge_id']:r for r in self.run_group(doc,g,p)['records']}
        self.assertEqual(records['supplyB2']['nominal_mm'],65);self.assertEqual(records['supplyB2']['status'],'direct_branch_DN_override')
        self.assertEqual(records['supplyM1']['nominal_mm'],80);self.assertEqual(records['supplyM2']['nominal_mm'],80);self.assertEqual(records['supplyB1']['nominal_mm'],80)

    def test_two_main_DNs_expose_ambiguous_T_inheritance_instead_of_guessing(self):
        doc,g,p=self.fixture();doc.modelspace().add_text('DN125',dxfattribs={'layer':'AN','height':1,'rotation':0,'insert':(25,.6)})
        records={r['edge_id']:r for r in self.run_group(doc,g,p)['records']}
        self.assertEqual(records['supplyM1']['nominal_mm'],80);self.assertEqual(records['supplyM2']['nominal_mm'],125)
        self.assertIsNone(records['supplyB2']['nominal_mm']);self.assertEqual(records['supplyB3']['nominal_mm'],125)

    def test_bent_feeder_seed_is_a_read_only_fragment_not_a_whole_feeder_value(self):
        doc,g,p=self.fixture();edge=next(e for e in g['edges'] if e['edge_id']=='supplyM0')
        line=doc.modelspace().add_line((0,-10),(0,0),dxfattribs={'layer':'空调冷冻水供水'});edge['attribute_paths']=[[[0,-10],[0,0],[10,0]]];edge['source_handles'].append(line.dxf.handle)
        next(n for n in g['nodes'] if n['node_id']=='supply0')['y']=-10
        text=doc.entitydb[p['seeds'][0]['text_handle']];text.dxf.insert=(-.6,-5);text.dxf.rotation=90
        p['seeds'][0].update(edge_id='supplyM0',source_line_handle=line.dxf.handle)
        before=copy.deepcopy(g);result=self.run_group(doc,g,p);self.assertEqual(g,before)
        self.assertNotIn('supplyM0',{r['edge_id'] for r in result['records']});self.assertEqual({r['nominal_mm'] for r in result['records'] if r['system']=='supply'},{80})
        proof=next(f for f in result['frontier_fragments'] if f['edge_id']=='supplyM0');self.assertEqual(proof['projected_source_path'],[[10,0],[0,0],[0.,-5.]])
        self.assertFalse(proof['whole_original_edge_value_assigned'])

    def test_ordinary_crossing_four_way_pending_T_compound_and_stale_seed_rejected(self):
        for variant in ('fourway','pending','compound','source','duplicate','F'):
            doc,g,p=self.fixture()
            if variant=='fourway':extra=copy.deepcopy(g['edges'][1]);extra['edge_id']='EXTRA';g['edges'].append(extra)
            if variant=='pending':next(n for n in g['nodes'] if n['node_id']=='supply20')['review_required']=True
            if variant=='compound':doc.modelspace().add_text('DN80/DN65',dxfattribs={'layer':'AN','height':1,'insert':(17,.6)})
            if variant=='source':p['seeds'][0]['expected_text']='DN999'
            if variant=='duplicate':doc.modelspace().add_line((0,0),(40,0),dxfattribs={'layer':'空调冷冻水供水'})
            if variant=='F':
                with self.assertRaises(ValueError):group_evidence(doc,g,p,source_texts(doc,'test','S'),'S','G',{p['seeds'][0]['text_handle']})
                continue
            with self.assertRaises(ValueError):self.run_group(doc,g,p)

    def test_frontier_cannot_cross_an_unproved_drawing_gap(self):
        _,g,_=self.fixture();edge=next(e for e in g['edges'] if e['edge_id']=='supplyM0');edge['attribute_paths']=[[[0,0],[4,0]],[[7,0],[10,0]]]
        with self.assertRaisesRegex(ValueError,'gap'):trim_frontier(g,edge,'supply10',[2,0])

    def test_unbound_near_label_and_far_leader_cannot_be_silently_inherited_over(self):
        for mode in ('near','leader'):
            doc,g,p=self.fixture()
            if mode=='near':doc.modelspace().add_text('DN65',dxfattribs={'layer':'AN','height':.3,'rotation':90,'insert':(20.8,1.5)})
            else:
                doc.modelspace().add_text('DN65',dxfattribs={'layer':'AN','height':.3,'rotation':0,'insert':(50,5.5)})
                doc.modelspace().add_line((20,5),(50,5),dxfattribs={'layer':'AN'})
            with self.assertRaises(ValueError):self.run_group(doc,g,p)

if __name__=='__main__':unittest.main()
