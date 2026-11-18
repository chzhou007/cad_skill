import unittest,copy,ezdxf
from source_terminal_pair_inventory import candidate_pairs,scan
class PairCandidateTest(unittest.TestCase):
 def test_rotated_and_mirrored_pairs_are_only_candidates(self):
  for x,y in [(300,0),(-300,0),(0,300),(0,-300),(180,240)]:
   ns=[{'node_id':'R','system':'return','x':0,'y':0},{'node_id':'S','system':'supply','x':x,'y':y}];p=candidate_pairs(ns,300,.05);self.assertEqual(len(p),1);self.assertEqual(p[0]['status'],'geometry_pair_not_a_connection');self.assertFalse(p[0]['terminal_pairing_ambiguous'])
 def test_competing_nearby_pair_is_not_hidden(self):
  ns=[{'node_id':'R','system':'return','x':0,'y':0},{'node_id':'S1','system':'supply','x':300,'y':0},{'node_id':'S2','system':'supply','x':0,'y':300}];p=candidate_pairs(ns,300,.05);self.assertEqual(len(p),2);self.assertTrue(all(x['terminal_pairing_ambiguous'] for x in p))
 def test_invalid_calibration_rejected(self):
  for x in (0,float('nan'),-1):
   with self.assertRaises(ValueError):candidate_pairs([],x,.05)

class SourcePairInventoryTest(unittest.TestCase):
 def fixture(self):
  d=ezdxf.new();m=d.modelspace();nodes=[];edges=[]
  glyph=[((0,0),(52.09458,114.14687)),((0,0),(114.14687,52.09458)),((34.72067,131.52078),(131.52078,34.72067)),((51.73687,148.53698),(148.53698,51.73687))]
  for system,x in [('return',0),('supply',300)]:
   circle=m.add_circle((x,0),80,dxfattribs={'layer':'空调冷冻水回水' if system=='return' else '空调冷冻水供水'});lines=[m.add_line((a[0]+x,a[1]),(b[0]+x,b[1]),dxfattribs={'layer':'空调立管、水平支管'}) for a,b in glyph];nodes.append({'node_id':system,'subtype':'out_of_plane_interface','system':system,'x':x,'y':0,'source_handle':circle.dxf.handle,'source_handles':[circle.dxf.handle]+[z.dxf.handle for z in lines]});edges.append({'edge_id':'E'+system,'start_node_id':system,'end_node_id':'end'+system})
  block=d.blocks.new('EQUIPMENT');block.add_lwpolyline([(0,0),(100,0),(100,100),(0,100)],close=True);ins=m.add_blockref('EQUIPMENT',(100,-200));nodes.append({'node_id':'device','node_type':'equipment','source_handle':ins.dxf.handle,'connection_status':'ports_unresolved'});return d,{'metadata':{'source_sha256':'S'},'nodes':nodes,'edges':edges},{'source_sha256':'S','graph_sha256':'G','pair_spacing':300,'pair_tolerance':.05,'body_search_radius':1000}
 def test_source_checked_pair_stays_unbound(self):
  d,g,p=self.fixture();before=copy.deepcopy(g);r=scan(d,g,p,'S','G');self.assertEqual(g,before);self.assertEqual(len(r['pairs']),1);self.assertEqual(r['equipment'][0]['pair_candidates'][0]['status'],'nearby_pair_not_bound');self.assertFalse(r['hil_ready'])
 def test_wrong_glyph_or_degree_is_rejected(self):
  d,g,p=self.fixture();g['nodes'][0]['source_handles'].pop()
  with self.assertRaisesRegex(ValueError,'terminal source'):scan(d,g,p,'S','G')
  d,g,p=self.fixture();g['edges'].append(dict(g['edges'][0],edge_id='other'))
  with self.assertRaisesRegex(ValueError,'degree'):scan(d,g,p,'S','G')
if __name__=='__main__':unittest.main()
