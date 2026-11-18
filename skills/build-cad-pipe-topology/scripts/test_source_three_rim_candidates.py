import copy,unittest
from source_three_rim_candidates import identify,with_prior_floor
class ThreeRim(unittest.TestCase):
 def fixture(self):
  nodes=[];edges=[]
  for i,(x,y) in enumerate([(0,1),(1,0),(0,-1)]):
   nodes.extend([dict(node_id='U'+str(i),node_type='virtual_equipment',x=x,y=y,floor='F1'),dict(node_id='T'+str(i),node_type='tee',x=x*3,y=y*3,floor='F1')]);edges.append(dict(edge_id='E'+str(i),start_node_id='U'+str(i),end_node_id='T'+str(i),system='return',path_points=[[x,y],[x*3,y*3]]))
  return {'nodes':nodes,'edges':edges},[dict(handle='C',x=0,y=0,r=1,layer='R')],{e['edge_id']:['R']for e in edges}
 def test_source_candidate_has_three_rays_and_does_not_mutate_graph(self):
  g,c,l=self.fixture();before=copy.deepcopy(g);rows=identify(g,c,l);self.assertEqual(len(rows),1);self.assertEqual(len(rows[0]['contacts']),3);self.assertEqual(g,before);self.assertEqual(rows[0]['status'],'algorithm_candidate_not_connected')
 def test_cross_layer_contact_is_not_a_third_ray(self):
  g,c,l=self.fixture();l['E1']=['S'];self.assertEqual(identify(g,c,l),[])
 def test_conflicting_services_floors_or_explicit_destination_are_not_candidates(self):
  for mode in ('service','floor','destination'):
   g,c,l=self.fixture()
   if mode=='service':g['edges'][0]['system']='supply'
   elif mode=='floor':g['nodes'][0]['floor']='F2'
   else:g['nodes'][0]['interface_destination']={'text':'接至设备'}
   self.assertEqual(identify(g,c,l),[])
 def test_inward_path_does_not_qualify(self):
  g,c,l=self.fixture();g['edges'][0]['path_points']=[[0,1],[0,0]];self.assertEqual(identify(g,c,l),[])
 def test_rotated_and_mirrored_source_rays(self):
  import math
  for mirror in (-1,1):
   g,c,l=self.fixture();angle=.71
   def f(p):return [mirror*(p[0]*math.cos(angle)-p[1]*math.sin(angle))+4,p[0]*math.sin(angle)+p[1]*math.cos(angle)-3]
   for n in g['nodes']:n['x'],n['y']=f([n['x'],n['y']])
   for e in g['edges']:e['path_points']=[f(p)for p in e['path_points']]
   c[0]['x'],c[0]['y']=f([0,0]);self.assertEqual(len(identify(g,c,l)),1)
 def test_competing_same_layer_contact_prevents_grouping(self):
  g,c,l=self.fixture();g['nodes']+= [dict(node_id='X',node_type='virtual_equipment',x=0,y=1,floor='F1'),dict(node_id='Z',node_type='tee',x=0,y=4,floor='F1')];g['edges'].append(dict(edge_id='EX',start_node_id='X',end_node_id='Z',system='return',path_points=[[0,1],[0,4]]));l['EX']=['R'];self.assertEqual(identify(g,c,l),[])
 def test_mirrored_rotated_and_foreign_tangent_node(self):
  g,c,l=self.fixture();g['nodes'].append(dict(node_id='X',node_type='virtual_equipment',x=0,y=-1,floor='F1'));g['nodes'].append(dict(node_id='Z',node_type='tee',x=0,y=-3,floor='F1'));g['edges'].append(dict(edge_id='X1',start_node_id='X',end_node_id='Z',system='supply',path_points=[[0,-1],[0,-3]]));l['X1']=['S'];rows=identify(g,c,l);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['excluded_other_layer_nodes'],['X'])
 def test_native_document_source_layers_and_required_readability(self):
  import ezdxf
  from source_three_rim_candidates import identify_in_doc
  g,c,l=self.fixture();doc=ezdxf.new();m=doc.modelspace();m.add_circle((0,0),1,dxfattribs={'layer':'R'})
  for e in g['edges']:e['source_handles']=[m.add_line(*e['path_points'],dxfattribs={'layer':'R'}).dxf.handle]
  p={'readability_verified':True,'calibration_evidence':['actual native forms'],'contact_tolerance':.01,'pipe_layers':['R'],'radii':[1]}
  self.assertEqual(len(identify_in_doc(doc,g,p)),1);p['readability_verified']=False
  with self.assertRaises(ValueError):identify_in_doc(doc,g,p)
 def test_prior_floor_requires_same_node_position_and_source_evidence(self):
  nodes=[dict(node_id='U',x=1.,y=2.,floor='Schematic')];prior=[dict(node_id='U',x=1.,y=2.,floor='F1',floor_semantics='source floor title')]
  self.assertEqual(with_prior_floor(nodes,prior)[0]['floor'],'F1');self.assertEqual(nodes[0]['floor'],'Schematic')
  for change in ({'x':1.01},{'node_id':'other'},{'floor_semantics':''}):
   candidate=dict(prior[0],**change);self.assertEqual(with_prior_floor(nodes,[candidate])[0]['floor'],'Schematic')
