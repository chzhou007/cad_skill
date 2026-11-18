import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from receive_current_review_answers import receive, produce, load, sha


class Tests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / 'pair.png').write_bytes(b'pair')
        digest = hashlib.sha256(b'pair').hexdigest()
        answer = dict(decision='平面省略，实物按轴测两阀', comment='保留原图',
                      source_pair_sha256=digest, updated_at='2026-11-12T09:23:29Z')
        question = dict(id='Q', text='两图差异？', options=[answer['decision'], '暂不确定'],
                        source_evidence=dict(pair_sha256=digest))
        existing = dict(schema='review', sections=[], followup_sections=[dict(title='源图对照',
                        image=dict(path='pair.png', sha256=digest), questions=[question])],
                        received_followup_feedback=dict(answers={'OLD': dict(decision='历史答复')},
                        status='old_receipt_status', receipt=dict(path='old-receipt')))
        reply = copy.deepcopy(existing)
        reply['followup_sections'][0]['questions'][0]['answer'] = copy.deepcopy(answer)
        reply['browser_answer_snapshot'] = dict(Q=copy.deepcopy(answer))
        return root, existing, reply

    def test_receive_preserves_old_answers_and_proves_no_native_application(self):
        root, existing, reply = self.fixture()
        before = copy.deepcopy(existing)
        result, report = receive(existing, reply, root, ['Q'])
        self.assertEqual(existing, before)
        self.assertEqual(result['followup_sections'], existing['followup_sections'])
        self.assertEqual(result['received_followup_feedback']['answers']['OLD'],
                         existing['received_followup_feedback']['answers']['OLD'])
        self.assertEqual(report['queue']['archived_received_questions'], ['Q'])
        self.assertEqual(report['native_technical_application_pending'], ['Q'])
        self.assertFalse(report['human_accepted'])
        self.assertEqual(report['physical_values_assigned'], 0)

    def test_changed_question_scope_pair_or_browser_snapshot_rejected(self):
        for field in ('text', 'options', 'source_evidence', 'snapshot', 'pair'):
            root, existing, reply = self.fixture()
            q = reply['followup_sections'][0]['questions'][0]
            if field == 'snapshot': reply['browser_answer_snapshot']['Q']['comment'] = 'different'
            elif field == 'pair': reply['followup_sections'][0]['image']['sha256'] = '0' * 64
            else: q[field] = 'changed'
            with self.subTest(field=field), self.assertRaises(ValueError):
                receive(existing, reply, root, ['Q'])

    def test_missing_choice_stale_pair_or_unreadable_comment_rejected(self):
        for key, value in [('decision', ''), ('source_pair_sha256', '0' * 64), ('comment', '\ufffd')]:
            root, existing, reply = self.fixture()
            reply['followup_sections'][0]['questions'][0]['answer'][key] = value
            reply['browser_answer_snapshot']['Q'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                receive(existing, reply, root, ['Q'])

    def test_changed_current_media_and_overwriting_old_answer_rejected(self):
        root, existing, reply = self.fixture()
        (root / 'pair.png').write_bytes(b'changed')
        with self.assertRaises(ValueError): receive(existing, reply, root, ['Q'])
        root, existing, reply = self.fixture()
        existing['received_followup_feedback']['answers']['Q'] = dict(decision='old')
        with self.assertRaisesRegex(ValueError, 'correction history'):
            receive(existing, reply, root, ['Q'])

    def test_optional_conflict_archive_preserves_prior_answers_and_never_authorizes(self):
        root, existing, reply = self.fixture()
        prior = dict(reply['browser_answer_snapshot']['Q'], decision='暂不确定', comment='旧意见')
        existing['received_followup_feedback']['answers']['Q'] = prior
        existing['received_followup_feedback']['received_pair_sha256_by_question'] = {'Q': prior['source_pair_sha256']}
        existing['received_followup_feedback']['count'] = 2
        before = copy.deepcopy(existing)
        result, report = receive(existing, reply, root, ['Q'], archive_conflicting_prior=True)
        self.assertEqual(result['received_followup_feedback'], before['received_followup_feedback'])
        self.assertEqual(existing, before)
        record = report['records'][0]
        self.assertTrue(record['conflicts_with_received_answer'])
        self.assertEqual(record['prior_received_answer'], prior)
        self.assertEqual(record['explicit_answer'], reply['browser_answer_snapshot']['Q'])
        self.assertEqual(record['status'], 'conflicting_received_answer_archived_not_authorized')
        self.assertEqual(report['conflicting_received_question_ids'], ['Q'])
        self.assertEqual(report['native_technical_application_pending'], [])
        self.assertFalse(record['native_application_proved'])
        self.assertFalse(report['human_accepted'])
        with self.assertRaisesRegex(ValueError, 'correction history'):
            receive(existing, reply, root, ['Q'])

    def test_conflict_archive_still_checks_pair_question_source_and_snapshot(self):
        for fault in ('pair', 'question', 'source', 'snapshot', 'unreadable'):
            root, existing, reply = self.fixture()
            existing['received_followup_feedback']['answers']['Q'] = dict(decision='暂不确定')
            if fault == 'pair':
                (root / 'pair.png').write_bytes(b'changed Pair')
            elif fault == 'question':
                reply['followup_sections'][0]['questions'][0]['text'] = 'changed question'
            elif fault == 'source':
                evidence = root / 'qualification.json'; evidence.write_bytes(b'{}')
                existing['current_review_queue_sources'] = {'Q': dict(
                    qualification=dict(path=str(evidence), sha256='0' * 64), source_inputs=[])}
            elif fault == 'snapshot':
                reply['browser_answer_snapshot']['Q']['comment'] = 'different'
            else:
                reply['browser_answer_snapshot']['Q']['comment'] = '\ufffd'
                reply['followup_sections'][0]['questions'][0]['answer']['comment'] = '\ufffd'
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                receive(existing, reply, root, ['Q'], archive_conflicting_prior=True)

    def test_conflict_from_an_older_receipt_does_not_add_new_followup_authority(self):
        root, existing, reply = self.fixture()
        prior = dict(reply['browser_answer_snapshot']['Q'], decision='暂不确定')
        existing['received_feedback'] = dict(answers={'Q': prior}, receipt='original-application')
        result, report = receive(existing, reply, root, ['Q'], archive_conflicting_prior=True)
        self.assertEqual(result['received_feedback'], existing['received_feedback'])
        self.assertNotIn('Q', result['received_followup_feedback']['answers'])
        self.assertNotIn('Q', result['received_followup_feedback']['received_pair_sha256_by_question'])
        self.assertEqual(report['records'][0]['prior_received_answer'], prior)

    def test_produce_archives_conflicting_raw_reply_and_strict_replay_stays_blocked(self):
        root, existing, reply = self.fixture()
        existing['received_followup_feedback']['answers']['Q'] = dict(decision='暂不确定')
        definitions, reply_path = root / 'existing.json', root / 'reply.json'
        for path, value in ((definitions, existing), (reply_path, reply)):
            path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'correction history'):
            produce(definitions, reply_path, root, ['Q'], root / 'strict')
        self.assertFalse((root / 'strict').exists())
        report = produce(definitions, reply_path, root, ['Q'], root / 'archived', archive_conflicting_prior=True)
        self.assertEqual(load(root / 'archived/receipt.json'), report)
        self.assertEqual((root / 'archived/original-reply.json').read_bytes(), reply_path.read_bytes())
        self.assertEqual(report['inputs']['reply']['sha256'], sha(reply_path))
        self.assertEqual(load(root / 'archived/review-queue.json')['received_followup_feedback']['answers']['Q'],
                         existing['received_followup_feedback']['answers']['Q'])
        with self.assertRaisesRegex(ValueError, 'correction history'):
            receive(load(report['inputs']['definitions']['path']), load(report['inputs']['reply']['path']), root, ['Q'])

    def test_optional_archive_has_no_effect_on_nonconflicting_receipt_wire_shape(self):
        root, existing, reply = self.fixture()
        normal = receive(existing, reply, root, ['Q'])
        archived = receive(existing, reply, root, ['Q'], archive_conflicting_prior=True)
        self.assertEqual(normal, archived)


if __name__ == '__main__':
    unittest.main()
