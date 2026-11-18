import copy
import unittest
import ezdxf
from native_level_evidence import verify, elevation_value


class NativeLevelEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.doc=ezdxf.new(); m=self.doc.modelspace(); rows=[]
        for floor,y,label,elev in [(1,0,'一层','±0.000'),(2,100,'二层','4.800'),(3,200,'三层','9.800')]:
            def line(a,b,layer='notes'):
                return m.add_line(a,b,dxfattribs={'layer':layer}).dxf.handle
            def text(t,p,height):
                return m.add_text(t,dxfattribs={'layer':'notes','insert':p,'height':height}).dxf.handle
            rows.append({'floor_number':floor,'floor_text':text(label,(20,y+7),10),
                         'elevation_text':text(elev,(-31,y+12),6),
                         'baseline':line((-100,y),(100,y),'building'),
                         'left_arm':line((0,y),(-10,y+10)), 'right_arm':line((0,y),(10,y+10)),
                         'leader':line((10,y+10),(-30,y+10)),
                         'elevation_text_expected':elev,'annotation_layer':'notes','baseline_layer':'building'})
        self.source='a'*64;self.policy={'source_sha256':self.source,'markers':rows}

    def test_verified_levels_only_not_pipe_length(self):
        result=verify(self.doc,self.policy,self.source)
        self.assertEqual([r['floor_text'] for r in result['levels']],['一层','二层','三层'])
        self.assertEqual([r['elevation_difference_decimal'] for r in result['consecutive_datum_differences']],['4.800','5.000'])
        self.assertTrue(all(r['physical_pipe_length'] is None for r in result['consecutive_datum_differences']))
        self.assertFalse(result['hil_ready'])

    def test_source_text_and_geometry_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'source hash mismatch'):verify(self.doc,self.policy,'b'*64)
        altered=copy.deepcopy(self.policy);altered['markers'][1]['floor_text']=altered['markers'][0]['floor_text']
        with self.assertRaisesRegex(ValueError,'unique'):verify(self.doc,altered,self.source)
        ent=self.doc.entitydb[self.policy['markers'][1]['right_arm']];ent.dxf.start=(1,100,0)
        with self.assertRaisesRegex(ValueError,'baseline or arrow'):verify(self.doc,self.policy,self.source)

    def test_incorrect_numeric_or_unit_text_is_not_assumed(self):
        for value in ['4.8','±2.000','4.800m','DN300(4.800)']:
            with self.assertRaises(ValueError):elevation_value(value)
        self.assertEqual(str(elevation_value('-3.200')),'-3.200')

    def test_floor_and_elevation_must_match_and_ascend(self):
        ent=self.doc.entitydb[self.policy['markers'][2]['elevation_text']];ent.dxf.text='4.000'
        policy=copy.deepcopy(self.policy);policy['markers'][2]['elevation_text_expected']='4.000'
        with self.assertRaisesRegex(ValueError,'order mismatch'):verify(self.doc,policy,self.source)
        policy=copy.deepcopy(self.policy);policy['markers'][2]['floor_number']=4
        with self.assertRaisesRegex(ValueError,'text mismatch'):verify(self.doc,policy,self.source)

if __name__=='__main__':unittest.main()
