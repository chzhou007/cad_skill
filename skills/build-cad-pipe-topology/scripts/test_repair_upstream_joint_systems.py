import copy
import unittest
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from test_inline_system_conflict_triage import InlineConflictTriageTests
from native_line_path_evidence import LAYERS
from repair_upstream_joint_systems import repair, RULE, verify_output


def fixture():
    original = InlineConflictTriageTests(); original.setUp()
    d, g = original.doc, original.graph
    main = d.modelspace().add_line((-10,-10),(-10,10),dxfattribs={'layer':LAYERS['supply']})
    g['nodes']=[{'node_id':'T','node_type':'tee','x':-10,'y':0},
                {'node_id':'EQ1','node_type':'equipment','x':30,'y':5},
                {'node_id':'EQ2','node_type':'equipment','x':60,'y':0}]
    g['edges'][0].update(start_node_id='T',end_node_id='EQ1',
        attribute_paths=[[[-10,0],[0,0],[30,5]]],equipment_inventory=[])
    g['edges'][1].update(start_node_id='OTHER',end_node_id='EQ2',device_label='EQ2',
        equipment_inventory=[{'equipment_type':'金属软接','count':1,'device_names':['EQ2/hose']}])
    for eid,y in [('LOW',-10),('HIGH',10)]:
        g['edges'].append({'edge_id':eid,'system':'supply','start_node_id':'T',
            'end_node_id':eid,'attribute_paths':[[[-10,0],[-10,y]]],'equipment_inventory':[]})
    g['sourceInlineSystemConflicts'][0]['device_name']='EQ2/hose'
    rows=[{'device_name':'EQ2/hose','equipment_type':'金属软接',
        'source_top_handle':original.joint.dxf.handle,'assignment_status':'assigned',
        'assignment_x':'5','assignment_y':'0','edge_id':'R','owner_equipment':'EQ2'}]
    h=dict(source_sha256='source',graph_sha256='graph',devices_sha256='devices')
    p=dict(h,confirmation={'rule':RULE,'status':'user_confirmed',
        'source_reference':'expert confirmation fixture','statement':'Upstream main defines system.'},
        coverage_policy=dict(source_sha256='source',graph_sha256='graph',edges=['S']),
        junction_policy=dict(source_sha256='source',graph_sha256='graph',junctions=[{
            'node_id':'T','edge_witnesses':{'S':original.left.dxf.handle,
                'LOW':main.dxf.handle,'HIGH':main.dxf.handle}}]),
        joints=[{'joint_handle':original.joint.dxf.handle,'device_name':'EQ2/hose',
            'from_edge':'R','to_edge':'S','upstream_tee':'T',
            'upstream_contact_line':original.left.dxf.handle,'new_device_name':'EQ1/hose'}])
    return d,g,rows,p,h


