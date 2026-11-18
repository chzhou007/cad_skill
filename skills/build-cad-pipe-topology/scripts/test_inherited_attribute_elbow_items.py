import copy,unittest
import ezdxf
import pipe_geometry
from inherited_attribute_elbow_items import collect
from axis_unbranched_vertical_DN import native_items,chain_evidence
from native_line_path_evidence import LAYERS

class AttributeElbowInheritanceTests(unittest.TestCase):
    def fixture(self):
        d=ezdxf.new('R2013');m=d.modelspace();line=m.add_line((10,-18,0),(10,2,0),dxfattribs={'layer':LAYERS['supply']});m.add_line((0,-10,0),(10,0,0),dxfattribs={'layer':LAYERS['supply']});g=dict(metadata={},edges=[]);policy=dict(config=dict(elbow_overshoot=dict(maximum_length=10,maximum_ratio=.1,minimum_angle_degrees=20)),elbow_overshoots=[dict(source_handles=[line.dxf.handle],original_endpoint=[10,2],semantic_endpoint=[10,0])]);scopes=[dict(native_source_status='single_source_line_covers',system='supply',scope_points=[[0,-10],[10,0]],path_index=0,segment_index=0),dict(native_source_status='single_source_line_covers',system='supply',scope_points=[[10,0],[10,-18]],path_index=0,segment_index=1)];return d,g,policy,scopes
    def test_original_trim_restores_two_arm_reader_without_changing_graph_source_or_global_tolerance(self):
        d,g,p,s=self.fixture();before=copy.deepcopy(g);tol=pipe_geometry.TOL;raw=native_items(d,g)
        with self.assertRaisesRegex(ValueError,'another source arm'):chain_evidence(s,None,raw)
        items,proof=collect(d,g,p);r=chain_evidence(s,None,items);self.assertEqual(r['bends'][0]['source_arms'],2);self.assertEqual(len(proof['records']),1);self.assertEqual(proof['physical_lengths_assigned'],0);self.assertEqual(g,before);self.assertEqual(pipe_geometry.TOL,tol);self.assertEqual(list(d.entitydb[p['elbow_overshoots'][0]['source_handles'][0]].dxf.end),[10,2,0])
    def test_missing_history_or_larger_threshold_is_rejected(self):
        d,g,p,s=self.fixture();p['elbow_overshoots']=[]
        with self.assertRaisesRegex(ValueError,'history'):collect(d,g,p)
        d,g,p,s=self.fixture();p['config']['elbow_overshoot']['maximum_length']=11
        with self.assertRaisesRegex(ValueError,'limits'):collect(d,g,p)
    def test_real_tip_attachment_and_Z_difference_remain_protected(self):
        d,g,p,s=self.fixture();d.modelspace().add_line((10,2,0),(14,2,0),dxfattribs={'layer':LAYERS['supply']});items,proof=collect(d,g,p);self.assertEqual(proof['records'],[])
        d,g,p,s=self.fixture();next(e for e in d.modelspace()if list(e.dxf.start)==[0,-10,0]).dxf.start=(0,-10,1);next(e for e in d.modelspace()if list(e.dxf.start)==[0,-10,1]).dxf.end=(10,0,1)
        with self.assertRaisesRegex(ValueError,'same-Z'):collect(d,g,p)

if __name__=='__main__':unittest.main()
