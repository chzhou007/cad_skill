import copy
import unittest
import ezdxf
from plan_hidden_branch_circle_screen import screen


class HiddenBranchCircleScreenTests(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new();m=self.doc.modelspace()
        main=m.add_line((0,0),(1000,0),dxfattribs={'layer':'return'})
        branch=m.add_line((200,-500),(200,-100),dxfattribs={'layer':'return'})
        circle=m.add_circle((700,0),80,dxfattribs={'layer':'supply'})
        self.circle=circle.dxf.handle
        self.graph={'metadata':{'source_sha256':'s'},'nodes':[{'node_id':'U','node_type':'virtual_equipment','subtype':'unresolved_source_terminal','system':'return','x':200,'y':-100},{'node_id':'V','node_type':'virtual_equipment','system':'return','x':200,'y':-500},{'node_id':'A','node_type':'tee','system':'return','x':0,'y':0},{'node_id':'B','node_type':'tee','system':'return','x':1000,'y':0}],'edges':[{'edge_id':'B1','start_node_id':'V','end_node_id':'U','system':'return','source_handles':[branch.dxf.handle],'path':[[200,-500],[200,-100]]},{'edge_id':'M','start_node_id':'A','end_node_id':'B','system':'return','source_handles':[main.dxf.handle],'path':[[0,0],[1000,0]]}]}
        self.policy={'source_sha256':'s','graph_sha256':'g','radius_range':[75,85],'max_extension':300,'max_along_main_offset':600,'system_layers':{'return':'return','supply':'supply'}}

    def test_finds_hidden_branch_candidate_even_when_circle_layer_differs(self):
        r=screen(self.doc,self.graph,self.policy,'s','g');self.assertEqual(len(r['candidates']),1)
        x=r['candidates'][0];self.assertEqual(x['circle_handle'],self.circle);self.assertEqual(x['system'],'return');self.assertEqual(x['circle_layer'],'supply');self.assertEqual(x['status'],'candidate_not_connectivity_proof');self.assertEqual(x['circle_offset_drawing_units'],500)

    def test_existing_tee_and_wrong_system_not_reproposed(self):
        g=copy.deepcopy(self.graph);g['nodes'].append({'node_id':'T','node_type':'tee','system':'return','x':700,'y':0})
        self.assertEqual(screen(self.doc,g,self.policy,'s','g')['candidates'],[])
        g=copy.deepcopy(self.graph);g['edges'][1]['system']='supply'
        self.assertEqual(screen(self.doc,g,self.policy,'s','g')['candidates'],[])

    def test_no_circle_and_bounds_do_not_infer_connection(self):
        p=copy.deepcopy(self.policy);p['radius_range']=[5,10]
        self.assertEqual(screen(self.doc,self.graph,p,'s','g')['candidates'],[])
        p=copy.deepcopy(self.policy);p['max_along_main_offset']=100
        self.assertEqual(screen(self.doc,self.graph,p,'s','g')['candidates'],[])
        self.assertEqual(self.graph['edges'][0]['end_node_id'],'U')

    def test_stale_and_ambiguous_branch_are_not_repaired(self):
        with self.assertRaises(ValueError):screen(self.doc,self.graph,self.policy,'s','stale')
        g=copy.deepcopy(self.graph);g['edges'].append(dict(g['edges'][0],edge_id='B2'))
        r=screen(self.doc,g,self.policy,'s','g');self.assertEqual(r['candidates'],[]);self.assertEqual(r['ambiguous'][0]['reason'],'not_single_incident_edge')


if __name__=='__main__':unittest.main()
