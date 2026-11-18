import copy,unittest
import ezdxf
from source_tangent_circle_candidates import attach

def fixture():
 d=ezdxf.new('R2010');m=d.modelspace();s=m.add_circle((0,0),10,dxfattribs={'layer':'S'});r=m.add_circle((0,20),10,dxfattribs={'layer':'R'});sl=m.add_line((-20,0),(0,0),dxfattribs={'layer':'S'});rl=m.add_line((-20,20),(0,20),dxfattribs={'layer':'R'})
 def node(id,sys,y):return {'node_id':id,'node_type':'virtual_equipment','boundary_type':'unresolved_source_terminal','floor':'F2','system':sys,'x':0,'y':y,'ports':[{'port_id':id+'-P','system':sys}]}
 ns=[node('S','supply',0),node('R','return',20),{'node_id':'A','node_type':'tee'},{'node_id':'B','node_type':'tee'}]
 edges=[{'edge_id':'ES','system':'supply','start_node_id':'A','end_node_id':'S','source_handles':[sl.dxf.handle]},{'edge_id':'ER','system':'return','start_node_id':'B','end_node_id':'R','source_handles':[rl.dxf.handle]}]
 def side(id,sys,c,l,y):return {'node_id':id,'edge_id':'E'+id,'system':sys,'circle':c.dxf.handle,'center':[0,y],'line_hits_at_center':[{'handle':l.dxf.handle,'center_location':'endpoint'}]}
 g={'metadata':{'source_sha256':'src','hil_ready':True},'nodes':ns,'edges':edges};e={'source_sha256':'src','graph_sha256':'graph','summary':{'pairs':1},'records':[{'supply':side('S','supply',s,sl,0),'return':side('R','return',r,rl,20),'circle_tangent_distance':20}]}
 return d,g,e

class TangentTests(unittest.TestCase):
 def test_shape_recorded_without_connection(self):
  d,g,e=fixture();before=copy.deepcopy(g);out,a=attach(g,e,d,'src','graph');self.assertEqual(g,before);self.assertEqual(out['edges'],g['edges']);self.assertEqual(out['nodes'][0]['ports'],g['nodes'][0]['ports']);self.assertEqual(a['physical_connections_added'],0);self.assertEqual(len(out['sourceTerminalGlyphs']),2);self.assertFalse(out['metadata']['hil_ready'])
 def test_stale_or_wrong_system_rejected(self):
  d,g,e=fixture()
  with self.assertRaises(ValueError):attach(g,e,d,'src','wrong')
  g['edges'][0]['system']='return'
  with self.assertRaises(ValueError):attach(g,e,d,'src','graph')
 def test_not_tangent_or_shared_glyph_rejected(self):
  d,g,e=fixture();d.entitydb[e['records'][0]['return']['circle']].dxf.radius=9
  with self.assertRaises(ValueError):attach(g,e,d,'src','graph')
  d,g,e=fixture();g['nodes'][0]['source_terminal_glyph_ids']=['existing']
  with self.assertRaises(ValueError):attach(g,e,d,'src','graph')
 def test_conflicting_line_witness_rejected(self):
  d,g,e=fixture();e['records'][0]['supply']['line_hits_at_center']*=2
  with self.assertRaises(ValueError):attach(g,e,d,'src','graph')
  d,g,e=fixture();d.modelspace().add_line((0,-10),(0,10),dxfattribs={'layer':'R'})
  with self.assertRaisesRegex(ValueError,'Competing native line'):attach(g,e,d,'src','graph')

if __name__=='__main__':unittest.main()
