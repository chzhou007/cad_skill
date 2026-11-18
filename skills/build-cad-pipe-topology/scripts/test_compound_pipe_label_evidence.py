import copy,json,tempfile,unittest
from pathlib import Path
import ezdxf
from compound_pipe_label_evidence import collect,parse,produce,verify

class CompoundLabelTests(unittest.TestCase):
    def test_different_diameters_and_levels_are_not_one_scalar(self):
        r=parse('DN300(3.600)/DN200(3.000)');self.assertEqual([m['nominal_mm']for m in r['members']],[300,200]);self.assertEqual([m['source_level_text']for m in r['members']],['3.600','3.000']);self.assertIsNone(r['scalar_whole_edge_DN_mm']);self.assertFalse(r['multiple_physical_pipes_proven'])
    def test_chinese_punctuation_and_signed_reference_preserved(self):
        r=parse('ＤＮ３００（＋３.６００）／DN200(-0.250)');self.assertEqual(r['members'][0]['source_level_text'],'+3.600');self.assertIsNone(r['members'][1]['physical_elevation_mm'])
    def test_plain_multi_DN_is_observation_not_pipe_population(self):
        r=parse('DN100/DN100');self.assertEqual(len(r['members']),2);self.assertFalse(r['multiple_physical_pipes_proven'])
    def test_scalar_names_partial_or_nonpositive_rejected(self):
        for text in ('DN200(3.200)','管道 DN300/DN200','DN300/备用','DN0/DN200','DN300(3.600)/DN200(3.000) 其他'):
            with self.subTest(text=text):self.assertIsNone(parse(text))
    def test_native_negative_OCS_and_rotation_are_source_only(self):
        doc=ezdxf.new('R2013');t=doc.modelspace().add_text('DN300(3.600)/DN200(3.000)',dxfattribs={'insert':(10,20,3),'extrusion':(0,0,-1),'rotation':90});r=collect(doc,'a'*64);row=r['records'][0];self.assertEqual(row['position_WCS'],list(t.ocs().to_wcs(t.dxf.insert)));self.assertFalse(row['connection_or_pipe_membership_proven']);self.assertEqual(r['physical_pipe_instances_created'],0)
    def test_nested_labels_are_not_silently_counted_modelspace(self):
        doc=ezdxf.new('R2013');block=doc.blocks.new('detail');block.add_text('DN300/DN200');doc.modelspace().add_blockref('detail',(0,0));self.assertEqual(collect(doc,'a'*64)['observations'],0)
    def test_real_native_producer_and_independent_replay_detect_tampering(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);source=root/'source.dxf';doc=ezdxf.new('R2013');doc.modelspace().add_text('二层暖通井');doc.modelspace().add_text('DN300(3.600)/DN200(3.000)');doc.saveas(source)
            out=root/'result';r=produce(source,out);self.assertEqual(verify(out)['observations'],1);self.assertEqual(r['scalar_DN_assignments'],0)
            p=out/'compound-pipe-labels.json';p.write_text(p.read_text(encoding='utf8')+' ',encoding='utf8')
            with self.assertRaises(ValueError):verify(out)
if __name__=='__main__':unittest.main()
