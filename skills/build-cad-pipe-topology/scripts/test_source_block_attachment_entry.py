import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_isometric_v17


class SourceBlockAttachmentEntryTest(unittest.TestCase):
 def test_requires_final_source_line_attachment(self):
  with tempfile.TemporaryDirectory() as folder:
   argv=['build_isometric_v17.py','--output-dir',folder,'--source-block-attachment-inputs','evidence.json']
   with patch.object(sys,'argv',argv), self.assertRaisesRegex(ValueError,'requires final partial line attachment'):
    build_isometric_v17.main()

 def test_existing_evidence_never_overwritten(self):
  with tempfile.TemporaryDirectory() as folder:
   (Path(folder)/'source_block_equipment_attachment_evidence.json').write_text('{}',encoding='utf8')
   argv=['build_isometric_v17.py','--output-dir',folder,'--exploded-device-chain-policy','chain.json','--final-path-coverage-policy','coverage.json','--final-partial-length-policy','length.json','--final-partial-line-policy','line.json','--final-attach-partial-line','--source-block-attachment-inputs','evidence.json']
   with patch.object(sys,'argv',argv), self.assertRaisesRegex(ValueError,'refusing to overwrite source block'):
    build_isometric_v17.main()


if __name__=='__main__':unittest.main()
