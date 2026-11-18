import copy,unittest
import test_native_level_evidence as original_tests
from discover_native_level_markers import discover

def fixture():
    old=original_tests.NativeLevelEvidenceTest();old.setUp();return old.doc,old.policy,old.source

class Tests(unittest.TestCase):
    def test_original_marker_policies_and_verified_values_are_reused_exactly(self):
        from native_level_evidence import verify
        doc,policy,source=fixture();result=discover(doc,source)
        self.assertEqual(len(result['groups']),1);group=result['groups'][0]
        self.assertEqual(group['policy'],policy);self.assertEqual(group['verification'],verify(doc,policy,source))
        self.assertEqual(result['unresolved_floor_texts'],[]);self.assertEqual(result['physical_lengths_assigned'],0);self.assertFalse(result['graph_mutated'])

    def test_room_numbers_DN_and_decimal_text_without_symbols_never_form_datums(self):
        import ezdxf
        doc=ezdxf.new();m=doc.modelspace()
        for text,xy in [('一层',(20,7)),('±0.000',(-31,12)),('二层',(20,107)),('4.800',(-31,112)),('DN200(3.200)',(0,0))]:m.add_text(text,dxfattribs=dict(insert=xy,height=10))
        result=discover(doc,'a'*64);self.assertEqual(result['groups'],[]);self.assertEqual(len(result['unresolved_floor_texts']),2)

    def test_duplicate_baseline_or_floor_caption_withholds_the_entire_ambiguous_stack(self):
        for mode in('baseline','floor','other-layer-baseline'):
            doc,policy,source=fixture();spec=policy['markers'][1]
            if mode=='floor':e=doc.entitydb[spec['floor_text']];doc.modelspace().add_text(e.dxf.text,dxfattribs=dict(layer=e.dxf.layer,insert=e.dxf.insert,height=e.dxf.height))
            else:
                for spec in(policy['markers']if mode=='other-layer-baseline'else[spec]):
                    e=doc.entitydb[spec['baseline']];doc.modelspace().add_line(e.dxf.start,e.dxf.end,dxfattribs=dict(layer='another-building-layer'if mode=='other-layer-baseline'else e.dxf.layer))
            result=discover(doc,source);self.assertEqual(result['groups'],[]);self.assertTrue(result['pending_stacks'])

    def test_rotated_or_negative_OCS_text_remains_unsupported_without_changing_the_old_verifier(self):
        for mode in('rotate','OCS'):
            doc,policy,source=fixture()
            for spec in policy['markers']:
                text=doc.entitydb[spec['floor_text']]
                if mode=='rotate':text.dxf.rotation=90
                else:text.dxf.extrusion=(0,0,-1)
            result=discover(doc,source);self.assertEqual(result['groups'],[]);self.assertEqual({r['reason']for r in result['unresolved_floor_texts']},{'unsupported_rotation_or_OCS'})

    def test_independent_native_stacks_are_separate_and_unequal_floor_offsets_are_not_pipe_lengths(self):
        from ezdxf.math import Matrix44
        doc,policy,source=fixture()
        for e in list(doc.modelspace()):
            cloned=e.copy();doc.modelspace().add_entity(cloned);cloned.transform(Matrix44.translate(1000,0,0))
        result=discover(doc,source);self.assertEqual(len(result['groups']),2)
        self.assertTrue(all(v['physical_pipe_length']is None for g in result['groups']for v in g['verification']['consecutive_datum_differences']))

if __name__=='__main__':unittest.main()
