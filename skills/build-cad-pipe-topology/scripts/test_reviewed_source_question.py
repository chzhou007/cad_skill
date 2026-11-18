import copy
from pathlib import Path
import tempfile
import unittest

from confirm_crossview_paths import load, sha, encode
from reviewed_source_question import bind_question


class Tests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        paths = {k: root / k for k in ('source', 'graph', 'pair', 'overview', 'native_context', 'reply', 'definitions', 'receipt')}
        for key in ('source', 'graph', 'pair', 'overview', 'native_context'):
            paths[key].write_text(key + '中文', 'utf8')
        evidence = {k: sha(paths[v]) for k, v in [('source_sha256', 'source'), ('graph_sha256', 'graph'),
            ('pair_sha256', 'pair'), ('overview_sha256', 'overview'), ('native_context_audit_sha256', 'native_context')]}
        answer = dict(decision='YES', source_pair_sha256=sha(paths['pair']))
        question = dict(id='Q', text='供回水各自连续？', options=['YES', 'NO'], source_evidence=evidence, answer=answer)
        section = dict(image=dict(sha256=sha(paths['pair'])), questions=[question])
        raw = dict(sections=[], followup_sections=[section], technical_updates=['not answer evidence'])
        definitions = copy.deepcopy(raw)
        del definitions['followup_sections'][0]['questions'][0]['answer']
        paths['reply'].write_bytes(encode(raw))
        paths['definitions'].write_bytes(encode(definitions))
        receipt = dict(input=dict(sha256=sha(paths['reply'])), records=[dict(question_id='Q', question=question['text'],
            options=question['options'], source_evidence=evidence, explicit_answer=answer, pair_sha256=sha(paths['pair']))])
        paths['receipt'].write_bytes(encode(receipt))
        policy = dict(question_id='Q', inputs={k: dict(sha256=sha(p)) for k, p in paths.items()})
        return paths, policy

    def test_exact_original_question_and_reply_reproduced(self):
        paths, policy = self.fixture()
        before = {k: p.read_bytes() for k, p in paths.items()}
        self.assertEqual(bind_question(paths, policy)['answer']['decision'], 'YES')
        self.assertEqual(before, {k: p.read_bytes() for k, p in paths.items()})

    def test_changed_source_or_pair_or_context_rejected(self):
        for key in ('source', 'pair', 'overview', 'native_context'):
            paths, policy = self.fixture()
            paths[key].write_text('changed', 'utf8')
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'input changed'):
                bind_question(paths, policy)

    def test_repinning_a_changed_pair_does_not_change_original_scope(self):
        paths, policy = self.fixture()
        paths['pair'].write_text('changed', 'utf8')
        policy['inputs']['pair']['sha256'] = sha(paths['pair'])
        with self.assertRaisesRegex(ValueError, 'original Pair differs'):
            bind_question(paths, policy)

    def test_changed_question_definition_rejected_even_if_config_rehashed(self):
        paths, policy = self.fixture()
        definitions = load(paths['definitions'])
        definitions['followup_sections'][0]['questions'][0]['text'] = 'different question'
        paths['definitions'].write_bytes(encode(definitions))
        policy['inputs']['definitions']['sha256'] = sha(paths['definitions'])
        with self.assertRaisesRegex(ValueError, 'question or Pair scope'):
            bind_question(paths, policy)

    def test_historical_technical_update_is_not_a_substitute_for_an_answer(self):
        paths, policy = self.fixture()
        policy['question_id'] = 'not answer evidence'
        with self.assertRaisesRegex(ValueError, 'missing or duplicated'):
            bind_question(paths, policy)


if __name__ == '__main__':
    unittest.main()
