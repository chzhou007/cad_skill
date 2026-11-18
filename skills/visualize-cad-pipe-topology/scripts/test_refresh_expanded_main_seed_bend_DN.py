import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from expanded_main_seed_bend_DN import compose
from axis_unbranched_vertical_DN import native_items
from test_expanded_main_seed_bend_DN import fixture
from refresh_expanded_main_seed_bend_DN import context_from
from confirm_crossview_paths import encode


class Tests(unittest.TestCase):
    def test_exact_vertical_append_preserves_component_overlay_attribute_domain(self):
        args=fixture();proof=compose(*args,native_items(args[0],args[1]),'a'*64)
        proof.update(complete_current_viewer_replayed=True,known_parent_and_seed_bytes_requalified_in_parent_replay=True,
            inputs=dict(axis_source=dict(sha256='a'*64),axis_graph=dict(sha256='b'*64)))
        with tempfile.TemporaryDirectory()as folder:
            parent=Path(folder);(parent/'public/data').mkdir(parents=True)
            graph=parent/'public/data/graph.json';graph.write_bytes(encode(args[1]));actual=hashlib.sha256(graph.read_bytes()).hexdigest()
            manifest=dict(componentFragmentOverlay=dict(current_graph_sha256=actual,parent_graph_sha256='d'*64),attributeValueContext=dict(
                current_rendered_graph_sha256='d'*64,retained_physical_lengths=dict(unknown=None,known=1200),
                axis_rule_vertical_DN=dict(records=[],count=0,all_current_vertical_domains=0,remaining_unknown=1,
                    source_bindings=dict(native_source='a'*64,native_graph='b'*64,rendered_graph='d'*64,native_proof='e'*64))))
            path=parent/'public/data/manifest.json';path.write_bytes(encode(manifest));source=parent/'proof.json';source.write_bytes(encode(proof))
            proof['inputs']['parent_viewer_manifest']=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            before=copy.deepcopy(manifest);out=context_from(parent,proof,source)
            self.assertEqual(out['current_rendered_graph_sha256'],'d'*64)
            self.assertEqual(out['retained_physical_lengths'],manifest['attributeValueContext']['retained_physical_lengths'])
            self.assertEqual(out['axis_rule_vertical_DN']['all_current_vertical_domains'],1)
            self.assertEqual(out['axis_rule_vertical_DN']['source_bindings']['rendered_graph'],'d'*64)
            self.assertEqual(manifest,before)
            manifest['componentFragmentOverlay']['current_graph_sha256']='f'*64;path.write_bytes(encode(manifest))
            with self.assertRaises(ValueError):context_from(parent,proof,source)


if __name__=='__main__':unittest.main()
