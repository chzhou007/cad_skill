import unittest
from unittest.mock import patch
import ezdxf
from group_micro_line_circle_context import group

class GroupMicroLineTest(unittest.TestCase):
 def test_groups_repeated_3d_geometry_and_keeps_ambiguous_separate(self):
  d=ezdxf.new();m=d.modelspace();rows=[]
  for i in range(3):
   c=m.add_circle((i*100,0,0),80,dxfattribs={'layer':'pipe'})
   l=m.add_line((i*100-.002,0,0),(i*100,0,0),dxfattribs={'layer':'pipe'})
   node={'node_id':f'T{i}','node_type':'tee','incident_edges':[{'edge_id':f'E{i}{j}','system':'supply'} for j in range(3 if i<2 else 2)]}
   rows.append({'source_handle':l.dxf.handle,'system':'supply','same_layer_center_circles':[{'circle_handle':c.dxf.handle,'graph_nodes':[node]}]})
  with patch('group_micro_line_circle_context.compare',return_value={'records':rows}):
   result=group(d,{}, {},'S','G')
  self.assertEqual([len(f['members']) for f in result['families']],[2]);self.assertEqual(result['ungrouped_source_handles'],[rows[2]['source_handle']]);self.assertEqual(result['source_handle_count'],3);self.assertFalse(result['human_accepted']);self.assertFalse(result['hil_ready'])

 def test_empty_input_does_not_claim_acceptance(self):
  with patch('group_micro_line_circle_context.compare',return_value={'records':[]}):result=group(ezdxf.new(),{},{},'S','G')
  self.assertEqual(result['families'],[]);self.assertFalse(result['hil_ready'])
if __name__=='__main__':unittest.main()
