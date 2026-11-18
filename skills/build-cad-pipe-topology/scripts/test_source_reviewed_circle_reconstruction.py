import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import test_repair_confirmed_circle_junctions as fixtures
from repair_confirmed_circle_junctions import apply

class SourceReconstructionTests(unittest.TestCase):
 def fixture(self):
  f=fixtures.ConfirmedCircleTests();f.setUp();return f
 def test_branch_that_is_also_main_preserves_subbranches_in_both_orders(self):
  f=self.fixture();m=f.doc.modelspace();line=m.add_line((100,180),(320,180));circle=m.add_circle((400,180),80);h=circle.dxf.handle
  f.graph['nodes'] += [{'node_id':'EQ2','node_type':'equipment','system':'supply','x':100,'y':180,'floor':1},{'node_id':'U2','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'supply','x':320,'y':180,'floor':1}]
  f.graph['edges'].append({'edge_id':'BR2','start_node_id':'EQ2','end_node_id':'U2','system':'supply','path':[[100,180],[320,180]],'path_points':[[100,180],[320,180]],'attribute_paths':[[[100,180],[320,180]]],'path_length':220,'source_handles':[line.dxf.handle],'equipment_names':[],'equipment_counts':{}})
  row=copy.deepcopy(f.screen['candidates'][0]);row.update(circle_handle=h,main_graph_edges=['BR'],branch_graph_edges=['BR2'],rim_virtual_nodes=['U2'],main_handle=f.graph['edges'][1]['source_handles'][0],branch_handle=line.dxf.handle,center=[400,180],branch_rim=[320,180])
  f.screen['candidates'].append(row);summaries=[]
  for selected in ([f.circle,h],[h,f.circle]):
   policy=dict(f.policy,circle_handles=selected);g,rows,audit=apply(f.doc,f.graph,f.rows,f.screen,policy,'s','g','screen')
   for circle_id in selected:
    tee='T-USER-'+circle_id
    self.assertEqual(sum(tee in (e['start_node_id'],e['end_node_id']) for e in g['edges']),3)
   self.assertEqual(sum(e['path_length'] for e in g['edges']),1440)
   self.assertEqual({r['device_name'] for r in rows},{'C1','C2'})
   summaries.append(sorted((e['edge_id'],e['start_node_id'],e['end_node_id'],e['attribute_paths']) for e in g['edges']))
  self.assertEqual(*summaries)
 def test_technical_review_does_not_fabricate_user_confirmation(self):
  f=self.fixture();layer='空调冷冻水供水'
  for e in f.doc.modelspace():e.dxf.layer=layer
  f.screen['graph_sha256']='g';c=f.screen['candidates'][0];c['circle_layer']=layer
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);image=root/'pair.png';image.write_bytes(b'reviewed')
   review=root/'review.json';review.write_text(json.dumps({'source_sha256':'s','review_kind':'technical_native_source_comparison','connections':[{'circle_handle':f.circle,'main_handle':c['main_handle'],'branch_handle':c['branch_handle'],'radius':80,'system':'supply','pair_image':str(image),'pair_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'disposition':'direct_same_system_circle_rim_contact'}]}),encoding='utf8')
   source_policy={'source_sha256':'s','review_manifest':str(review),'review_sha256':hashlib.sha256(review.read_bytes()).hexdigest()}
   policy=copy.deepcopy(f.policy);policy.pop('confirmation')
   prior={'records':[{'circle_handle':'previous'}],'source_comparison':{'human_accepted':False}}
   f.graph['sourceReviewedCircleJunctionRepair']=copy.deepcopy(prior)
   g,rows,audit=apply(f.doc,f.graph,f.rows,f.screen,policy,'s','g','screen',source_review_policy=source_policy)
   self.assertNotIn('userConfirmedCircleJunctionRepair',g)
   proof=g['sourceReviewedCircleJunctionRepair'];self.assertNotIn('confirmation',proof);self.assertFalse(proof['source_comparison']['human_accepted'])
   self.assertEqual(proof['previous_repair'],prior)
   self.assertEqual(audit['records'][0]['tee'],'T-SOURCE-'+f.circle)
   f.doc.entitydb[c['branch_handle']].dxf.start=(400,300,10)
   with self.assertRaises(ValueError):apply(f.doc,f.graph,f.rows,f.screen,policy,'s','g','screen',source_review_policy=source_policy)
if __name__=='__main__':unittest.main()
