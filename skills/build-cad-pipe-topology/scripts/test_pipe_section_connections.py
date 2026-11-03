import unittest,copy
from pipe_section_connections import reconnect
class SectionTests(unittest.TestCase):
 def fixture(self):
  def n(i,x,y):return {'node_id':i,'node_type':'virtual_equipment','floor':'F1','x':x,'y':y,'ports':[{'port_id':i+'P'}]}
  def e(i,a,b,p):return {'edge_id':i,'start_node_id':a,'end_node_id':b,'system':'supply','path_points':p,'attribute_paths':[p],'source_handles':[i],'source_systems':['supply'],'path_length':sum(__import__('math').dist(x,y)for x,y in zip(p,p[1:])),'equipment_inventory':[]}
  g={'nodes':[n('A',-10,0),n('U',0,0),n('V',0,1),n('B',0,3)],'edges':[e('E1','A','U',[[-10,0],[0,0]]),e('E2','V','B',[[0,1],[0,3]])]}
  c=[{'handle':'C','x':0,'y':0,'r':1,'layer':'S'}];p={'id':'fixture','calibration_evidence':['native positive/negative fixture'],'readability_verified':True,'contact_tolerance':.01,'pipe_layers':['S'],'radii':[1],'angles_degrees':[90,180],'angle_tolerance_degrees':1,'short_tail_max_length':5}
  return g,c,{'E1':['S'],'E2':['S']},p
 def test_connect_preserves_source_paths_and_ids(self):
  g,c,l,p=self.fixture();before=copy.deepcopy(g);out,a=reconnect(g,c,l,p)
  self.assertEqual(len(out['nodes']),2);self.assertEqual(out['edges'][0]['edge_id'],'E1');self.assertEqual(len(out['edges'][0]['attribute_paths']),2);self.assertEqual(g,before);self.assertEqual(a['edge_id_mapping'],{'E2':'E1'})
 def test_cross_service_tangency_cannot_merge(self):
  g,c,l,p=self.fixture();g['edges'][1]['system']='return';out,a=reconnect(g,c,l,p);self.assertEqual(len(out['edges']),2)
 def test_wrong_source_layer_and_floor_stay_separate(self):
  g,c,l,p=self.fixture();l['E2']=['R'];self.assertEqual(len(reconnect(g,c,l,p)[0]['edges']),2)
  g,c,l,p=self.fixture();g['nodes'][2]['floor']='F2';self.assertEqual(len(reconnect(g,c,l,p)[0]['edges']),2)
 def test_internal_stroke_is_not_an_external_main(self):
  g,c,l,p=self.fixture();g['edges'][0]['path_points']=[[-.5,0],[0,0]];self.assertEqual(len(reconnect(g,c,l,p)[0]['edges']),2)
 def test_uncalibrated_or_unreadable_source_rejected(self):
  g,c,l,p=self.fixture();p['readability_verified']=False
  with self.assertRaises(ValueError):reconnect(g,c,l,p)
 def test_known_destination_not_retired(self):
  g,c,l,p=self.fixture();g['nodes'][1]['interface_destination']={'text':'已知接口'};self.assertEqual(len(reconnect(g,c,l,p)[0]['edges']),2)
 def test_rotated_and_mirrored_family(self):
  import math
  for mirror in [1,-1]:
   g,c,l,p=self.fixture()
   def f(x,y):return [mirror*(x-y)/math.sqrt(2)+4,(x+y)/math.sqrt(2)+6]
   for n in g['nodes']:n['x'],n['y']=f(n['x'],n['y'])
   for e in g['edges']:
    e['path_points']=[f(*q)for q in e['path_points']];e['attribute_paths']=[e['path_points']]
   c[0]['x'],c[0]['y']=f(0,0)
   self.assertEqual(len(reconnect(g,c,l,p)[0]['edges']),1)
 def test_component_identity_and_diameter_conflict(self):
  g,c,l,p=self.fixture()
  for i,e in enumerate(g['edges']):e['equipment_inventory']=[{'equipment_type':'V','count':1,'device_names':['V'+str(i)]}]
  out,_=reconnect(g,c,l,p);self.assertEqual(out['edges'][0]['equipment_inventory'][0]['count'],2)
  g['edges'][0]['diameter_nominal_mm']=50;g['edges'][1]['diameter_nominal_mm']=100
  self.assertEqual(len(reconnect(g,c,l,p)[0]['edges']),2)
 def test_prior_edge_id_is_reconciled_after_native_connection(self):
  import ezdxf
  from pipe_section_connections import apply_to_doc
  g,c,l,p=self.fixture();doc=ezdxf.new();m=doc.modelspace();m.add_circle((0,0),1,dxfattribs={'layer':'S'})
  for e in g['edges']:
   native=m.add_line(*e['path_points'],dxfattribs={'layer':'S'});e['source_handles']=[native.dxf.handle]
  prior={'edges':[{'edge_id':'KEEP','start_node_id':'A','end_node_id':'B','source_handles':[h for e in g['edges']for h in e['source_handles']]}]}
  out,a=apply_to_doc(doc,g,p,prior);self.assertEqual(out['edges'][0]['edge_id'],'KEEP');self.assertEqual(a['connections'][0]['retained_edge_id'],'KEEP')
if __name__=='__main__':unittest.main()
