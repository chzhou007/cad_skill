import copy,unittest
import test_plan_pipe_diameter_scopes as fixtures
from checked_plan_DN_scope_attributes import attribute_checked_scope
from crossview_equipment_branch_inventory import native_tee
from pipe_annotation_attributes import source_texts


class InheritedDNKernelTests(unittest.TestCase):
    def setUp(self):self.f=fixtures.DiameterScopeTests()
    def run_scope(self,doc,graph,group,taps=None,excluded=()):
        taps=taps or {b['tee'] for b in group['branches']};ordered=[b['tee'] for b in group['branches']]+sorted(set(taps)-{b['tee'] for b in group['branches']})
        junctions={nid:native_tee(doc,graph,nid,'S','G') for nid in ordered}
        return attribute_checked_scope(doc,graph,group,source_texts(doc,'test','S'),'S','G',set(),junctions=junctions,verified_taps=taps,branch_frontier_edges=excluded)
    def test_inherited_kernel_is_byte_equivalent_on_legacy_rotated_mirrored_scopes(self):
        from confirm_crossview_paths import encode
        for angle,mirror in [(0,1),(90,1),(180,-1),(270,-1)]:
            doc,g,p=self.f.fixture(angle,mirror)
            self.assertEqual(encode(self.run_scope(doc,g,p)),encode(self.f.run_group(doc,g,p)))
    def test_direct_equipment_branch_override_does_not_backflow(self):
        doc,g,p=self.f.fixture();doc.modelspace().add_text('DN65',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(20.4,1.5)))
        r={r['edge_id']:r for r in self.run_scope(doc,g,p)['records']}
        self.assertEqual(r['supplyB2']['nominal_mm'],65);self.assertEqual(r['supplyM1']['nominal_mm'],80);self.assertEqual(r['supplyM2']['nominal_mm'],80)
    def test_non_through_interior_network_branch_cannot_seed_main(self):
        doc,g,p=self.f.fixture();taps={b['tee'] for b in p['branches']};excluded={'supplyB2','returnB2'}
        p['branches']=[b for b in p['branches'] if b['edge_id'] not in excluded]
        doc.modelspace().add_text('DN65',dxfattribs=dict(layer='AN',height=.3,rotation=90,insert=(20.4,1.5)))
        before=copy.deepcopy(g);out=self.run_scope(doc,g,p,taps,excluded);r={r['edge_id']:r for r in out['records']}
        self.assertEqual(g,before);self.assertEqual(r['supplyM1']['nominal_mm'],80);self.assertNotIn('supplyB2',r)
        self.assertEqual(out['non_through_branch_frontiers_excluded_from_main_inheritance'],sorted(excluded))
    def test_two_different_main_DNs_leave_the_branch_unknown(self):
        doc,g,p=self.f.fixture();doc.modelspace().add_text('DN125',dxfattribs=dict(layer='AN',height=1,insert=(25,.6)))
        r={r['edge_id']:r for r in self.run_scope(doc,g,p)['records']};self.assertIsNone(r['supplyB2']['nominal_mm']);self.assertEqual(r['supplyM2']['nominal_mm'],125)
    def test_frontier_scope_and_source_labels_stay_guarded(self):
        for case in ('bad_frontier','stale_seed','compound','leader'):
            doc,g,p=self.f.fixture()
            if case=='stale_seed':p['seeds'][0]['expected_text']='DN999'
            if case=='compound':doc.modelspace().add_text('DN80/DN65',dxfattribs=dict(layer='AN',height=1,insert=(17,.6)))
            if case=='leader':
                doc.modelspace().add_text('DN65',dxfattribs=dict(layer='AN',height=.3,insert=(50,5.5)));doc.modelspace().add_line((20,5),(50,5),dxfattribs=dict(layer='AN'))
            with self.assertRaises(ValueError):self.run_scope(doc,g,p,excluded={'NOT-A-FRONTIER'} if case=='bad_frontier' else ())


if __name__=='__main__':unittest.main()
