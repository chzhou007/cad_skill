import copy
import unittest
import ezdxf
from inline_system_conflict_triage import triage
from native_line_path_evidence import LAYERS

class InlineConflictTriageTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new();block=self.doc.blocks.new('JOINT')
        block.add_line((0,-1),(0,1));block.add_line((10,-1),(10,1))
        for x in (2,4,6,8):block.add_arc((x,0),1,0,180)
        m=self.doc.modelspace();self.joint=m.add_blockref('JOINT',(0,0))
        self.left=m.add_line((0,0),(-10,0),dxfattribs={'layer':LAYERS['supply']})
        self.right=m.add_line((10,0),(20,0),dxfattribs={'layer':LAYERS['return']})
        self.graph={'sourceInlineOwnershipRepair':{'source_sha256':'source'},
            'edges':[{'edge_id':'S','system':'supply','device_label':'EQ1','attribute_paths':[[[-10,0],[0,0]]]},
                     {'edge_id':'R','system':'return','device_label':'EQ1','attribute_paths':[[[50,0],[60,0]]]}],
            'sourceInlineSystemConflicts':[{'status':'source_system_conflict','joint_handle':self.joint.dxf.handle,
                'device_name':'EQ1/hose','assigned_edge_id':'R','witness_edge_ids':['S'],'contacts':[
                    {'midpoint':[0,0,0],'lines':[{'source_handle':self.left.dxf.handle,'system':'supply','line_start':[0,0,0],'line_end':[-10,0,0],'graph_edges':['S']}]},
                    {'midpoint':[10,0,0],'lines':[{'source_handle':self.right.dxf.handle,'system':'return','line_start':[10,0,0],'line_end':[20,0,0],'graph_edges':[]}]}]}]}
    def test_same_owner_conflict_is_classified_without_repair(self):
        before=copy.deepcopy(self.graph);out=triage(self.doc,self.graph,'source')
        self.assertEqual(out['records'][0]['classification'],'different_edge_same_device_system_conflict_remains')
        self.assertFalse(out['graph_mutated']);self.assertFalse(out['hil_ready']);self.assertEqual(self.graph,before)
    def test_different_owner_and_existing_assignment(self):
        self.graph['edges'][1]['device_label']='EQ2'
        self.assertEqual(triage(self.doc,self.graph,'source')['records'][0]['classification'],'different_edge_different_device_system_conflict_remains')
        self.graph['sourceInlineSystemConflicts'][0]['assigned_edge_id']='S'
        self.assertEqual(triage(self.doc,self.graph,'source')['records'][0]['classification'],'assigned_edge_matches_one_contact_system_conflict_remains')
    def test_stale_source_and_changed_witness_rejected(self):
        with self.assertRaises(ValueError):triage(self.doc,self.graph,'wrong')
        self.graph['edges'][0]['attribute_paths']=[[[100,0],[110,0]]]
        with self.assertRaises(ValueError):triage(self.doc,self.graph,'source')
    def test_duplicate_bar_contact_rejected(self):
        c=self.graph['sourceInlineSystemConflicts'][0]['contacts']
        c[1]=copy.deepcopy(c[0])
        with self.assertRaises(ValueError):triage(self.doc,self.graph,'source')
if __name__=='__main__':unittest.main()
