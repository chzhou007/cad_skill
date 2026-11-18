from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from build_native_caption_identity import build
from confirm_crossview_paths import encode,sha


class Tests(unittest.TestCase):
    def test_changed_fixed_input_stops_before_native_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);source=d/'source.dxf';source.write_text('unchanged',encoding='utf8')
            policy=d/'policy.json';policy.write_bytes(encode(dict(inputs=dict(source=dict(path=str(source),sha256=sha(source))))))
            source.write_text('changed',encoding='utf8')
            with patch('build_native_caption_identity.compute') as native:
                with self.assertRaisesRegex(ValueError,'input differs source'):
                    build(dict(source=source,graph=d/'graph.json',devices=d/'components.csv'),policy,d/'output')
                native.assert_not_called()


if __name__=='__main__':unittest.main()
