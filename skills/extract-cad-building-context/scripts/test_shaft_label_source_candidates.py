import copy,unittest,ezdxf
from shaft_label_source_candidates import scan

def fixture():
 d=ezdxf.new();b=d.blocks.new('LEVEL');t=b.add_text('空调管井',dxfattribs={'insert':(1,2)});i=d.modelspace().add_blockref('LEVEL',(10,20),dxfattribs={'rotation':90});p=i.matrix44().transform(t.dxf.insert)
 c={'source_sha256':'HASH','records':[{'source_text':'空调管井','source_chain':[i.dxf.handle,t.dxf.handle],'position':[p.x,p.y]}]};g={'metadata':{'source_sha256':'HASH'},'nodes':[{'node_id':'R','subtype':'out_of_plane_riser','system':'supply','x':p.x+3,'y':p.y+4,'source_handles':['C']},{'node_id':'T','subtype':'physical_tee','x':p.x,'y':p.y}]};return d,c,g
class ShaftTextEvidenceTest(unittest.TestCase):
 def test_nested_transform_and_no_mutation(self):
  d,c,g=fixture();before=copy.deepcopy((c,g));r=scan(d,'HASH',c,g,{'空调管井'},10);self.assertEqual((c,g),before);self.assertEqual(r['labels'][0]['nearby_riser_candidates'][0]['distance_drawing_units'],5);self.assertFalse(r['hil_ready'])
 def test_identity_chain_text_and_transform_rejected(self):
  d,c,g=fixture()
  with self.assertRaisesRegex(ValueError,'identity'):scan(d,'OTHER',c,g,{'空调管井'},10)
  c['records'][0]['position'][0]+=1
  with self.assertRaisesRegex(ValueError,'transform'):scan(d,'HASH',c,g,{'空调管井'},10)
  d,c,g=fixture();c['records'][0]['source_chain'][1]='BAD'
  with self.assertRaisesRegex(ValueError,'entities'):scan(d,'HASH',c,g,{'空调管井'},10)
 def test_radius_and_label_selection_are_only_candidates(self):
  d,c,g=fixture();self.assertEqual(scan(d,'HASH',c,g,{'暖通井'},10)['labels'],[]);self.assertEqual(scan(d,'HASH',c,g,{'空调管井'},4)['labels'][0]['nearby_riser_candidates'],[])
  with self.assertRaises(ValueError):scan(d,'HASH',c,g,{'空调管井'},0)
if __name__=='__main__':unittest.main()
