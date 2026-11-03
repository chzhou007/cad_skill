import unittest
from derive_hydraulic_graph import derive
class Projection(unittest.TestCase):
 def graph(self):return dict(nodes=[dict(node_id='A',node_type='tee',x=0,y=0),dict(node_id='P',node_type='equipment',subtype='Water Pump',x=10,y=0,source_handles=['pump']),dict(node_id='B',node_type='tee',x=20,y=0)],edges=[dict(edge_id='E1',start_node_id='A',end_node_id='P',system='supply',path_points=[[0,0],[9,0]],source_handles=['L']),dict(edge_id='E2',start_node_id='P',end_node_id='B',system='supply',path_points=[[11,0],[20,0]],source_handles=['R'])])
 def test_pump_is_one_edge_attribute_source_graph_unchanged(self):
  g=self.graph();v,rows,a=derive(g,[dict(device_name='V1',edge_id='E2')],{});self.assertEqual(len(g['nodes']),3);self.assertEqual(len(v['nodes']),2);self.assertEqual(len(v['edges']),1);self.assertEqual(len(v['edges'][0]['attribute_paths']),2);self.assertEqual({x['device_name']for x in rows},{'V1','P'});self.assertTrue(a['conservation'])
 def test_conflicting_system_pump_does_not_bridge(self):
  g=self.graph();g['edges'][1]['system']='return';v,rows,a=derive(g,[],{});self.assertEqual(len(v['edges']),2);self.assertIn('P',{n['node_id']for n in v['nodes']})
 def test_equipment_branch_exclusion_rejected(self):
  with self.assertRaises(ValueError):derive(self.graph(),[dict(device_name='V1',edge_id='E2')],dict(excluded_source_handles=['R']))
 def test_equipment_type_exclusion_rejected(self):
  with self.assertRaises(ValueError):derive(self.graph(),[],dict(excluded_equipment_types=['Water Pump']))
 def test_equipment_block_exclusion_rejected(self):
  g=self.graph();g['nodes'][1]['source_block']='BLOCK'
  with self.assertRaises(ValueError):derive(g,[],dict(excluded_equipment_blocks=['BLOCK']))
 def test_resistance_not_assumed_zero(self):
  g=self.graph();g['nodes'][1]['subtype']='Heat Exchanger';v,r,a=derive(g,[],{})
  n=next(n for n in v['nodes']if n['node_id']=='P');self.assertFalse(n['hydraulic_model']['assumed_zero_resistance']);self.assertFalse(v['hydraulicReadiness']['solver_ready'])
 def test_isolated_physical_equipment_not_dropped(self):
  g=self.graph();g['nodes'].append(dict(node_id='X',node_type='equipment',subtype='Dosing Unit',x=30,y=0));v,r,a=derive(g,[],{})
  self.assertIn('X',{n['node_id']for n in v['nodes']});self.assertEqual(next(n for n in v['hydraulicEquipmentCoverage']if n['node_id']=='X')['connection_status'],'source_ports_unresolved')
if __name__=='__main__':unittest.main()
