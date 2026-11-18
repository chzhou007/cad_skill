import copy,hashlib,json,math,tempfile,unittest
from pathlib import Path
import ezdxf
from source_reviewed_circle_connections import candidate,load_review
from expert_circle_source_lengths import correct_circle_branch_lengths

class ReviewedCircleTests(unittest.TestCase):
 def setUp(self):
  self.doc=ezdxf.new();m=self.doc.modelspace()
  c=m.add_circle((0,0),80);a=m.add_line((-500,0),(500,0));b=m.add_line((0,500),(0,80))
  self.c={'handle':c.dxf.handle,'center':(0,0),'radius':80,'system':'return'}
  self.s=[{'handle':a.dxf.handle,'system':'return','a':(-500,0),'b':(500,0)},{'handle':b.dxf.handle,'system':'return','a':(0,500),'b':(0,80)}]
  self.row={'circle_handle':c.dxf.handle,'main_handle':a.dxf.handle,'branch_handle':b.dxf.handle,'system':'return','radius':80}
  self.review={c.dxf.handle:self.row}
 def test_source_scoped_contact(self):
  result=candidate(self.doc,self.c,self.s,self.review);self.assertEqual(result[0]['handle'],self.row['main_handle'])
  self.assertIsNone(candidate(self.doc,self.c,self.s,{}))
 def test_reviewed_symbol_layer_does_not_override_two_return_pipes(self):
  self.doc.entitydb[self.c['handle']].dxf.layer='空调冷冻水供水';self.c['system']='supply'
  for s in self.s:self.doc.entitydb[s['handle']].dxf.layer='空调冷冻水回水'
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
  self.row.update(system_evidence='both_native_pipe_layers',source_circle_layer='空调冷冻水供水')
  self.assertIsNotNone(candidate(self.doc,self.c,self.s,self.review))
  self.assertEqual(self.c['system'],'supply')
  self.doc.entitydb[self.row['branch_handle']].dxf.layer='空调冷冻水供水'
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
 def test_symbol_layer_review_retains_z_and_crossing_guards(self):
  self.doc.entitydb[self.c['handle']].dxf.layer='空调冷冻水供水';self.c['system']='supply'
  for s in self.s:self.doc.entitydb[s['handle']].dxf.layer='空调冷冻水回水'
  self.row.update(system_evidence='both_native_pipe_layers',source_circle_layer='空调冷冻水供水')
  self.doc.entitydb[self.row['branch_handle']].dxf.start=(0,500,7)
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
  self.doc.entitydb[self.row['branch_handle']].dxf.start=(0,500,0)
  self.s.append({'handle':'cross','system':'supply','a':(0,-100),'b':(0,100)})
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
 def test_rotated_mirrored_and_reversed_lines(self):
  for angle in (0,37,90,180,270):
   for mirror in (False,True):
    self.setUp();theta=math.radians(angle)
    def tf(p):
     x,y=p;x=-x if mirror else x
     return (x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta))
    for s in self.s:
     s['a'],s['b']=tf(s['b']),tf(s['a'])
     e=self.doc.entitydb[s['handle']];e.dxf.start=s['a'];e.dxf.end=s['b']
    self.assertIsNotNone(candidate(self.doc,self.c,self.s,self.review))
 def test_no_nearest_circle_substitution(self):
  c=dict(self.c,center=(100,0))
  with self.assertRaises(ValueError):candidate(self.doc,c,self.s,self.review)
 def test_competing_branch_blocks(self):
  s=copy.deepcopy(self.s);s.append(dict(s[1],handle='extra',a=(0,-500),b=(0,-80)))
  with self.assertRaises(ValueError):candidate(self.doc,self.c,s,self.review)
 def test_other_system_crossing_blocks(self):
  s=copy.deepcopy(self.s);s.append({'handle':'cross','system':'supply','a':(0,-100),'b':(0,100)})
  with self.assertRaises(ValueError):candidate(self.doc,self.c,s,self.review)
 def test_interface_fragment_blocks(self):
  self.doc.modelspace().add_line((0,0),(52,114),dxfattribs={'layer':'空调立管、水平支管'})
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
 def test_z_and_ocs_conflicts_block(self):
  self.doc.entitydb[self.row['branch_handle']].dxf.start=(0,500,5)
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
  self.doc.entitydb[self.row['branch_handle']].dxf.start=(0,500,0)
  self.doc.entitydb[self.c['handle']].dxf.extrusion=(0,0,-1)
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review)
 def test_z_exception_requires_exact_user_confirmed_source_control(self):
  layer='空调冷冻水回水';self.doc.entitydb[self.c['handle']].dxf.layer=layer
  for s in self.s:self.doc.entitydb[s['handle']].dxf.layer=layer
  self.doc.entitydb[self.c['handle']].dxf.center=(0,0,2)
  self.doc.entitydb[self.row['branch_handle']].dxf.start=(0,500,7)
  self.doc.entitydb[self.row['branch_handle']].dxf.end=(0,80,5)
  m=self.doc.modelspace();rc=m.add_circle((1000,0,2),80,dxfattribs={'layer':layer});rm=m.add_line((500,0,0),(1500,0,0),dxfattribs={'layer':layer});rb=m.add_line((1000,500,7),(1000,80,5),dxfattribs={'layer':layer})
  self.row['confirmed_plan_control']={'circle_handle':rc.dxf.handle,'main_handle':rm.dxf.handle,'branch_handle':rb.dxf.handle}
  confirm={'confirmed_by':'user','answer':'yes'}
  control={'node_id':'T','x':1000,'y':0,'floor':3,'system':'return','user_confirmed_circle':{'circle_handle':rc.dxf.handle,'confirmation':confirm}}
  g={'metadata':{'source_sha256':'s'},'nodes':[control,{'node_id':'U','x':0,'y':80,'floor':3,'subtype':'unresolved_source_terminal'}],'edges':[{'edge_id':'L','system':'return','start_node_id':'T','end_node_id':'a','source_handles':[rm.dxf.handle]},{'edge_id':'R','system':'return','start_node_id':'T','end_node_id':'b','source_handles':[rm.dxf.handle]},{'edge_id':'B','system':'return','start_node_id':'T','end_node_id':'c','source_handles':[rb.dxf.handle]},{'edge_id':'CB','system':'return','start_node_id':'U','end_node_id':'v','source_handles':[self.row['branch_handle']]}],'userConfirmedCircleJunctionRepair':{'source_sha256':'s','confirmation':confirm,'records':[{'circle_handle':rc.dxf.handle,'tee':'T','system':'return','branch_edge':'B'}]}}
  self.assertIsNotNone(candidate(self.doc,self.c,self.s,self.review,graph=g))
  for mode in ('no_user','wrong_z','wrong_branch','wrong_service','wrong_node','wrong_floor','no_graph'):
   test=copy.deepcopy(g)
   if mode=='no_user':test['userConfirmedCircleJunctionRepair']['confirmation']['confirmed_by']='algorithm'
   elif mode=='wrong_z':rb.dxf.start=(1000,500,9)
   elif mode=='wrong_branch':test['edges'][2]['source_handles']=['wrong']
   elif mode=='wrong_service':test['edges'][1]['system']='supply'
   elif mode=='wrong_node':test['nodes'][0]['x']=1001
   elif mode=='wrong_floor':test['nodes'][1]['floor']=4
   elif mode=='no_graph':test=None
   with self.subTest(mode=mode),self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review,graph=test)
   rb.dxf.start=(1000,500,7)
  # A shorter branch can use only the explicitly scoped local-rim mode. Its
  # far end must remain a source-backed unknown boundary.
  actual=self.doc.entitydb[self.row['branch_handle']];actual.dxf.start=(0,400,7)
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review,graph=g)
  self.s[1]['a']=(0,400);self.row['plan_control_match']='same_rim_variable_unknown_remote'
  g['edges'][3].update(end_node_id=None,end_boundary_id='A')
  g['boundary_anchors']=[{'boundary_id':'A','x':0,'y':400,'system':'return','source_pipe_handle':self.row['branch_handle'],'connectivity_beyond_boundary':'unknown'}]
  self.assertIsNotNone(candidate(self.doc,self.c,self.s,self.review,graph=g))
  g['boundary_anchors'][0]['connectivity_beyond_boundary']='confirmed'
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review,graph=g)
  g['boundary_anchors']=[];g['edges'][3].pop('end_boundary_id');g['edges'][3]['end_node_id']='V'
  g['nodes'].append({'node_id':'V','x':0,'y':400,'floor':3,'system':'return','subtype':'unresolved_source_terminal'})
  self.assertIsNotNone(candidate(self.doc,self.c,self.s,self.review,graph=g))
  g['nodes'][-1]['floor']=4
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review,graph=g)
  g['nodes'][-1]['floor']=3
  self.doc.entitydb[self.c['handle']].dxf.center=(0,0,0)
  actual.dxf.start=(0,400,0);actual.dxf.end=(0,80,0)
  with self.assertRaises(ValueError):candidate(self.doc,self.c,self.s,self.review,graph=g)
 def test_source_radius_excluded_without_inventing_expert_confirmation(self):
  nodes=[{'node_id':'T','node_type':'tee','system':'return','x':0,'y':0}]
  edges=[{'edge_id':'E','system':'return','start_node_id':'U','end_node_id':'T','source_handles':['B'],'attribute_paths':[[[0,500],[0,0]]],'path_length':500}]
  bridge={'source_comparison':{'human_accepted':False},'semantic_endpoint':(0,0),'original_endpoint':(0,80),'branch_handle':'B','main_handle':'M','circle_handle':'C','system':'return'}
  correct_circle_branch_lengths(nodes,edges,[bridge]);self.assertEqual(edges[0]['path_length'],420)
  self.assertNotIn('expert_issue',edges[0]['source_circle_connection']);self.assertFalse(edges[0]['path_length_complete'])
 def test_review_hash_binding_and_duplicate_rejection(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);image=root/'pair.png';image.write_bytes(b'test-pair')
   row=dict(self.row,pair_image=str(image),pair_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),disposition='direct_same_system_circle_rim_contact')
   manifest=root/'review.json'
   def policy(rows):
    manifest.write_text(json.dumps({'source_sha256':'s','review_kind':'technical_native_source_comparison','connections':rows}),encoding='utf8')
    return {'source_sha256':'s','review_manifest':str(manifest),'review_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest()}
   p=policy([row]);self.assertEqual(len(load_review(p,'s')),1)
   with self.assertRaises(ValueError):load_review(p,'wrong')
   with self.assertRaises(ValueError):load_review(policy([row,row]),'s')
   p=policy([row]);image.write_bytes(b'changed')
   with self.assertRaises(ValueError):load_review(p,'s')
if __name__=='__main__':unittest.main()
