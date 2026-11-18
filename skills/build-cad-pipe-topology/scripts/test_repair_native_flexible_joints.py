import copy,unittest
import ezdxf
from repair_native_flexible_joints import fingerprint,repair

class NativeJointTests(unittest.TestCase):
 def setup_case(self,rotation=0,mirror=False):
  doc=ezdxf.new('R2010');b=doc.blocks.new('JOINT');b.add_point((-5,0));b.add_point((5,0));b.add_line((-5,-2),(-5,2));b.add_line((5,-2),(5,2));ins=doc.modelspace().add_blockref('JOINT',(100,200),dxfattribs={'rotation':rotation,'xscale':-1 if mirror else 1});pts=[p.dxf.location for p in ins.virtual_entities() if p.dxftype()=='POINT'];u,v=pts;axis=((v.x-u.x)/10,(v.y-u.y)/10)
  def node(n,p,typ,sub=''):return {'node_id':n,'node_type':typ,'subtype':sub,'floor':3,'x':p[0],'y':p[1]}
  A=(u.x-axis[0]*20,u.y-axis[1]*20);B=(v.x+axis[0]*20,v.y+axis[1]*20);U=(u.x,u.y);V=(v.x,v.y)
  nodes=[node('A',A,'equipment'),node('U',U,'virtual_equipment','unresolved_source_terminal'),node('V',V,'virtual_equipment','unresolved_source_terminal'),node('B',B,'tee')]
  def edge(id,a,b,p):return {'edge_id':id,'start_node_id':a,'end_node_id':b,'system':'supply','path':p,'path_points':p,'attribute_paths':[p],'source_handles':[id],'path_length':20,'equipment_names':[],'equipment_counts':{}}
  g={'nodes':nodes,'edges':[edge('E1','A','U',[A,U]),edge('E2','V','B',[V,B])],'metadata':{'other':'kept'}}
  p={'instance_handles':[ins.dxf.handle],'block_name':'JOINT','block_fingerprint_sha256':fingerprint(b),'contact_tolerance':.01,'angle_tolerance_degrees':1,'allowed_systems':['supply','return'],'device_id_prefix':'F-','expert_evidence':'test'}
  return doc,g,p
 def test_rotated_and_mirrored_joint(self):
  for angle,mirror in [(0,False),(90,False),(90,True),(180,True)]:
   with self.subTest(angle=angle,mirror=mirror):
    d,g,p=self.setup_case(angle,mirror);old=copy.deepcopy(g);new,devices,audit=repair(g,[],d,p)
    self.assertEqual(g,old);self.assertEqual((len(new['nodes']),len(new['edges']),len(devices)),(2,1,1));self.assertEqual(new['edges'][0]['path_length'],40);self.assertFalse(new['edges'][0]['path_length_complete']);self.assertEqual(len(new['edges'][0]['attribute_paths']),2);self.assertFalse(new['metadata']['hil_ready']);self.assertEqual(new['metadata']['other'],'kept')
 def test_technical_calibration_requires_unique_real_pipe_contacts(self):
  d,g,p=self.setup_case(90,True);d.blocks['JOINT'].add_spline(fit_points=[(-5,0),(0,1),(5,0)]);p['block_fingerprint_sha256']=fingerprint(d.blocks['JOINT']);p['confirmation_basis']='source_geometry_calibrated'
  for e in g['edges']:
   line=d.modelspace().add_line(e['path'][0],e['path'][-1],dxfattribs={'layer':'空调冷冻水供水'});e['source_handles']=[line.dxf.handle]
  out,rows,_=repair(g,[],d,p);edge=out['edges'][0];self.assertEqual(edge['connection_mode'],'source_geometry_calibrated_native_flexible_joint_unreviewed');self.assertEqual(edge['source_flexible_joints'][0]['confirmation_basis'],'source_geometry_calibrated');self.assertFalse(out['metadata']['hil_ready'])
  e=g['edges'][0];d.modelspace().add_line(e['path'][0],e['path'][-1],dxfattribs={'layer':'空调冷冻水供水'})
  with self.assertRaisesRegex(ValueError,'ambiguous'):repair(g,[],d,p)
 def test_multiple_source_calibrated_joints_on_same_run(self):
  d,g,p=self.setup_case();d.blocks['JOINT'].add_spline(fit_points=[(-5,0),(0,1),(5,0)]);second=d.modelspace().add_blockref('JOINT',(130,200));p.update(block_fingerprint_sha256=fingerprint(d.blocks['JOINT']),confirmation_basis='source_geometry_calibrated');p['instance_handles'].append(second.dxf.handle)
  g['nodes'][-1].update(node_type='virtual_equipment',subtype='unresolved_source_terminal');g['nodes'] += [{'node_id':'W','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','floor':3,'x':135,'y':200},{'node_id':'Z','node_type':'tee','floor':3,'x':155,'y':200}];g['edges'].append({'edge_id':'E3','start_node_id':'W','end_node_id':'Z','system':'supply','path':[[135,200],[155,200]],'path_points':[[135,200],[155,200]],'attribute_paths':[[[135,200],[155,200]]],'source_handles':['E3'],'path_length':20,'equipment_names':[],'equipment_counts':{}})
  for e in g['edges']:
   line=d.modelspace().add_line(e['path'][0],e['path'][-1],dxfattribs={'layer':'空调冷冻水供水'});e['source_handles']=[line.dxf.handle]
  result,rows,audit=repair(g,[],d,p);self.assertEqual((len(result['edges']),len(rows)),(1,2));self.assertEqual(len(result['edges'][0]['source_flexible_joints']),2);self.assertEqual(len({x['edge_id'] for x in rows}),1);self.assertEqual(len(audit['steps']),2)
 def test_technical_calibration_preserves_existing_repair_history(self):
  d,g,p=self.setup_case();p['confirmation_basis']='source_geometry_calibrated';g['expertFlexibleJointRepair']={'steps':[{'source_handle':'prior'}]}
  with self.assertRaisesRegex(ValueError,'history reconciliation'):repair(g,[],d,p)
 def test_rejects_wrong_fingerprint_and_duplicate(self):
  d,g,p=self.setup_case();q=copy.deepcopy(p);q['block_fingerprint_sha256']='bad'
  with self.assertRaises(ValueError):repair(g,[],d,q)
  q=copy.deepcopy(p);q['instance_handles']*=2
  with self.assertRaises(ValueError):repair(g,[],d,q)
 def test_rejects_mixed_service_and_floor(self):
  d,g,p=self.setup_case();g['edges'][1]['system']='return'
  with self.assertRaises(ValueError):repair(g,[],d,p)
  d,g,p=self.setup_case();g['nodes'][2]['floor']=4
  with self.assertRaises(ValueError):repair(g,[],d,p)
 def test_rejects_ambiguous_or_branched_endpoints(self):
  d,g,p=self.setup_case();n=copy.deepcopy(g['nodes'][1]);n['node_id']='duplicate';g['nodes'].append(n)
  with self.assertRaises(ValueError):repair(g,[],d,p)
  d,g,p=self.setup_case();e=copy.deepcopy(g['edges'][0]);e['edge_id']='E3';g['edges'].append(e)
  with self.assertRaises(ValueError):repair(g,[],d,p)
 def test_rejects_unaligned_rays(self):
  d,g,p=self.setup_case();g['edges'][0]['path_points'][0]=(95,175)
  with self.assertRaises(ValueError):repair(g,[],d,p)
 def test_merge_preserves_riser_evidence_on_retired_edge(self):
  d,g,p=self.setup_case();g['edges'][1]['source_riser_interfaces']=[{'circle_handle':'C2','physical_riser_length':'unknown'}]
  new,_,_=repair(g,[],d,p);e=new['edges'][0]
  self.assertEqual(e['source_riser_interfaces'],[{'circle_handle':'C2','physical_riser_length':'unknown'}])
  self.assertEqual(e['path_length_scope'],'source_drawn_pipe_only_flexible_joint_and_riser_lengths_unknown')
 def test_merge_preserves_expert_riser_connection_from_retired_edge(self):
  d,g,p=self.setup_case();g['edges'][1]['source_expert_riser_connections']=[{'circle_handle':'C2','physical_length':'unknown'}]
  new,_,_=repair(g,[],d,p);self.assertEqual(new['edges'][0]['source_expert_riser_connections'][0]['circle_handle'],'C2')
 def test_wave_glyph_retargets_retired_edge(self):
  d,g,p=self.setup_case();g['nodes'][0]['node_type']='virtual_equipment';g['sourceTerminalGlyphs']=[{'node_id':'A','edge_id':'E1','id':'W1'}]
  new,_,_=repair(g,[],d,p);glyph=new['sourceTerminalGlyphs'][0];self.assertEqual(glyph['edge_id'],new['edges'][0]['edge_id']);self.assertIn('A',(new['edges'][0]['start_node_id'],new['edges'][0]['end_node_id']))

if __name__=='__main__':unittest.main()
