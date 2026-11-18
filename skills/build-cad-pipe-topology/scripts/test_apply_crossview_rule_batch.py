from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from apply_crossview_rule_batch import checked,compute,sha


class Tests(unittest.TestCase):
    def test_input_change_stops_before_native_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'receipt.json';p.write_text('{}',encoding='utf8')
            good=dict(path=str(p),sha256=sha(p));self.assertEqual(checked(good),p)
            p.write_text('{"changed":true}',encoding='utf8')
            with patch('apply_crossview_rule_batch.verify_identity') as native:
                with self.assertRaisesRegex(ValueError,'dependency changed'):
                    compute(dict(inputs=dict(identity_receipt=good),metric_policies={}))
                native.assert_not_called()


if __name__=='__main__':unittest.main()
