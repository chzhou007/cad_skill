"""Receive explicit version-bound expert answers without adopting graph values.

The original questions and receipts stay intact. Native technical application
is a separate stage; receiving an answer is never whole-drawing acceptance.
"""
import argparse, copy, hashlib, json
from pathlib import Path
from current_source_review_queue import questions, queue_summary, received, checked
from review_page_preflight import validate_dataset, text

MODE = 'version_bound_current_review_answer_intake_v1'


def load(path):
    raw = Path(path).read_text(encoding='utf-8-sig').strip()
    if raw.startswith('window.REVIEW_CASES = '):
        raw = raw.removeprefix('window.REVIEW_CASES = ').removesuffix(';')
    return json.loads(raw)


def receive(existing, reply, page_root, question_ids, archive_conflicting_prior=False):
    if not isinstance(archive_conflicting_prior, bool):
        raise ValueError('archive_conflicting_prior must be an explicit boolean')
    validate_dataset(existing, page_root)
    before = copy.deepcopy(existing)
    definitions = {q['id']: (s, q) for s, q in questions(existing)}
    exported = [(s, q) for s, q in questions(reply)]
    if len({q['id'] for s, q in exported}) != len(exported):
        raise ValueError('duplicate exported question identity')
    by_id = {q['id']: (s, q) for s, q in exported}
    if not question_ids or len(set(question_ids)) != len(question_ids):
        raise ValueError('explicit unique question identities required')
    if existing.get('schema') != reply.get('schema'):
        raise ValueError('review schema changed')
    result = copy.deepcopy(existing)
    receipt = result.setdefault('received_followup_feedback', {})
    answers = receipt.setdefault('answers', {})
    pairs = receipt.setdefault('received_pair_sha256_by_question', {})
    prior = received(existing)
    records = []
    for qid in question_ids:
        if qid not in definitions or qid not in by_id:
            raise ValueError('current or exported question missing: ' + qid)
        section, definition = definitions[qid]
        other, question = by_id[qid]
        if (section['image'] != other.get('image')
                or section.get('contexts', []) != other.get('contexts', [])
                or any(question.get(k) != definition.get(k)
                       for k in ('id', 'text', 'options', 'source_evidence'))):
            raise ValueError('question, source extent or original Pair changed: ' + qid)
        answer = question.get('answer', {})
        if answer != reply.get('browser_answer_snapshot', {}).get(qid):
            raise ValueError('explicit question answer and browser snapshot disagree: ' + qid)
        if (not isinstance(answer, dict) or answer.get('decision') not in definition['options']
                or answer.get('source_pair_sha256') != section['image']['sha256']
                or not isinstance(answer.get('updated_at'), str) or not answer['updated_at']):
            raise ValueError('explicit version-bound answer missing: ' + qid)
        for field in ('decision', 'comment'):
            if field in answer:
                text(answer[field], qid + '.' + field)
        conflicting_prior = qid in prior and prior[qid] != answer
        if conflicting_prior and not archive_conflicting_prior:
            raise ValueError('existing answer differs; explicit correction history required: ' + qid)
        binding = existing.get('current_review_queue_sources', {}).get(qid)
        if binding:
            checked(binding['qualification'])
            for spec in binding['source_inputs']:
                checked(spec)
        record = dict(question_id=qid, question=definition['text'],
            options=copy.deepcopy(definition['options']), source_evidence=copy.deepcopy(definition.get('source_evidence', {})),
            explicit_answer=copy.deepcopy(answer), pair_sha256=section['image']['sha256'],
            status='answer_received_native_technical_application_pending',
            current_queue_source_binding_checked=bool(binding), native_application_proved=False)
        if conflicting_prior:
            # A correction candidate is evidence for a new conflict, never an
            # update to prior authority. produce archives this record together
            # with the exact original reply. The strict native-owner replay
            # remains the default and therefore cannot authorize this receipt.
            record.update(status='conflicting_received_answer_archived_not_authorized',
                          conflicts_with_received_answer=True,
                          prior_received_answer=copy.deepcopy(prior[qid]))
        else:
            answers[qid] = copy.deepcopy(answer)
            pairs[qid] = section['image']['sha256']
        records.append(record)
    receipt['count'] = len(answers)
    # The old receipt, old status and old answers remain available verbatim.
    for qid, answer in before.get('received_followup_feedback', {}).get('answers', {}).items():
        if answers[qid] != answer:
            raise ValueError('old expert answer changed')
    if any(result.get(k) != before.get(k) for k in ('sections', 'followup_sections',
            'received_feedback', 'received_compound_lane_feedback', 'review_workflow')):
        raise ValueError('old questions, source scopes or independent receipts changed')
    if existing != before:
        raise ValueError('caller review data mutated')
    report = dict(mode=MODE, records=records, queue=queue_summary(result),
        answers_received=len(records), graph_mutated=False, physical_values_assigned=0,
        native_technical_application_pending=[r['question_id'] for r in records
            if not r.get('conflicts_with_received_answer')], human_accepted=False)
    conflicts = [r['question_id'] for r in records if r.get('conflicts_with_received_answer')]
    if conflicts:
        report['conflicting_received_question_ids'] = conflicts
    return result, report


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def produce(existing, reply, page_root, question_ids, output, archive_conflicting_prior=False):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    pins = {k: dict(path=str(Path(p).resolve()), sha256=sha(p))
            for k, p in [('definitions', existing), ('reply', reply)]}
    data, receipt = receive(load(existing), load(reply), page_root, question_ids,
                            archive_conflicting_prior=archive_conflicting_prior)
    if any(sha(v['path']) != v['sha256'] for v in pins.values()):
        raise ValueError('review input changed during answer intake')
    output.mkdir(parents=True)
    archived_inputs = {}
    for key, name, path in [('definitions', 'original-definitions', existing), ('reply', 'original-reply', reply)]:
        archived = output / (name + Path(path).suffix)
        archived.write_bytes(Path(path).read_bytes())
        if sha(archived) != pins[key]['sha256']:
            raise ValueError('archived review input differs')
        archived_inputs[key] = dict(path=str(archived.resolve()), sha256=sha(archived))
    target = output / 'review-queue.json'
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    receipt.update(inputs=archived_inputs, received_from=pins,
                   implementation_sha256=sha(__file__), output_sha256=sha(target))
    (output / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return receipt


def main():
    parser = argparse.ArgumentParser()
    for key in ('existing', 'reply', 'page-root', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--question-id', action='append', required=True)
    parser.add_argument('--archive-conflicting-prior', action='store_true')
    args = parser.parse_args()
    result = produce(args.existing, args.reply, args.page_root, args.question_id, args.output,
                     archive_conflicting_prior=args.archive_conflicting_prior)
    print(json.dumps(dict(status=MODE, received=result['answers_received'],
        pending_answers=len(result['queue']['pending_question_ids']),
        native_application_pending=bool(result['native_technical_application_pending'])), ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
