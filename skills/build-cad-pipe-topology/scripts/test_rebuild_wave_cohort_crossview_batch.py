import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from confirm_crossview_paths import sha
from native_line_path_evidence import LAYERS
from rebuild_wave_cohort_crossview_batch import wave_branch,compute


class Tests(unittest.TestCase):
    def fixture(self):
        doc=ezdxf.new();m=doc.modelspace();layer=LAYERS['supply'];doc.layers.new(layer)
        main=m.add_line((-10,0),(10,0),dxfattribs=dict(layer=layer));branch=m.add_line((0,-10),(0,-1),dxfattribs=dict(layer=layer))
        nodes=[dict(node_id=n,node_type=t,floor=3,system='supply',x=x,y=y) for n,t,x,y in [('L','tee',-10,0),('T','tee',0,0),('R','tee',10,0),('D','equipment',0,-10)]]
        edges=[dict(edge_id='ML',start_node_id='L',end_node_id='T',system='supply',path=[[-10,0],[0,0]],attribute_paths=[[[-10,0],[0,0]]]),
               dict(edge_id='MR',start_node_id='T',end_node_id='R',system='supply',path=[[0,0],[10,0]],attribute_paths=[[[0,0],[10,0]]]),
               dict(edge_id='B',start_node_id='D',end_node_id='T',system='supply',path=[[0,-10],[0,-1],[0,0]],attribute_paths=[[[0,-10],[0,-1]]],path_length=9)]
        record=dict(equipment_id='D',system='supply',branch_edge='B',tee_id='T',outward=[0,1],
            original_branch=copy.deepcopy(edges[-1]),branch_contact=dict(source_line_handle=branch.dxf.handle,line_XYZ=[[0,-10,0],[0,-1,0]]),
            target=dict(source_handle=main.dxf.handle),wave=dict(wave_handle='W'))
        return doc,dict(nodes=nodes,edges=edges,sourceWaveMainCohort=dict(records=[record]))

    def test_current_source_branch_and_three_rays_keep_omitted_length_unknown(self):
        doc,g=self.fixture();result=wave_branch(doc,g,'D','supply','S','G')
        self.assertTrue(result['ready_for_mapping_comparison']);self.assertFalse(result['physical_ports_verified'])
        self.assertIsNone(result['whole_physical_length_mm']);self.assertEqual(result['trace']['tee'],'T')
        rays=result['junction_evidence']['junctions'][0]['source_rays'];self.assertEqual(len(rays),3)
        self.assertEqual({r['rule'] for r in rays},{'native_main_LINE_at_calibrated_wave_landing','calibrated_native_wave_omitted_branch_ray'})

    def test_changed_native_metric_scope_or_cross_system_ray_is_rejected(self):
        for mode in ('metric','service'):
            doc,g=self.fixture()
            if mode=='metric':g['edges'][-1]['path_length']=10
            else:g['edges'][0]['system']='return'
            with self.subTest(mode=mode),self.assertRaises(ValueError):wave_branch(doc,g,'D','supply','S','G')

    def test_dependency_changes_fail_before_replaying_complete_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'receipt';p.write_bytes(b'{}');pin=dict(path=str(p),sha256=sha(p));p.write_bytes(b'{"changed":true}')
            with patch('rebuild_wave_cohort_crossview_batch.verify_parent') as parent:
                with self.assertRaisesRegex(ValueError,'dependency changed'):compute(dict(inputs=dict(parent_receipt=pin)))
                parent.assert_not_called()


if __name__=='__main__':unittest.main()
