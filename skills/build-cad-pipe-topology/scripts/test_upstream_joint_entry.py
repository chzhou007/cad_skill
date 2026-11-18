import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import build_isometric_v17


class UpstreamJointEntryTests(unittest.TestCase):
    def evaluate(self, flags, expected):
        with tempfile.TemporaryDirectory() as folder:
            argv=['build_isometric_v17.py','--output-dir',folder]+flags
            with patch.object(sys,'argv',argv),self.assertRaisesRegex(ValueError,expected):
                build_isometric_v17.main()

    def test_requires_source_attachment_graph(self):
        self.evaluate(['--upstream-joint-system-policy','correction.json'],
                      'requires the final source attachment graph')

    def test_floor_reconciliation_requires_source_attachment_graph(self):
        self.evaluate(['--source-floor-repair-inputs','floor.json'],
                      'requires the final source attachment graph')

    def test_corrected_inventory_cannot_reuse_old_direct_joint_contact_audit(self):
        self.evaluate(['--upstream-joint-system-policy','correction.json',
                       '--source-block-attachment-inputs','attachment.json',
                       '--final-gap-joint-policy','gap.json','--direct-spline-joint-policy','old.json'],
                      'requires final direct joint recheck')

    def test_final_joint_audit_cannot_run_without_correction(self):
        self.evaluate(['--final-direct-spline-joint-policy','final.json'],
                      'requires upstream system correction')

    def test_existing_correction_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'topology-upstream-joint-systems').mkdir()
            argv=['build_isometric_v17.py','--output-dir',folder,
                  '--upstream-joint-system-policy','correction.json',
                  '--source-block-attachment-inputs','attachment.json']
            with patch.object(sys,'argv',argv),self.assertRaisesRegex(ValueError,'refusing to overwrite'):
                build_isometric_v17.main()


if __name__=='__main__':unittest.main()
