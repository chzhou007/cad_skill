"""HIL orchestration contracts and a real subprocess synthetic closed loop.

The small native owner substitutes for expensive CAD calculation, while answer
intake, rule resolution, pinned commands, DAG scheduling, regression comparison,
publication sequencing and finalization execute their production implementations.
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch

import hil_feedback_pipeline as pipeline


SYNTHETIC_OWNER = r'''
import argparse,hashlib,json,pathlib,shutil
P=pathlib.Path
def load(p):return json.loads(P(p).read_text('utf-8'))
def sha(p):return hashlib.sha256(P(p).read_bytes()).hexdigest()
def pin(p):return {'path':str(P(p).resolve()),'sha256':sha(p)}
def checked(b):
 p=P(b['path']);assert p.is_file() and sha(p)==b['sha256'];return p
def write(p,value):
 p=P(p);p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def compute(manifest):
 m=load(manifest);source=load(checked(m['inputs']['source']))
 receipt=load(checked(m['inputs']['answer_receipt']))
 rows=[r for r in receipt['records'] if r['question_id'] in m['question_ids']]
 assert sorted(r['question_id'] for r in rows)==sorted(m['question_ids'])
 assert all(r['explicit_answer']['decision']=='按原图保留' for r in rows)
 return {'mode':'synthetic_native','inputs':m['inputs'],'manifest':pin(manifest),
         'records':[{'question_id':r['question_id'],'value':source[r['question_id']]} for r in rows],
         'human_accepted':False}
def native_proof(path):
 p=load(path);assert p==compute(checked(p['manifest']));return p
parser=argparse.ArgumentParser();parser.add_argument('action')
for name in ('manifest','native','parent','proof','viewer','output'):parser.add_argument('--'+name)
a=parser.parse_args();out=P(a.output)
if a.action=='native':
 out.mkdir(parents=True);p=compute(a.manifest);write(out/'proof.json',p)
 write(out/'receipt.json',{'status':'passed','proof':pin(out/'proof.json')})
elif a.action=='verify':
 p=native_proof(P(a.native)/'proof.json')
 write(out/'verification.json',{'status':'passed','proof':pin(P(a.native)/'proof.json'),
                               'proof_sha256':sha(P(a.native)/'proof.json'),'records':len(p['records'])})
elif a.action=='publish':
 p=native_proof(a.proof);parent=P(a.parent);shutil.copytree(parent,out)
 values=load(out/'published.json') if (out/'published.json').exists() else {}
 for row in p['records']:values[row['question_id']]=row['value']
 write(out/'published.json',values)
 write(out/'publication.json',{'status':'published','proof':pin(a.proof),'proof_sha256':sha(a.proof),'parent':str(parent),
                              'graph':pin(parent/'public/data/graph.json'),'records':len(p['records'])})
 manifest=load(out/'public/data/manifest.json')
 manifest['reviewedDetailFeedback']={'receipt_path':'publication.json'}
 write(out/'public/data/manifest.json',manifest)
elif a.action=='publish_verify':
 viewer=P(a.viewer);r=load(viewer/'publication.json');p=native_proof(checked(r['proof']))
 values=load(viewer/'published.json')
 assert all(values[row['question_id']]==row['value'] for row in p['records'])
 assert sha(viewer/'public/data/graph.json')==r['graph']['sha256']
 parent=P(r['parent'])
 assert {f.name:f.read_bytes() for f in (parent/'annotations').glob('*')}=={f.name:f.read_bytes() for f in (viewer/'annotations').glob('*')}
 write(out/'verification.json',{'status':'passed','publication':pin(viewer/'publication.json'),
                               'proof':r['proof'],'proof_sha256':r['proof']['sha256'],'checked_records':len(p['records'])})
else:raise ValueError(a.action)
'''

FEATURE_IMPACT = r'''
import json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
def load_registry():
 data=json.loads((ROOT/'registry.json').read_text('utf-8'));return data,{r['id']:r for r in data['features']}
def run_selected(selection,root,workers):
 result=[]
 for name in selection['tests']:
  process=subprocess.run([sys.executable,'-B',str(ROOT/name)],capture_output=True,text=True,encoding='utf-8')
  result.append({'test':name,'exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr})
 return result
'''


class Tests(unittest.TestCase):
    def fixture(self, groups=None, history=True):
        temp = tempfile.TemporaryDirectory(prefix='hil-feedback-tests-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / '中文闭环'
        root.mkdir()
        skills = root / 'skills'
        scripts = skills / 'orchestrate-cad-drawing-pipeline/scripts'
        scripts.mkdir(parents=True)
        # The production orchestrator is copied unchanged for child-process
        # finalization/regression under this isolated synthetic skill tree.
        copied_pipeline = scripts / 'hil_feedback_pipeline.py'
        shutil.copy2(pipeline.__file__, copied_pipeline)
        (scripts / 'feature_impact.py').write_text(textwrap.dedent(FEATURE_IMPACT), encoding='utf-8')
        (scripts / 'verify_dependencies.py').write_text(
            "def verify(): return {'status':'completed','synthetic_dependency_closure':True}\n", encoding='utf-8')
        native = skills / 'synthetic-owner/scripts/owner.py'
        native.parent.mkdir(parents=True)
        native.write_text(textwrap.dedent(SYNTHETIC_OWNER), encoding='utf-8')
        test = skills / 'synthetic-owner/scripts/test_baseline.py'
        test.write_text("import unittest\nclass T(unittest.TestCase):\n def test_chinese(self): self.assertEqual('历史记录', '历史'+'记录')\nunittest.main()\n", encoding='utf-8')
        features = [{'id': 'historic-feature', 'tests': ['synthetic-owner/scripts/test_baseline.py']}]
        baseline = root / 'baseline-registry.json'
        pipeline.write(baseline, {'features': features})
        pipeline.write(skills / 'registry.json', {'features': features})
        parent = root / 'parent-viewer'
        pipeline.write(parent / 'public/data/graph.json', {'edges': [{'edge_id': 'E1'}], 'source': '原图'})
        pipeline.write(parent / 'public/data/manifest.json', {'bundleId': 'parent-id', 'identity': '保留'})
        pipeline.write(parent / 'annotations/history.json', {'manual': '历史批注', 'revision': 9})
        pipeline.write(parent / 'unrelated-feature.json', {'late_stage': ['完整保留', 3]})
        (parent / 'public/index.html').write_text('<p>原始页面</p>', encoding='utf-8')
        page = root / 'review-page'; page.mkdir()
        (page / 'pair.png').write_bytes(b'synthetic-Pair')
        pair_hash = pipeline.digest(page / 'pair.png')
        groups = groups or {'detail': ['Q1', 'Q2']}
        qids = [q for ids in groups.values() for q in ids]
        answer = dict(decision='按原图保留', source_pair_sha256=pair_hash, updated_at='2026-11-18T00:00:00Z')
        definitions = dict(schema='synthetic-review', sections=[], followup_sections=[dict(
            title='源图范围核查', image=dict(path='pair.png', sha256=pair_hash), questions=[dict(
                id=q, text='请核查 '+q, options=['按原图保留', '不同答复'],
                source_evidence=dict(pair_sha256=pair_hash)) for q in qids])],
            received_followup_feedback=dict(answers={'OLD': dict(decision='历史已应用')},
                                            status='historical', receipt={'unchanged': True}))
        reply = copy.deepcopy(definitions)
        for q in reply['followup_sections'][0]['questions']:
            q['answer'] = copy.deepcopy(answer)
        reply['browser_answer_snapshot'] = {q: copy.deepcopy(answer) for q in qids}
        definitions_path, reply_path = root / 'definitions.json', root / 'reply.json'
        pipeline.write(definitions_path, definitions)
        pipeline.write(reply_path, reply)
        source = root / 'source.json'; pipeline.write(source, {q: i + 10 for i, q in enumerate(qids)})
        catalog = dict(schema='cad_confirmed_hil_rule_catalog_v1', rules=[], bindings=[], history=[])
        if history:
            historical = root / 'history-proof.json'
            pipeline.write(historical, {'status': 'passed', 'question_id': 'OLD', 'native_applied': True})
            catalog['history'] = [dict(question_id='OLD', answer=dict(decision='历史已应用',
                source_pair_sha256=pair_hash), pair_sha256=pair_hash, rule_id='historic-owner',
                proofs=[dict(pipeline.pin(historical), assertions={'/status': 'passed', '/native_applied': True})],
                current_evidence=[dict(pipeline.pin(parent / 'public/data/graph.json'), assertions={'/source': '原图'})])]
        for rule_id, ids in groups.items():
            template = root / (rule_id + '-manifest.json')
            pipeline.write(template, dict(question_ids=ids, inputs=dict(source=pipeline.pin(source), answer_receipt={})))
            def command(args):
                return dict(script=pipeline.pin(native), args=args, cores=1)
            catalog['rules'].append(dict(id=rule_id, question_ids=ids, manifest_template=pipeline.pin(template),
                inputs=[pipeline.pin(source)], proof_filename='proof.json', publication_receipt='viewer/publication.json',
                native=command(['native', '--manifest', '{manifest}', '--output', '{stage_output}/native']),
                verify=command(['verify', '--native', '{native}', '--output', '{stage_output}']),
                publish=command(['publish', '--parent', '{parent_viewer}', '--proof', '{proof}', '--output', '{stage_output}/viewer']),
                publish_verify=command(['publish_verify', '--viewer', '{viewer}', '--output', '{stage_output}'])))
            catalog['bindings'].extend(dict(question_id=q, approved_answer=copy.deepcopy(answer),
                pair_sha256=pair_hash, rule_id=rule_id, reapply=True) for q in ids)
        catalog_path = root / 'catalog.json'; pipeline.write(catalog_path, catalog)
        config = dict(schema=pipeline.SCHEMA, catalog=pipeline.pin(catalog_path),
            baseline_registry=pipeline.pin(baseline), parent_viewer=str(parent), port=10638,
            parent_bindings=[pipeline.pin(parent / 'public/data/graph.json'),
                             pipeline.pin(parent / 'public/data/manifest.json')],
            intakes=[dict(id='fresh-answers', definitions=pipeline.pin(definitions_path),
                reply=pipeline.pin(reply_path), page_root=str(page), question_ids=qids)], test_workers=1)
        config_path = root / 'config.json'; pipeline.write(config_path, config)
        return dict(root=root, skills=skills, scripts=scripts, copied_pipeline=copied_pipeline,
                    parent=parent, source=source, definitions=definitions_path, reply=reply_path,
                    catalog=catalog, catalog_path=catalog_path, config=config, config_path=config_path,
                    answer=answer, qids=qids, native=native)

    @contextlib.contextmanager
    def environment(self, fixture):
        # Keep the genuine viewer intake module; only the temporary native skill
        # tree and child-process orchestrator path change for these tests.
        with (patch.object(pipeline, 'SKILLS', fixture['skills']),
              patch.object(pipeline, '__file__', str(fixture['copied_pipeline']))):
            yield

    def records(self, fixture):
        return [dict(question_id=q, explicit_answer=copy.deepcopy(fixture['answer']),
                     pair_sha256=fixture['answer']['source_pair_sha256'], intake_id='fresh-answers',
                     source_evidence={'scope': q}) for q in fixture['qids']]

    def repin(self, fixture):
        pipeline.write(fixture['catalog_path'], fixture['catalog'])
        fixture['config']['catalog'] = pipeline.pin(fixture['catalog_path'])
        fixture['config']['intakes'][0]['reply'] = pipeline.pin(fixture['reply'])
        pipeline.write(fixture['config_path'], fixture['config'])

    def test_resolution_groups_questions_once_and_preserves_verified_history(self):
        f = self.fixture()
        history = pipeline.verify_history(f['catalog'])
        original = copy.deepcopy((f['catalog'], history))
        resolved = pipeline.resolve(self.records(f), f['catalog'], history)
        self.assertEqual(resolved['applications'], {'detail': ['Q1', 'Q2']})
        self.assertEqual(len([r for r in resolved['records'] if r['question_id'] == 'OLD']), 1)
        self.assertEqual(resolved['new_conflicts'], [])
        self.assertEqual((f['catalog'], history), original)

    def test_history_requires_bound_proof_current_evidence_and_assertions(self):
        for failure in ('no_proofs', 'no_current', 'proof_bytes', 'current_bytes', 'assertion',
                        'no_proof_assertion', 'no_current_assertion'):
            f = self.fixture(); row = f['catalog']['history'][0]
            if failure == 'no_proofs': row['proofs'] = []
            elif failure == 'no_current': row['current_evidence'] = []
            elif failure == 'proof_bytes': Path(row['proofs'][0]['path']).write_bytes(b'changed')
            elif failure == 'current_bytes': Path(row['current_evidence'][0]['path']).write_bytes(b'changed')
            elif failure == 'assertion': row['proofs'][0]['assertions']['/status'] = 'not-passed'
            elif failure == 'no_proof_assertion': row['proofs'][0].pop('assertions')
            else: row['current_evidence'][0].pop('assertions')
            with self.subTest(failure=failure), self.assertRaises(ValueError): pipeline.verify_history(f['catalog'])

    def test_semantically_same_history_is_not_reasked_but_pair_change_is_conflict(self):
        f = self.fixture(); history = pipeline.verify_history(f['catalog'])
        answer = dict(history['OLD']['answer'], updated_at='new-time')
        record = dict(question_id='OLD', explicit_answer=answer,
                      pair_sha256=f['answer']['source_pair_sha256'], intake_id='fresh-answers')
        result = pipeline.resolve([record], f['catalog'], history)
        self.assertEqual(result['applications'], {})
        self.assertEqual(result['new_conflicts'], [])
        record['pair_sha256'] = 'f' * 64
        result = pipeline.resolve([record], f['catalog'], history)
        self.assertEqual(len(result['new_conflicts']), 1)
        self.assertEqual(result['new_conflicts'][0]['reason'], 'source_pair_changed_requires_new_qualification')
        self.assertEqual(history['OLD']['state'], 'previous_application_verified')

    def test_different_answer_comment_or_pair_creates_only_one_new_conflict(self):
        for change in ('decision', 'comment', 'pair'):
            f = self.fixture(); records = self.records(f)
            if change == 'decision': records[0]['explicit_answer']['decision'] = '不同答复'
            elif change == 'comment': records[0]['explicit_answer']['comment'] = '连接范围已变化'
            else: records[0]['pair_sha256'] = 'f' * 64
            result = pipeline.resolve(records, f['catalog'], pipeline.verify_history(f['catalog']))
            self.assertEqual(len(result['new_conflicts']), 1)
            self.assertEqual(result['new_conflicts'][0]['question_id'], 'Q1')
            self.assertEqual(result['applications'], {})
            rows = {r['question_id']: r for r in result['records']}
            self.assertEqual(rows['Q2']['state'], 'blocked_by_new_conflict')
            self.assertEqual(rows['OLD']['state'], 'previous_application_verified')

    def test_isolated_other_rule_runs_and_same_group_is_blocked_without_extra_question(self):
        f = self.fixture({'detail': ['Q1', 'Q2'], 'other': ['Q3']})
        reply = pipeline.load(f['reply'])
        reply['followup_sections'][0]['questions'][0]['answer']['decision'] = '不同答复'
        reply['browser_answer_snapshot']['Q1']['decision'] = '不同答复'
        pipeline.write(f['reply'], reply); self.repin(f)
        with self.environment(f): pipeline.prepare(f['config_path'], f['root'] / 'workflow')
        resolution = pipeline.load(f['root'] / 'workflow/resolution.json')
        self.assertEqual(resolution['applications'], {'other': ['Q3']})
        self.assertEqual(len(resolution['new_conflicts']), 1)
        jobs = pipeline.load(f['root'] / 'workflow/batch-manifest.json')['jobs']
        self.assertIn('other-native', [j['id'] for j in jobs])
        self.assertNotIn('detail-native', [j['id'] for j in jobs])

    def test_real_intake_prior_answer_conflict_is_archived_and_independent_rule_publishes(self):
        # Q1 has a received answer but no catalog application history. Its new
        # answer even agrees with the registered rule; the receipt conflict flag
        # must still prevent authorizing it and must block only its own cohort.
        f = self.fixture({'detail': ['Q1', 'Q2'], 'other': ['Q3']})
        definitions = pipeline.load(f['definitions'])
        prior = dict(f['answer'], decision='不同答复', updated_at='2026-11-17T00:00:00Z')
        definitions['received_followup_feedback']['answers']['Q1'] = prior
        definitions['received_followup_feedback']['received_pair_sha256_by_question'] = {
            'Q1': prior['source_pair_sha256']}
        page = Path(f['config']['intakes'][0]['page_root'])
        overview = page / 'overview.png'; overview.write_bytes(b'larger-source-overview')
        contexts = [dict(title='大范围原图', path='overview.png', sha256=pipeline.digest(overview), locators=[])]
        definitions['followup_sections'][0]['contexts'] = contexts
        reply = pipeline.load(f['reply']); reply['followup_sections'][0]['contexts'] = contexts
        pipeline.write(f['definitions'], definitions); pipeline.write(f['reply'], reply)
        f['config']['intakes'][0]['definitions'] = pipeline.pin(f['definitions'])
        self.repin(f)
        old_definitions = f['definitions'].read_bytes()
        workflow = f['root'] / 'workflow'
        with self.environment(f): result = pipeline.run(f['config_path'], workflow, cores=2)
        self.assertEqual(result['status'], 'published_with_new_conflicts')
        self.assertEqual(result['applied_this_run'], 1)
        self.assertEqual(len(result['new_conflicts']), 1)
        conflict = result['new_conflicts'][0]
        self.assertEqual(conflict['question_id'], 'Q1')
        self.assertEqual(conflict['reason'], 'decision_conflicts_with_previously_received_answer')
        self.assertEqual(conflict['prior_answer'], prior)
        intake = pipeline.load(workflow / 'intakes/fresh-answers/receipt.json')
        archived = next(r for r in intake['records'] if r['question_id'] == 'Q1')
        self.assertTrue(archived['conflicts_with_received_answer'])
        self.assertEqual(archived['prior_received_answer'], prior)
        self.assertNotIn('Q1', intake['native_technical_application_pending'])
        queue = pipeline.load(workflow / 'intakes/fresh-answers/review-queue.json')
        self.assertEqual(queue['received_followup_feedback']['answers']['Q1'], prior)
        # Only the unrelated, conflict-free cohort can reach a native owner.
        native_intake = pipeline.load(workflow / 'rule-intakes/other/receipt.json')
        self.assertEqual([r['question_id'] for r in native_intake['records']], ['Q3'])
        self.assertFalse((workflow / 'rule-intakes/detail').exists())
        self.assertEqual((workflow / 'rule-intakes/other/original-reply.json').read_bytes(), f['reply'].read_bytes())
        self.assertEqual(f['definitions'].read_bytes(), old_definitions)
        self.assertEqual(pipeline.load(Path(result['published_viewer']) / 'published.json'), {'Q3': 12})
        ledger = pipeline.load(result['application_ledger']['path'])
        rows = {r['question_id']: r for r in ledger['records']}
        self.assertEqual(rows['Q2']['state'], 'blocked_by_new_conflict')
        self.assertEqual(rows['Q3']['state'], 'native_applied_regressed_and_published')
        html = (workflow / 'new-conflicts.html').read_text('utf-8')
        self.assertIn('大范围原图', html)
        self.assertIn('<b>Q1</b>', html)
        self.assertNotIn('<b>Q2</b>', html)
        self.assertNotIn('<b>Q3</b>', html)
        self.assertEqual(len(list((workflow / 'conflict-assets').glob('*'))), 2)

    def test_duplicate_imported_question_rejected_and_not_merged_silently(self):
        f = self.fixture(); records = self.records(f)
        records.append(dict(records[0], intake_id='second-file'))
        with self.assertRaisesRegex(ValueError, 'imported twice'):
            pipeline.resolve(records, f['catalog'], pipeline.verify_history(f['catalog']))
        f['config']['intakes'].append(copy.deepcopy(f['config']['intakes'][0]))
        pipeline.write(f['config_path'], f['config'])
        with self.environment(f), self.assertRaisesRegex(ValueError, 'intake id'):
            pipeline.prepare(f['config_path'], f['root'] / 'workflow')

    def test_missing_handler_is_technical_failure_not_new_HIL(self):
        f = self.fixture(); f['catalog']['rules'] = []
        self.repin(f)
        with self.environment(f), self.assertRaisesRegex(ValueError, 'lacks executable registration'):
            pipeline.run(f['config_path'], f['root'] / 'workflow', cores=2)
        status = pipeline.load(f['root'] / 'workflow/status.json')
        self.assertEqual(status['status'], 'technical_failure')
        self.assertFalse((f['root'] / 'workflow/new-conflicts.json').exists())

    def test_reply_commands_are_data_and_commands_come_only_from_pinned_catalog(self):
        f = self.fixture()
        reply = pipeline.load(f['reply'])
        payload = 'UNTRUSTED_COMMAND_SHOULD_NEVER_RUN'
        reply['command'] = [sys.executable, '-c', payload]
        for q in reply['followup_sections'][0]['questions']:
            q['answer']['command'] = payload
            reply['browser_answer_snapshot'][q['id']]['command'] = payload
        pipeline.write(f['reply'], reply); self.repin(f)
        with self.environment(f): pipeline.prepare(f['config_path'], f['root'] / 'workflow')
        jobs = pipeline.load(f['root'] / 'workflow/batch-manifest.json')['jobs']
        self.assertNotIn(payload, json.dumps([j['command'] for j in jobs]))
        native = next(j for j in jobs if j['id'] == 'detail-native')
        self.assertEqual(native['command'][4], str(f['native']))
        self.assertIn(payload, (f['root'] / 'workflow/intakes/fresh-answers/original-reply.json').read_text('utf-8'))

    def test_second_publication_waits_for_first_independent_verification(self):
        f = self.fixture({'first': ['Q1'], 'second': ['Q2']})
        with self.environment(f): pipeline.prepare(f['config_path'], f['root'] / 'workflow')
        jobs = {j['id']: j for j in pipeline.load(f['root'] / 'workflow/batch-manifest.json')['jobs']}
        self.assertIn('first-publish-verify', jobs['second-publish']['depends_on'])
        self.assertIn('{stage_output:first-publish}/viewer', jobs['second-publish']['command'])

    def test_catalog_script_hash_remains_locked_after_prepare(self):
        f = self.fixture()
        with self.environment(f): pipeline.prepare(f['config_path'], f['root'] / 'workflow')
        f['native'].write_text("raise RuntimeError('must fail binding before execution')\n", encoding='utf-8')
        from pipeline_batch_runtime import run_manifest
        with self.assertRaisesRegex(ValueError, 'changed'):
            run_manifest(f['root'] / 'workflow/batch-manifest.json', f['root'] / 'workflow/batch', cores=2)

    def test_utf8_real_intake_archives_exact_originals_and_keeps_historical_answers(self):
        f = self.fixture(); original = f['definitions'].read_bytes(); reply = f['reply'].read_bytes()
        with self.environment(f): pipeline.prepare(f['config_path'], f['root'] / 'workflow')
        intake = f['root'] / 'workflow/intakes/fresh-answers'
        self.assertEqual((intake / 'original-definitions.json').read_bytes(), original)
        self.assertEqual((intake / 'original-reply.json').read_bytes(), reply)
        queue = pipeline.load(intake / 'review-queue.json')
        self.assertEqual(queue['received_followup_feedback']['answers']['OLD'], {'decision': '历史已应用'})
        self.assertEqual(queue['received_followup_feedback']['answers']['Q1']['decision'], '按原图保留')
        self.assertNotIn('\ufffd', (intake / 'receipt.json').read_text('utf-8'))

    def test_changed_trusted_inputs_are_not_accepted(self):
        for target in ('reply', 'catalog_path'):
            f = self.fixture(); f[target].write_bytes(b'changed')
            with self.subTest(target=target), self.environment(f), self.assertRaises(ValueError):
                pipeline.prepare(f['config_path'], f['root'] / 'workflow')

    def test_real_subprocess_prepare_run_finalize_closed_loop(self):
        f = self.fixture({'first': ['Q1'], 'second': ['Q2']})
        parent_before = pipeline.inventory(f['parent'])
        with self.environment(f):
            result = pipeline.run(f['config_path'], f['root'] / 'workflow', cores=2)
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['applied_this_run'], 2)
        self.assertEqual(result['verified_existing_applications'], 1)
        self.assertEqual(result['pending_technical_applications'], [])
        self.assertEqual(result['new_conflicts'], [])
        self.assertEqual(pipeline.inventory(f['parent']), parent_before)
        published = Path(result['published_viewer'])
        self.assertEqual(pipeline.load(published / 'published.json'), {'Q1': 10, 'Q2': 11})
        self.assertEqual((published / 'annotations/history.json').read_bytes(),
                         (f['parent'] / 'annotations/history.json').read_bytes())
        self.assertEqual((published / 'unrelated-feature.json').read_bytes(),
                         (f['parent'] / 'unrelated-feature.json').read_bytes())
        ledger = pipeline.load(result['application_ledger']['path'])
        rows = {r['question_id']: r for r in ledger['records']}
        self.assertEqual(rows['OLD']['state'], 'previous_application_verified')
        for qid in ('Q1', 'Q2'):
            self.assertEqual(rows[qid]['state'], 'native_applied_regressed_and_published')
            self.assertTrue(pipeline.checked(rows[qid]['native_proof']).is_file())
            self.assertEqual(pipeline.load(pipeline.checked(rows[qid]['verification']))['status'], 'passed')

    def test_regression_failure_is_technical_and_never_marks_answers_published(self):
        f = self.fixture()
        pipeline.write(f['skills'] / 'registry.json', {'features': []})
        with self.environment(f), self.assertRaisesRegex(ValueError, 'batch failed'):
            pipeline.run(f['config_path'], f['root'] / 'workflow', cores=2)
        status = pipeline.load(f['root'] / 'workflow/status.json')
        self.assertEqual(status['status'], 'technical_failure')
        self.assertFalse((f['root'] / 'workflow/batch/stages/finalize/artifacts/application-ledger.json').exists())
        self.assertEqual(pipeline.load(f['root'] / 'workflow/new-conflicts.json')['records'], [])

    def test_finalize_rejects_empty_or_mismatched_native_publication_and_verification(self):
        f = self.fixture()
        workflow = f['root'] / 'workflow'
        with self.environment(f): pipeline.run(f['config_path'], workflow, cores=2)
        stages = workflow / 'batch/stages'
        publication = stages / 'detail-publish/artifacts/viewer/publication.json'
        native = stages / 'detail-native/artifacts/native/proof.json'
        independent = stages / 'detail-publish-verify/artifacts/verification.json'
        native_verify = stages / 'detail-verify/artifacts/verification.json'
        attempts = [('empty_publication', publication, {}), ('empty_native', native, {}),
                    ('empty_verification', independent, {}),
                    ('bare_verification_flag', independent, {'status': 'passed'}),
                    ('wrong_publication_proof', publication,
                     dict(pipeline.load(publication), proof_sha256='0' * 64)),
                    ('failed_native_verification', native_verify, {'status': 'failed'})]
        for name, path, value in attempts:
            original = path.read_bytes()
            try:
                pipeline.write(path, value)
                with self.subTest(name=name), self.environment(f), self.assertRaises(ValueError):
                    pipeline.finalize(workflow, f['root'] / ('rejected-' + name))
            finally:
                path.write_bytes(original)

    def test_finalize_refuses_changed_annotations_and_historical_parent(self):
        f = self.fixture(); workflow = f['root'] / 'workflow'
        with self.environment(f): result = pipeline.run(f['config_path'], workflow, cores=2)
        published_annotation = Path(result['published_viewer']) / 'annotations/history.json'
        original = published_annotation.read_bytes()
        published_annotation.write_bytes(b'changed')
        with self.environment(f), self.assertRaisesRegex(ValueError, 'annotation history'):
            pipeline.finalize(workflow, f['root'] / 'rejected-annotations')
        published_annotation.write_bytes(original)
        (f['parent'] / 'annotations/history.json').write_bytes(b'changed parent')
        with self.environment(f), self.assertRaisesRegex(ValueError, 'parent payload'):
            pipeline.finalize(workflow, f['root'] / 'rejected-parent')

    def test_dynamic_manifest_receipt_locator_closed_loop_and_stage_boundary(self):
        f = self.fixture()
        locator = dict(manifest_path='viewer/public/data/manifest.json',
                       json_pointer='/reviewedDetailFeedback/receipt_path', relative_root='../..')
        f['catalog']['rules'][0]['publication_receipt'] = locator
        self.repin(f)
        workflow = f['root'] / 'workflow'
        with self.environment(f): result = pipeline.run(f['config_path'], workflow, cores=2)
        ledger = pipeline.load(result['application_ledger']['path'])
        row = next(r for r in ledger['records'] if r['question_id'] == 'Q1')
        self.assertEqual(Path(row['publication']['path']), Path(result['published_viewer']) / 'publication.json')
        manifest_path = Path(result['published_viewer']) / 'public/data/manifest.json'
        manifest = pipeline.load(manifest_path)
        manifest['reviewedDetailFeedback']['receipt_path'] = '../../../outside-stage.json'
        pipeline.write(manifest_path, manifest)
        with self.environment(f), self.assertRaisesRegex(ValueError, 'outside stage'):
            pipeline.finalize(workflow, f['root'] / 'rejected-locator')

    def test_independent_native_verification_cannot_mutate_proof_then_claim_success(self):
        f = self.fixture()
        proof = f['root'] / 'native-proof.json'; pipeline.write(proof, {'source': '原图'})
        result = f['root'] / 'verification.json'
        code = "from pathlib import Path;import sys;Path(sys.argv[1]).write_bytes(b'changed')"
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = pipeline.main(['_verify-owner', '--proof', str(proof),
                '--receipt-output', str(result), '--', sys.executable, '-B', '-c', code, str(proof)])
        self.assertEqual(exit_code, 1)
        self.assertFalse(result.exists())


if __name__ == '__main__':
    unittest.main()
