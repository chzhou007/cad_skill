import unittest,ezdxf
from compare_parallel_branch_motifs import compare
class MotifTest(unittest.TestCase):
 def setUp(self):
  self.d=ezdxf.new();m=self.d.modelspace();self.sm=m.add_line((0,0),(0,100),dxfattribs={'layer':'S'});self.rm=m.add_line((10,0),(10,100),dxfattribs={'layer':'R'});self.lines=[]
  for y,dx in [(20,0),(40,.5)]:self.lines.append((m.add_line((-10+dx,y),(dx,y),dxfattribs={'layer':'S'}),m.add_line((-10+dx,y-2),(10,y-2),dxfattribs={'layer':'R'})))
  self.g={'metadata':{'source_sha256':'S'},'nodes':[{'node_id':'T','node_type':'tee','system':'supply','x':0,'y':20}],'edges':[{'source_handles':[self.sm.dxf.handle,self.rm.dxf.handle]+[x.dxf.handle for pair in self.lines for x in pair]}]};self.p={'source_sha256':'S','graph_sha256':'G','system_layers':{'supply':'S','return':'R'},'graph_node_radius':1,'groups':[{'id':str(i),'supply_handle':s.dxf.handle,'return_handle':r.dxf.handle,'supply_main':self.sm.dxf.handle,'return_main':self.rm.dxf.handle} for i,(s,r) in enumerate(self.lines)]}
 def test_motif_is_evidence_not_connection(self):
  r=compare(self.d,self.g,self.p,'S','G');self.assertFalse(r['hil_ready']);self.assertAlmostEqual(r['groups'][1]['supply']['endpoint_to_main_distance'],.5);self.assertEqual(r['groups'][0]['supply']['nearby_graph_nodes'][0]['node_id'],'T')
 def test_stale_or_cross_system_fails(self):
  with self.assertRaises(ValueError):compare(self.d,self.g,self.p,'S','wrong')
  self.lines[0][0].dxf.layer='R'
  with self.assertRaises(ValueError):compare(self.d,self.g,self.p,'S','G')
if __name__=='__main__':unittest.main()
