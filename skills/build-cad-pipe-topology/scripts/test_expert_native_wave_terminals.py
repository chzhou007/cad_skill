import copy
import unittest
import ezdxf
from expert_native_wave_terminals import attach

class ExpertNativeWave(unittest.TestCase):
 def setup_case(self):
  d=ezdxf.new('R2010');b=d.blocks.new('WAVE');b.add_lwpolyline([(-2,-1),(0,1),(2,-1)]);ins=d.modelspace().add_blockref('WAVE',(0,0));line=d.modelspace().add_line((0,0),(10,0),dxfattribs={'layer':'PIPE'})
  n={'node_id':'U','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'return','floor':3,'x':0,'y':0,'source_handles':[line.dxf.handle]};e={'edge_id':'E','start_node_id':'U','end_node_id':'T','system':'return','source_handles':[line.dxf.handle]};p={'source_sha256':'hash','expert_issue':'ERR','block_name':'WAVE','contact_tolerance':.1,'terminals':[{'insert_handle':ins.dxf.handle,'line_handle':line.dxf.handle,'line_layer':'PIPE','system':'return'}]};return d,[n],[e],p
 def test_existing_boundary_gains_identity_without_remote_connection(self):
  d,n,e,p=self.setup_case();glyphs,audit=attach(d,n,e,p,'hash');self.assertEqual(len(glyphs),1);self.assertEqual(n[0]['subtype'],'native_transverse_wave_interface');self.assertFalse(n[0]['remote_continuation_confirmed']);self.assertEqual(e[0]['start_port_id'],'U-P1');self.assertEqual(audit[0]['edge_id'],'E')
 def test_wrong_hash_line_or_competing_edge_rejected(self):
  d,n,e,p=self.setup_case()
  with self.assertRaises(ValueError):attach(d,copy.deepcopy(n),copy.deepcopy(e),p,'other')
  q=copy.deepcopy(p);q['terminals'][0]['line_layer']='OTHER'
  with self.assertRaises(ValueError):attach(d,copy.deepcopy(n),copy.deepcopy(e),q,'hash')
  with self.assertRaises(ValueError):attach(d,copy.deepcopy(n),copy.deepcopy(e+[dict(e[0],edge_id='E2')]),p,'hash')
