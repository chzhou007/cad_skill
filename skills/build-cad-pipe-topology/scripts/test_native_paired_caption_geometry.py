import math,unittest
import ezdxf
from native_paired_caption_geometry import collect,leader_claims
from native_paired_end_labels import observe

def fixture(angle=0):
    d=ezdxf.new('R2013');m=d.modelspace();a=math.radians(angle)
    def p(x,y):return (x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a))
    s=m.add_line(p(0,0),p(8000,0),dxfattribs={'layer':'空调冷冻水供水'})
    r=m.add_line(p(0,400),p(8000,400),dxfattribs={'layer':'空调冷冻水回水'})
    m.add_line(p(0,-800),p(8000,-800),dxfattribs={'layer':'空调冷冻水回水'})
    t1=m.add_text('DN300(3.600)',dxfattribs={'insert':p(3000,-385),'height':350,'rotation':angle,'layer':'DN'})
    t2=m.add_text('DN300(3.600)',dxfattribs={'insert':p(3483,494),'height':350,'rotation':angle,'layer':'DN'})
    return d,s,r,t1,t2,p

class Tests(unittest.TestCase):
    def test_interior_pair_resolves_baseline_nearest_pipe_ambiguity_without_values(self):
        for angle in (0,90,180,270):
            d,s,r,t1,t2,p=fixture(angle);result=collect(d)
            self.assertEqual(len(result['pairs']),1)
            self.assertEqual([o['native_pipe']['source_LINE'] for o in result['pairs'][0]['observations']],[s.dxf.handle,r.dxf.handle])
            t1.dxf.text='DN80(7.00)';t2.dxf.text='DN250(8.00)'
            self.assertEqual([o['native_pipe']['source_LINE'] for o in collect(d)['pairs'][0]['observations']],[s.dxf.handle,r.dxf.handle])
    def test_third_pipe_duplicate_line_unsupported_text_or_profile_cannot_pass(self):
        for kind in ('third','duplicate','mirror','profile'):
            d,s,r,t1,t2,p=fixture()
            if kind=='third':d.modelspace().add_line((0,200),(8000,200),dxfattribs={'layer':'空调冷冻水供水'})
            if kind=='duplicate':d.modelspace().add_entity(s.copy())
            if kind=='mirror':t1.dxf.text_generation_flag=2
            if kind=='profile':t1.dxf.height=300
            self.assertEqual(collect(d)['pairs'],[],kind)
    def test_F_ownership_blocks_bare_fallback_with_three_crossings(self):
        d=ezdxf.new('R2013');m=d.modelspace()
        for a,b in [((1000,0),(1000,1200)),((1000,0),(1800,0)),((1000,400),(1800,400))]:m.add_line(a,b,dxfattribs={'layer':'DN'})
        for y,layer in ((600,'空调冷冻水供水'),(700,'空调冷冻水回水'),(1200,'空调冷冻水供水')):m.add_line((0,y),(1000,y),dxfattribs={'layer':layer})
        ts=[m.add_text(text,dxfattribs={'insert':(1100,y),'height':350,'layer':'DN'}) for text,y in (('DN80(3.00)',20),('DN100(4.00)',420))]
        claims=leader_claims(d,observe(d));self.assertEqual(set(claims),{t.dxf.handle for t in ts});self.assertEqual(collect(d)['pairs'],[])
        for t in ts:t.dxf.text='DN80'
        self.assertEqual(set(collect(d)['F_owned_texts']),{t.dxf.handle for t in ts})
    def test_inherited_end_column_still_qualifies_with_guard(self):
        from test_native_paired_end_labels import fixture as end
        d,s,r,*_=end();self.assertEqual(len(collect(d)['pairs']),1)

if __name__=='__main__':unittest.main()
