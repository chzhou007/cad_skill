from pathlib import Path
import subprocess
import unittest


class CurrentNamedPrefixFrontendTests(unittest.TestCase):
    def test_actual_precomposition_properties_CSV_and_negative_claims(self):
        result = subprocess.run(['node', str(Path(__file__).with_suffix('.mjs'))],
            capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
