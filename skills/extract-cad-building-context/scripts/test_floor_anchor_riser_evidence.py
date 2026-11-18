import copy,unittest,ezdxf
from floor_anchor_riser_evidence import compare

def side(dx,dy,sha):
 d=ezdxf.new();block=d.blocks.new('BL');pts=[(0,0),(100,0),(0,100)];txts=[]
 for i,p in enumerate(pts):txts.append(block.add_text('锚点'+str(i),dxfattribs={'insert':p}))
 insert=d.modelspace().add_blockref('BL',(dx,dy));records=[{'source_chain':[insert.dxf.handle,t.dxf.handle],'source_text':t.plain_text(),'position':[t.dxf.insert.x+dx,t.dxf.insert.y+dy]} for t in txts]
 g={'metadata':{'source_sha256':sha},'nodes':[{'node_id':'R','subtype':'out_of_plane_riser','system':'supply','x':dx+10,'y':dy+20}]};shaft={'source_sha256':sha,'labels':[{'nearby_riser_candidates':[{'node_id':'R','system':'supply','xy':[dx+10,dy+20]}]}]};return d,{'source_sha256':sha,'records':records},g,shaft
class FloorAnchorEvidenceTest(unittest.TestCase):
 def setUp(self):
  self.a=side(0,0,'A');self.b=side(1000,2000,'B');self.policy={'minimum_triangle_area':1,'anchors':[{'a':{'chain':x['source_chain'],'text':x['source_text']},'b':{'chain':y['source_chain'],'text':y['source_text']}} for x,y in zip(self.a[1]['records'],self.b[1]['records'])]}
 def call(self):return compare(self.a[0],self.b[0],'A','B',self.a[1],self.b[1],self.a[2],self.b[2],self.a[3],self.b[3],self.policy)
 def test_aligned_is_only_candidate(self):
  r=self.call();self.assertEqual(r['translation'],[1000,2000]);self.assertEqual(r['same_system_riser_pairs'][0]['registration_residual_drawing_units'],0);self.assertFalse(r['hil_ready'])
 def test_mismatched_anchors_rejected(self):
  self.b[1]['records'][0]['position'][0]+=1
  with self.assertRaisesRegex(ValueError,'transform'):self.call()
  self.b=side(1000,2000,'B');self.policy['anchors'][0]['b']['text']='另一文字'
  with self.assertRaisesRegex(ValueError,'text mismatch'):self.call()
 def test_stale_riser_rejected(self):
  self.b[3]['labels'][0]['nearby_riser_candidates'][0]['xy'][0]+=1
  with self.assertRaisesRegex(ValueError,'riser candidate mismatch'):self.call()
 def test_collinear_rejected(self):
  self.policy['minimum_triangle_area']=6000
  with self.assertRaisesRegex(ValueError,'collinear'):self.call()
if __name__=='__main__':unittest.main()
