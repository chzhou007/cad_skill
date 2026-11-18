"""Static compact imports must remain in the qualified dependency closure."""
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from current_attribute_read_runtime import module_closure
import current_attribute_read_runtime as current
from delivered_node_read_bridge import STATIC_IMPORTS as IMPORTS

class CompactImportClosureTests(unittest.TestCase):
    def setUp(self):
        # The new input adapter installs this matcher before the original
        # reader. Historical immutable modules stay byte-identical.
        guard=patch.object(current,'IMPORTS',IMPORTS);guard.start();self.addCleanup(guard.stop)
    def test_standard_and_compact_static_import_and_reexports(self):
        source="import{x}from'./one.js';export{y}from'./two.js';export*from'./three.js';import * as z from './four.js';"
        self.assertEqual(IMPORTS.findall(source),['./one.js','./two.js','./three.js','./four.js'])

    def test_transitive_compact_and_side_effect_modules_are_not_omitted(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder)
            for name,text in {'entry.js':"import{x}from'./one.js';import './side.js';",'one.js':"export{x}from'./two.js';",'two.js':'export const x=1;','side.js':'export const ready=true;'}.items():
                (root/name).write_text(text,encoding='utf8')
            before=module_closure(root/'entry.js')
            self.assertEqual(set(before),{'entry.js','one.js','two.js','side.js'})
            (root/'two.js').write_text('export const x=2;',encoding='utf8')
            self.assertNotEqual(before['two.js'],module_closure(root/'entry.js')['two.js'])

    def test_compact_parent_traversal_is_still_rejected(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'entry.js';path.write_text("import{x}from'../outside.js';",encoding='utf8')
            with self.assertRaisesRegex(ValueError,'external or nonliteral'):module_closure(path)

    def test_dynamic_import_is_still_rejected(self):
        with tempfile.TemporaryDirectory()as folder:
            path=Path(folder)/'entry.js';path.write_text("export const value=()=>import('./outside.js');",encoding='utf8')
            with self.assertRaisesRegex(ValueError,'unsupported runtime effects'):module_closure(path)

if __name__=='__main__':unittest.main()
