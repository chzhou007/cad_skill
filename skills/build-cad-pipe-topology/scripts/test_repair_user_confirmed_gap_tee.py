import copy
import unittest
import tempfile
from pathlib import Path
import ezdxf
from repair_user_confirmed_gap_tee import apply, reject_revoked_policy


class ConfirmedGapTeeTests(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        m = self.doc.modelspace()
        main = m.add_line((0, 0), (1000, 0), dxfattribs={'layer': 'return'})
        branch = m.add_line((400, -300), (400, -80), dxfattribs={'layer': 'return'})
        supply = m.add_line((0, -120), (1000, -120), dxfattribs={'layer': 'supply'})
        def node(i, x, y, system='return', subtype=None):
            return {'node_id': i, 'node_type': 'virtual_equipment' if subtype else 'tee', 'subtype': subtype, 'system': system, 'x': x, 'y': y, 'floor': 1}
        def edge(i, a, b, path, h, system='return'):
            return {'edge_id': i, 'start_node_id': a, 'end_node_id': b, 'system': system, 'start_floor': 1, 'end_floor': 1, 'path': path, 'path_points': copy.deepcopy(path), 'attribute_paths': [copy.deepcopy(path)], 'path_length': sum(((q[0]-p[0])**2+(q[1]-p[1])**2)**.5 for p,q in zip(path,path[1:])), 'source_handles': [h], 'equipment_names': [], 'equipment_counts': {}}
        self.graph = {'metadata': {'source_sha256': 's'}, 'nodes': [node('A',0,0),node('B',1000,0),node('U',400,-80,subtype='unresolved_source_terminal'),node('V',400,-300,subtype='out_of_plane_interface'),node('S1',0,-120,'supply'),node('S2',1000,-120,'supply')], 'edges': [edge('M','A','B',[[0,0],[1000,0]],main.dxf.handle),edge('BR','V','U',[[400,-300],[400,-80]],branch.dxf.handle),edge('S','S1','S2',[[0,-120],[1000,-120]],supply.dxf.handle,'supply')], 'virtual_equipment_ports': []}
        self.policy = {'source_sha256':'s','graph_sha256':'g','confirmed_by':'user','evidence_sha256':'e','main_edge':'M','branch_edge':'BR','terminal':'U','system':'return','main_handle':main.dxf.handle,'branch_handle':branch.dxf.handle,'source_layer':'return','junction_xy':[400,0],'tee_id':'T','child_edge_id':'M2'}

    def test_repair_and_crossing_isolation(self):
        out,_ = apply(self.doc,self.graph,[],self.policy,'s','g')
        incident = [e for e in out['edges'] if 'T' in (e['start_node_id'],e['end_node_id'])]
        self.assertEqual(len(incident),3)
        self.assertEqual({e['system'] for e in incident},{'return'})
        supply = next(e for e in out['edges'] if e['edge_id']=='S')
        for key in ('start_node_id','end_node_id','path','path_length','source_handles','system'):
            self.assertEqual(supply[key],self.graph['edges'][2][key])
        b=next(e for e in out['edges'] if e['edge_id']=='BR')
        self.assertEqual(b['attribute_paths'],[[[400,-300],[400,-80]]])
        self.assertEqual(b['path_length'],220)
        self.assertFalse(b['path_length_complete'])
        self.assertEqual(b['confirmed_gap_extension']['physical_length'],'unknown')
        self.assertEqual(self.graph['edges'][1]['end_node_id'],'U')
        self.assertFalse(out['metadata']['hil_ready'])

    def test_reject_unconfirmed_wrong_hash_and_system(self):
        for key,value in [('confirmed_by','algorithm'),('graph_sha256','stale'),('system','supply'),('evidence_sha256','')]:
            p=copy.deepcopy(self.policy);p[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): apply(self.doc,self.graph,[],p,'s','g')

    def test_reject_noncollinear_and_existing_component(self):
        p=copy.deepcopy(self.policy);p['junction_xy']=[410,0]
        with self.assertRaises(ValueError):apply(self.doc,self.graph,[],p,'s','g')
        with self.assertRaises(ValueError):apply(self.doc,self.graph,[{'edge_id':'M'}],self.policy,'s','g')

    def test_reject_extension_back_along_branch(self):
        g=copy.deepcopy(self.graph)
        g['nodes'][2]['y']=-300
        g['nodes'][3]['y']=-80
        g['edges'][1]['path']=[[400,-80],[400,-300]]
        with self.assertRaises(ValueError):apply(self.doc,g,[],self.policy,'s','g')

    def test_reject_unmapped_attributes_and_source_layer(self):
        g=copy.deepcopy(self.graph);g['edges'][0]['diameter_nominal_mm']=300
        with self.assertRaises(ValueError):apply(self.doc,g,[],self.policy,'s','g')
        p=copy.deepcopy(self.policy);p['source_layer']='supply'
        with self.assertRaises(ValueError):apply(self.doc,self.graph,[],p,'s','g')

    def test_revoked_policy_is_rejected_and_invalid_registry_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'revoked.json';p.write_text('{"schema_version":1,"revoked":{"old":"correction"}}',encoding='utf8')
            with self.assertRaises(ValueError):reject_revoked_policy('old',p)
            reject_revoked_policy('new',p)
            p.write_text('{"schema_version":2,"revoked":{}}',encoding='utf8')
            with self.assertRaises(ValueError):reject_revoked_policy('new',p)


if __name__=='__main__':unittest.main()
