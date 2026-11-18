import copy,unittest
import ezdxf
from native_line_path_evidence import LAYERS
from translated_inline_conflict_family import compare

class TranslatedConflictTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();self.doc.blocks.new('J');m=self.doc.modelspace();self.j1=m.add_blockref('J',(0,0));self.j2=m.add_blockref('J',(100,50))
  self.lines=[]
  for dx,dy in [(0,0),(100,50)]:
   self.lines.append([m.add_line((dx,dy),(dx+10,dy),dxfattribs={'layer':LAYERS['supply']}),m.add_line((dx+20,dy),(dx+30,dy),dxfattribs={'layer':LAYERS['return']})])
  def row(j,group,dx,dy):return {'joint_handle':j.dxf.handle,'assigned_edge_id':'E','assigned_system':'supply','witness_edge_ids':['E'],'classification':'unresolved','resolution':'unresolved','human_accepted':False,'contacts':[{'midpoint':[dx,dy,0],'lines':[{'source_handle':group[0].dxf.handle,'system':'supply'}]},{'midpoint':[dx+20,dy,0],'lines':[{'source_handle':group[1].dxf.handle,'system':'return'}]}]}
  self.t={'source_sha256':'s','graph_sha256':'g','status':'read_only_triage_not_repair','hil_ready':False,'records':[row(self.j1,self.lines[0],0,0),row(self.j2,self.lines[1],100,50)]};self.g={'edges':[{'edge_id':'E','system':'supply'}]};self.h={'source_sha256':'s','graph_sha256':'g','triage_sha256':'t'};self.p=dict(self.h,pairs=[[self.j1.dxf.handle,self.j2.dxf.handle]])
 def test_translated_family_stays_unresolved(self):
  before=copy.deepcopy(self.g);r=compare(self.doc,self.g,self.t,self.p,self.h);self.assertEqual(r['records'][0]['translation'],[100,50,0]);self.assertFalse(r['human_accepted']);self.assertFalse(r['hil_ready']);self.assertEqual(self.g,before)
 def test_wrong_layer_translation_or_review_rejected(self):
  self.lines[1][0].dxf.layer=LAYERS['return']
  with self.assertRaises(ValueError):compare(self.doc,self.g,self.t,self.p,self.h)
  self.lines[1][0].dxf.layer=LAYERS['supply'];self.lines[1][0].dxf.end=(111,50)
  with self.assertRaises(ValueError):compare(self.doc,self.g,self.t,self.p,self.h)
  self.lines[1][0].dxf.end=(110,50);self.t['records'][0]['human_accepted']=True
  with self.assertRaises(ValueError):compare(self.doc,self.g,self.t,self.p,self.h)
 def test_stale_graph_and_duplicate_pair_rejected(self):
  with self.assertRaises(ValueError):compare(self.doc,self.g,self.t,self.p,dict(self.h,graph_sha256='old'))
  self.p['pairs'].append(self.p['pairs'][0])
  with self.assertRaises(ValueError):compare(self.doc,self.g,self.t,self.p,self.h)
if __name__=='__main__':unittest.main()
