import unittest
import ezdxf
from common_schedule_evidence import common_phrase


class CommonScheduleEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.doc = ezdxf.new()
        a = self.doc.modelspace().add_text('备注：底部接管')
        b = self.doc.modelspace().add_text('3、底部接管；')
        self.profiles = [self.profile('A', a), self.profile('B', b)]

    @staticmethod
    def profile(name, entity):
        return {'profile_id': name, 'properties': {'requirements': {'source': {'entities': [
            {'handle': entity.dxf.handle, 'text': entity.plain_text()}]}}}}

    def test_common_is_reference_only(self):
        result = common_phrase(self.profiles, ['B', 'A'], self.doc, '底部接管')
        self.assertEqual(result['status'], 'common_candidate_reference_only')
        self.assertEqual(len(result['witnesses']), 2)
        self.assertFalse(result['instance_connection_verified'])

    def test_noncommon_and_missing_never_inferred(self):
        self.assertEqual(common_phrase(self.profiles, ['A', 'B'], self.doc, '备注')['status'],
                         'not_common_or_missing_evidence')
        with self.assertRaises(ValueError): common_phrase(self.profiles, ['A', 'C'], self.doc, '底部接管')

    def test_changed_source_and_duplicate_candidate_rejected(self):
        entity = self.doc.entitydb[self.profiles[0]['properties']['requirements']['source']['entities'][0]['handle']]
        entity.dxf.text = '备注：顶部接管'
        with self.assertRaises(ValueError): common_phrase(self.profiles, ['A', 'B'], self.doc, '底部接管')
        with self.assertRaises(ValueError): common_phrase(self.profiles, ['A', 'A'], self.doc, '底部接管')


if __name__ == '__main__': unittest.main()
