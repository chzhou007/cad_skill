import copy,csv,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_repair_confirmed_overlapping_branches as inherited
from repair_confirmed_overlapping_branches import apply
from confirm_crossview_paths import encode,load,sha
from native_line_path_evidence import LAYERS
from native_confirmed_overlap_rays import collect
from confirmed_overlap_plan_DN import current_tee


class Tests(unittest.TestCase):
    def fixture(self,angle=0,mirror=1):
        old=inherited.OverlappingBranchesTests();old.setUp()
        doc,parent,policy=old.doc,old.graph,old.policy
        if LAYERS['supply'] not in doc.layers:doc.layers.new(LAYERS['supply'])
        def xy(p):
            a=math.radians(angle)
            return [mirror*p[0]*math.cos(a)-p[1]*math.sin(a),mirror*p[0]*math.sin(a)+p[1]*math.cos(a)]
        for entity in doc.modelspace():
            if entity.dxftype()=='LINE':entity.dxf.layer=LAYERS['supply'];entity.dxf.start=xy(entity.dxf.start);entity.dxf.end=xy(entity.dxf.end)
            elif entity.dxftype()=='CIRCLE':entity.dxf.center=xy(entity.dxf.center)
        for node in parent['nodes']:node['x'],node['y']=xy([node['x'],node['y']])
        for edge in parent['edges']:
            for key in('path','path_points'):edge[key]=[xy(p)for p in edge[key]]
            edge['attribute_paths']=[[xy(p)for p in path]for path in edge['attribute_paths']]
        for connection in policy['connections']:
            connection['pipe_layer']=LAYERS['supply'];connection['circle_center']=xy(connection['circle_center'])
            connection['display_route']=[xy(p)for p in connection['display_route']]
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup);base=Path(directory.name)
        original=base/'parent.json';original.write_bytes(encode(parent));parent=load(original)
        devices=base/'devices.csv';devices.write_text('device_name,edge_id\n',encoding='utf8')
        answer=base/'answer.json';answer.write_bytes(encode(dict(user='fixed original explicit same-service connection')))
        evidence=base/'evidence.json';evidence.write_bytes(encode(dict(items=[dict(path=str(answer),sha256=sha(answer))])))
        policy.update(graph_sha256=sha(original),devices_sha256=sha(devices),evidence_manifest_sha256=sha(evidence))
        path=base/'policy.json';path.write_bytes(encode(policy))
        graph,audit=apply(doc,parent,[],policy,'s',sha(original),sha(evidence))
        entry={k:dict(path=str(p),sha256=sha(p))for k,p in dict(policy=path,evidence_manifest=evidence,parent_graph=original,parent_devices=devices).items()}
        return doc,graph,audit['records'],entry

    def test_native_rim_and_hidden_overlap_reuse_original_owner_rotations_and_mirrors(self):
        for angle,mirror in[(0,1),(37,1),(90,1),(180,-1),(270,-1)]:
            doc,graph,records,entry=self.fixture(angle,mirror);before=copy.deepcopy(graph)
            for row in records:
                proof=collect(doc,graph,row['tee'],'s','CURRENT',[entry])
                self.assertTrue(proof['original_owner_replayed']);self.assertFalse(proof['display_route_is_physical'])
                self.assertIsNone(proof['hidden_connection_length_mm']);self.assertEqual(len(proof['junctions'][0]['source_rays']),3)
            self.assertEqual(graph,before)

    def test_hidden_display_tail_does_not_become_the_branch_ray_or_measured_pipe(self):
        doc,graph,records,entry=self.fixture();row=records[1]
        proof=collect(doc,graph,row['tee'],'s','G',[entry]);ray=next(r for r in proof['junctions'][0]['source_rays']if r['edge_id']=='C')
        self.assertEqual(ray['direction'],[0,-1]);self.assertEqual(ray['graph_segment'][0],[300,-80])
        self.assertEqual(proof['junctions'][0]['position'],[700,0]);self.assertEqual(proof['physical_values_assigned'],0)
        branch=next(e for e in graph['edges']if e['edge_id']=='C');self.assertEqual(branch['path_length'],220)

    def test_stale_evidence_mixed_services_fake_lengths_and_unaccounted_source_lines_fail(self):
        for mode in('evidence','parent','policy','devices','mixed','route','physical','duplicate','fourway','unscoped'):
            doc,graph,records,entry=self.fixture();nid=records[1]['tee']
            if mode=='evidence':Path(load(entry['evidence_manifest']['path'])['items'][0]['path']).write_bytes(b'other')
            elif mode in('parent','policy','devices'):
                key={'parent':'parent_graph','policy':'policy','devices':'parent_devices'}[mode];Path(entry[key]['path']).write_bytes(b'{}')
            elif mode=='mixed':next(e for e in graph['edges']if e['edge_id']=='C')['system']='return'
            elif mode=='route':next(n for n in graph['nodes']if n['node_id']==nid)['user_confirmed_overlap_connection']['display_route'][0][0]+=1
            elif mode=='physical':next(e for e in graph['edges']if e['edge_id']=='C')['physical_length']='known'
            elif mode=='duplicate':doc.modelspace().add_line((0,0),(1000,0),dxfattribs={'layer':LAYERS['supply']})
            elif mode=='fourway':doc.modelspace().add_line((700,0),(700,300),dxfattribs={'layer':LAYERS['supply']})
            else:graph.pop('userConfirmedOverlappingBranches')
            with self.subTest(mode=mode),self.assertRaises(ValueError):collect(doc,graph,nid,'s','G',[entry])

    def test_original_confirmed_native_Z_is_recorded_without_becoming_height_or_length(self):
        doc,graph,records,entry=self.fixture()
        branch=doc.entitydb[load(entry['policy']['path'])['connections'][1]['branch_handle']]
        branch.dxf.start=(300,-300,4);branch.dxf.end=(300,-80,4)
        proof=collect(doc,graph,records[1]['tee'],'s','G',[entry])
        self.assertEqual(proof['original_native_XYZ']['branch'][0][2],4)
        self.assertIsNone(proof['hidden_connection_length_mm']);self.assertFalse(proof['physical_ports_verified'])

    def test_ordinary_missing_graph_ray_does_not_enable_an_unconfirmed_overlap(self):
        with patch('confirmed_overlap_plan_DN.previous_tee',side_effect=ValueError('missing or ambiguous graph T ray')):
            with patch('confirmed_overlap_plan_DN.overlap_collect')as fallback:
                with self.assertRaises(ValueError):current_tee(None,dict(nodes=[dict(node_id='T')]),'T','s','G',[],None,[])
                fallback.assert_not_called()


if __name__=='__main__':unittest.main()