class UpstreamJointRepairTests(unittest.TestCase):
    def test_corrects_cross_device_ownership_retains_original_source_and_unknown_length(self):
        d,g,rows,p,h=fixture(); before=copy.deepcopy((g,rows))
        result,inventory,audit=repair(d,g,rows,p,h)
        self.assertEqual((g,rows),before)
        self.assertEqual(inventory[0]['edge_id'],'S')
        self.assertEqual(inventory[0]['owner_equipment'],'EQ1')
        self.assertEqual(inventory[0]['original_owner_equipment'],'EQ2')
        self.assertEqual(inventory[0]['original_device_name'],'EQ2/hose')
        self.assertFalse(result['sourceInlineSystemConflicts'])
        self.assertEqual(result['nodes'],g['nodes'])
        self.assertEqual(audit['changes'][0]['original_conflict'],g['sourceInlineSystemConflicts'][0])
        self.assertEqual(audit['changes'][0]['physical_length'],'unknown')
        self.assertFalse(result['metadata']['hil_ready'])
        self.assertEqual(d.entitydb[g['sourceInlineSystemConflicts'][0]['contacts'][1]['lines'][0]['source_handle']].dxf.layer,LAYERS['return'])

    def test_same_edge_resolution_does_not_duplicate_component(self):
        d,g,r,p,h=fixture()
        g['edges'][0]['equipment_inventory']=g['edges'][1]['equipment_inventory'];g['edges'][1]['equipment_inventory']=[]
        r[0]['edge_id']='S';g['sourceInlineSystemConflicts'][0]['assigned_edge_id']='S'
        p['joints'][0]['from_edge']='S'
        new,rows,a=repair(d,g,r,p,h)
        self.assertEqual(sum(i['count'] for e in new['edges'] for i in e['equipment_inventory']),1)
        self.assertEqual(rows[0]['edge_id'],'S')

    def test_reverse_path_orientation_supported(self):
        d,g,r,p,h=fixture();g['edges'][0]['attribute_paths'][0].reverse()
        self.assertEqual(repair(d,g,r,p,h)[2]['remaining_conflicts'],0)

    def test_absent_expert_confirmation_and_stale_inputs_rejected(self):
        for k in ['confirmation','source_sha256','graph_sha256','devices_sha256']:
            with self.subTest(key=k):
                d,g,r,p,h=fixture();p.pop(k)
                with self.assertRaises(ValueError):repair(d,g,r,p,h)

    def test_broken_native_route_cannot_be_inherited(self):
        d,g,r,p,h=fixture()
        g['edges'][0]['attribute_paths']=[[[-10,0],[-5,0],[-5,5],[0,0],[30,5]]]
        with self.assertRaisesRegex(ValueError,'stale graph witness|reach selected joint'):repair(d,g,r,p,h)

    def test_ambiguous_source_ray_rejected(self):
        d,g,r,p,h=fixture()
        d.modelspace().add_line((-10,-10),(-10,10),dxfattribs={'layer':LAYERS['supply']})
        with self.assertRaisesRegex(ValueError,'ambiguous'):repair(d,g,r,p,h)

    def test_reject_other_target_or_duplicate_selection(self):
        for mode in ['target','duplicate']:
            with self.subTest(mode=mode):
                d,g,r,p,h=fixture()
                if mode=='target':p['joints'][0]['to_edge']='R'
                else:p['joints'].append(copy.deepcopy(p['joints'][0]))
                with self.assertRaises(ValueError):repair(d,g,r,p,h)

    def test_remaining_conflicts_not_cleared_by_empty_selection(self):
        d,g,r,p,h=fixture();p['joints']=[]
        with self.assertRaises(ValueError):repair(d,g,r,p,h)

    def test_cli_artifacts_reproduce_and_reject_tampered_inventory(self):
        d,g,rows,p,h=fixture()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);src=root/'source.dxf';gp=root/'graph.json';csvp=root/'devices.csv';pp=root/'policy.json'
            d.saveas(src);sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
            h['source_sha256']=sha(src);g['sourceInlineOwnershipRepair']['source_sha256']=sha(src)
            gp.write_text(json.dumps(g),encoding='utf8')
            with csvp.open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
            h.update(graph_sha256=sha(gp),devices_sha256=sha(csvp));p.update(h)
            for k in ('coverage_policy','junction_policy'):
                p[k].update(source_sha256=h['source_sha256'],graph_sha256=h['graph_sha256'])
            pp.write_text(json.dumps(p),encoding='utf8');out=root/'output'
            script=Path(__file__).with_name('repair_upstream_joint_systems.py')
            subprocess.run([sys.executable,str(script),'--source',str(src),'--graph',str(gp),
                '--devices',str(csvp),'--policy',str(pp),'--output',str(out)],check=True,capture_output=True)
            self.assertEqual(verify_output(out/'graph_with_edges.json')['joints'],1)
            inv=out/'edge_device_instances.csv'
            inv.write_bytes(inv.read_bytes().replace(b'EQ1/hose',b'EQ9/hose'))
            with self.assertRaisesRegex(ValueError,'not reproducible'):verify_output(out/'graph_with_edges.json')


if __name__=='__main__':unittest.main()
