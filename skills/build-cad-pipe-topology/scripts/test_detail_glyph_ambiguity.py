import copy,unittest,ezdxf
from detail_glyph_ambiguity import analyze

def fixture():
 d=ezdxf.new();m=d.modelspace();nodes=[];edges=[];pairs=[]
 def add_glyph(id,x,change=False):
  hs=[m.add_circle((x,0),80,dxfattribs={'layer':'供水'}).dxf.handle]
  for i in range(4):hs.append(m.add_line((x+i,0),(x+i,1+(i==3 and change)),dxfattribs={'layer':'符号'}).dxf.handle)
  nodes.append({'node_id':id,'node_type':'virtual_equipment','subtype':'out_of_plane_interface','system':'supply','x':x,'y':0,'source_handles':hs})
 for i in range(2):
  add_glyph('U'+str(i),i*100);add_glyph('D'+str(i),1000+i*100)
  nodes.extend([{'node_id':'UT'+str(i)},{'node_id':'T'+str(i)}]);edges.extend([{'edge_id':'UE'+str(i),'system':'supply','start_node_id':'U'+str(i),'end_node_id':'UT'+str(i),'source_handles':['UP'+str(i)]},{'edge_id':'DE'+str(i),'system':'supply','start_node_id':'T'+str(i),'end_node_id':'D'+str(i),'source_handles':['DP'+str(i)]}]);pairs.append({'system':'supply','rank':i+1,'upper_edge':'UE'+str(i),'upper_terminal':'UT'+str(i),'upper_pipe':'UP'+str(i),'detail_tee':'T'+str(i),'detail_pipe':'DP'+str(i)})
 g={'metadata':{'source_sha256':'S'},'nodes':nodes,'edges':edges,'sourceDetailComparison':{'source_sha256':'S','pairs':pairs}}
 return d,g,{'source_sha256':'S','graph_sha256':'G'}
class DetailGlyphTest(unittest.TestCase):
 def test_indistinguishable_glyphs_do_not_confirm_mapping(self):
  d,g,p=fixture();old=copy.deepcopy(g);r=analyze(d,g,p,'S','G');self.assertEqual(g,old);self.assertEqual(r['summary'],{'individual_mapping_ambiguous':2});self.assertEqual(r['rows'][0]['same_signature_detail_ranks'],[1,2])
 def test_broken_glyph_and_stale_source_fail_closed(self):
  d,g,p=fixture();g['nodes'][0]['source_handles'].pop()
  with self.assertRaisesRegex(ValueError,'glyph'):analyze(d,g,p,'S','G')
  d,g,p=fixture()
  with self.assertRaisesRegex(ValueError,'identity'):analyze(d,g,p,'other','G')
 def test_wrong_system_is_not_an_alternative(self):
  d,g,p=fixture();g['edges'][2]['system']='return'
  with self.assertRaisesRegex(ValueError,'candidate mismatch'):analyze(d,g,p,'S','G')
if __name__=='__main__':unittest.main()
