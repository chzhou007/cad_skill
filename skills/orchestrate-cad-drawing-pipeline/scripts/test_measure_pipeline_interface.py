import hashlib,json,tempfile,unittest
from pathlib import Path
from measure_pipeline_interface import measure

class MeasureInterface(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name)
        self.before=self.r/'before.json';self.after=self.r/'after.json';self.proof=self.r/'proof.json'
        self.before.write_text(json.dumps({'当前值':'中文','历史':['旧数据']*40},ensure_ascii=False),'utf8')
        self.after.write_text(json.dumps({'当前值':'中文'},ensure_ascii=False),'utf8');self.proof.write_text('{}','utf8')
        def pin(p):return{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        self.manifest=self.r/'input.json';self.data={'schema_version':1,'comparisons':[{'id':'query','before':[pin(self.before)],'after':[pin(self.after)],'correctness_evidence':[pin(self.proof)]}]}
        self.manifest.write_text(json.dumps(self.data),'utf8')
    def tearDown(self):self.tmp.cleanup()
    def test_unicode_byte_measurement_does_not_claim_model_savings(self):
        report=measure(self.manifest,self.r/'out.json');row=report['comparisons'][0]
        self.assertEqual(row['after']['utf8_bytes'],len(self.after.read_bytes()))
        self.assertLess(row['after']['characters'],row['after']['utf8_bytes'])
        self.assertGreater(row['utf8_bytes_reduction_fraction'],0.8)
        self.assertFalse(report['actual_model_usage_measured']);self.assertIsNone(row['before']['text_tokens'])
    def test_changed_payload_rejected(self):
        self.after.write_text('changed','utf8')
        with self.assertRaisesRegex(ValueError,'hash changed'):measure(self.manifest,self.r/'out.json')
    def test_changed_correctness_evidence_rejected(self):
        self.proof.write_text('changed','utf8')
        with self.assertRaisesRegex(ValueError,'hash changed'):measure(self.manifest,self.r/'out.json')
    def test_duplicate_ids_and_existing_reports_rejected(self):
        measure(self.manifest,self.r/'out.json')
        with self.assertRaises(FileExistsError):measure(self.manifest,self.r/'out.json')
        self.data['comparisons']*=2;self.manifest.write_text(json.dumps(self.data),'utf8')
        with self.assertRaisesRegex(ValueError,'unique'):measure(self.manifest,self.r/'new.json')

if __name__=='__main__':unittest.main()
