import copy,math,unittest
import ezdxf
from native_line_f_diameter_evidence import collect

class NativeLineFTests(unittest.TestCase):
    def fixture(self,angle=0,mirror=1,negative_ocs=False,reversed_stem=False):
        def p(x,y):
            a=math.radians(angle);return (mirror*x*math.cos(a)-y*math.sin(a),mirror*x*math.sin(a)+y*math.cos(a),0)
        doc=ezdxf.new();doc.layers.new('AN');s=doc.modelspace();stem=s.add_line(p(30,0) if reversed_stem else p(0,0),p(0,0) if reversed_stem else p(30,0),dxfattribs={'layer':'AN'})
        bars=[s.add_line(p(x,0),p(x,height),dxfattribs={'layer':'AN'}) for x,height in ((20,12),(30,10))];texts=[]
        for x,label in ((19,'DN80(2.900)'),(29,'DN100(2.900)')):
            t=s.add_text(label,dxfattribs={'layer':'AN','height':1,'extrusion':(0,0,-1) if negative_ocs else (0,0,1)})
            t.dxf.insert=t.ocs().from_wcs(p(x,2));direction=t.ocs().from_wcs(p(0,1));t.dxf.rotation=math.degrees(math.atan2(direction.y,direction.x));texts.append(t)
        edges=[]
        for x,system,layer in ((5,'supply','空调冷冻水供水'),(10,'return','空调冷冻水回水')):
            doc.layers.new(layer);line=s.add_line(p(x,-10),p(x,15),dxfattribs={'layer':layer});edges.append(dict(edge_id=system,system=system,source_handles=[line.dxf.handle],attribute_paths=[[list(p(x,-10))[:2],list(p(x,15))[:2]]]))
        spec=dict(stem_handle=stem.dxf.handle,bar_handles=[b.dxf.handle for b in reversed(bars)],text_handles=[t.dxf.handle for t in reversed(texts)])
        return doc,dict(edges=edges),spec

    def test_order_is_WCS_and_survives_rotation_mirror_negative_OCS_and_stroke_reversal(self):
        for angle,mirror,negative,reversed_stem in [(0,1,False,False),(90,1,False,True),(180,-1,True,False),(270,-1,True,True)]:
            doc,g,p=self.fixture(angle,mirror,negative,reversed_stem);old=copy.deepcopy(g);result=collect(doc,g,[p],'S','G');self.assertEqual(g,old)
            values={r['edge_id']:r['nominal_mm'] for r in result['frames'][0]['bindings']};self.assertEqual(values,{'supply':80,'return':100})
            self.assertFalse(result['pipe_systems_connected']);self.assertFalse(result['human_accepted'])
            self.assertTrue(all(not r['physical_length_from_parentheses'] for r in result['frames'][0]['bindings']))

    def test_duplicate_pipe_third_bar_competing_label_wrong_Z_and_missing_stroke_rejected(self):
        for mode in ('pipe','bar','label','Z','missing'):
            doc,g,p=self.fixture()
            if mode=='pipe':doc.modelspace().add_line((5,-10),(5,15),dxfattribs={'layer':'空调冷冻水供水'})
            if mode=='bar':doc.modelspace().add_line((25,0),(25,12),dxfattribs={'layer':'AN'})
            if mode=='label':doc.modelspace().add_text('DN65',dxfattribs={'layer':'AN','height':1,'rotation':90,'insert':(20.5,3)})
            if mode=='Z':doc.entitydb[p['bar_handles'][0]].dxf.end=(30,10,2)
            if mode=='missing':p['stem_handle']='MISSING'
            with self.assertRaises(ValueError):collect(doc,g,[p],'S','G')

    def test_F_attribute_contact_at_a_graph_T_is_not_an_arbitrary_edge_choice(self):
        doc,g,p=self.fixture();extra=copy.deepcopy(g['edges'][0]);extra['edge_id']='duplicate-owner';g['edges'].append(extra)
        with self.assertRaisesRegex(ValueError,'unique'):collect(doc,g,[p],'S','G')

if __name__=='__main__':unittest.main()
