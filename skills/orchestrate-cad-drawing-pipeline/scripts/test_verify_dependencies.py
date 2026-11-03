import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import verify_dependencies as dep


class DependencyVersions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        for name,version in dep.VERSIONS.items():
            folder=self.root/name;folder.mkdir()
            header=('Version: **'if name.startswith('orchestrate')else'Current release: **v')
            (folder/'SKILL.md').write_text(header+version.replace('-HIL',' HIL')+'**\n','utf8')
        payload=b'canonical building owner\n'
        for name in ('extract-cad-building-context','visualize-cad-pipe-topology'):
            folder=self.root/name/'scripts';folder.mkdir();(folder/'architecture_context.py').write_bytes(payload)
        lock={'owner':'extract-cad-building-context','version':'1.1.1','sha256':hashlib.sha256(payload).hexdigest()}
        (self.root/'visualize-cad-pipe-topology/scripts/architecture-dependency-lock.json').write_text(json.dumps(lock),'utf8')
        self.patch=patch.object(dep,'ROOT',self.root);self.patch.start()

    def tearDown(self):
        self.patch.stop();self.tmp.cleanup()

    def test_current_declared_versions_and_owner_hash_pass(self):
        self.assertEqual(dep.verify()['status'],'completed')

    def test_historical_version_mention_cannot_hide_wrong_current_release(self):
        p=self.root/'build-cad-pipe-topology/SKILL.md'
        p.write_text('Current release: **v99.0.0**\nHistory: '+dep.VERSIONS['build-cad-pipe-topology'],'utf8')
        with self.assertRaisesRegex(ValueError,'Installed version differs'):
            dep.verify()

    def test_stale_version_file_cannot_hide_behind_current_skill_header(self):
        (self.root/'build-cad-pipe-topology/VERSION').write_text('1.8.0','utf8')
        with self.assertRaisesRegex(ValueError,'VERSION file differs'):
            dep.verify()

    def test_changed_building_vendor_still_requires_deliberate_sync(self):
        (self.root/'visualize-cad-pipe-topology/scripts/architecture_context.py').write_text('different owner code','utf8')
        with self.assertRaisesRegex(ValueError,'mismatch'):
            dep.verify()


if __name__=='__main__':unittest.main()
