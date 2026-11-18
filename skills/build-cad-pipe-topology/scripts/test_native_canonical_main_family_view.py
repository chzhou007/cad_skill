import copy,tempfile,unittest
from pathlib import Path
from test_native_inherited_duplicate_circle_evidence import fixture
from native_inherited_duplicate_circle_evidence import collect
from native_canonical_main_family_view import project
from match_source_checked_crossview_paths import native_main_corridor
from native_line_path_evidence import LAYERS


class Tests(unittest.TestCase):
    def args(self,folder):
        doc,g,sh,gh,_=fixture(folder);taps={'D0':'C','D1':'A'}
        evidence={nid:dict(evidence=collect(doc,g,nid,sh,gh),branch_edges=['B'+nid]) for nid in taps.values()}
        meta=next(n for n in g['nodes'] if n['node_id']=='C')['expert_confirmed_circle'];family=meta['coincident_native_main_handles']
        return doc,g,taps,'supply',3,dict(canonical_source_handle=family[0],coincident_source_family=family),evidence,sh,gh

    def test_explicit_current_family_provenance_view_preserves_raw_entities_and_unknown_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.args(Path(temp));doc,g=args[:2];before=copy.deepcopy(g);raw=list(doc.modelspace().query('LINE'))
            with self.assertRaises(ValueError):native_main_corridor(doc,g,args[2],'supply',3)
            view,corridor,basis=project(*args);manifest=basis['canonical_source_projection']
            self.assertEqual(g,before);self.assertEqual(list(doc.modelspace().query('LINE')),raw)
            self.assertEqual(len(list(view.modelspace().query('LINE'))),len(raw)-1);self.assertIn(args[5]['coincident_source_family'][1],doc.entitydb)
            self.assertFalse(manifest['physical_source_identity_resolved']);self.assertFalse(manifest['source_entities_deleted']);self.assertEqual(len(manifest['source_entities']),2)
            self.assertEqual(basis['source_line_handle'],args[5]['canonical_source_handle']);self.assertTrue(corridor['edges'])

    def test_absent_explicit_family_stale_anchor_wrong_Z_or_unexplained_competitor_rejected(self):
        for case in ('family','canonical','Z','extra','anchor','wrong_owner','floor'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                args=list(self.args(Path(temp)));doc,g,taps,system,floor,spec,evidence,sh,gh=args
                if case=='family':spec['coincident_source_family']=spec['coincident_source_family'][:1]
                elif case=='canonical':spec['canonical_source_handle']='missing'
                elif case=='Z':doc.entitydb[spec['coincident_source_family'][1]].dxf.end=(0,100,1)
                elif case=='extra':doc.modelspace().add_line((0,-100,0),(0,200,0),dxfattribs=dict(layer=LAYERS['supply']))
                elif case=='anchor':evidence['A']['evidence']['graph_sha256']='stale'
                elif case=='wrong_owner':evidence['A']['evidence']['junctions'][0]['source_rays'][1]['source_line_handle']='other'
                else:args[4]=2
                with self.assertRaises(ValueError):project(*args)


if __name__=='__main__':unittest.main()
