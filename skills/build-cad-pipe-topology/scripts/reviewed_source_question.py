"""Bind an explicit source/graph Pair answer without interpreting report prose."""
from confirm_crossview_paths import load, sha


def bind_question(paths, policy):
    for key, path in paths.items():
        if sha(path) != policy['inputs'][key]['sha256']:
            raise ValueError('reviewed source input changed: ' + key)
    raw, definitions, receipt = (load(paths[k]) for k in ('reply', 'definitions', 'receipt'))
    if receipt['input']['sha256'] != sha(paths['reply']):
        raise ValueError('raw response differs from validated archive')
    def find(document):
        matches = [(q, section['image']) for group in ('sections', 'followup_sections')
                   for section in document[group] for q in section['questions'] if q['id'] == policy['question_id']]
        if len(matches) != 1:
            raise ValueError('reviewed question is missing or duplicated')
        return matches[0]
    question, image = find(raw)
    definition, original_image = find(definitions)
    if image != original_image or any(question.get(k) != definition.get(k) for k in ('text', 'options', 'source_evidence')):
        raise ValueError('reviewed question or Pair scope changed')
    archived = [r for r in receipt['records'] if r['question_id'] == question['id']]
    answer = question.get('answer', {})
    if (len(archived) != 1 or archived[0]['explicit_answer'] != answer
            or answer.get('decision') not in question['options']):
        raise ValueError('explicit validated answer missing')
    evidence = question['source_evidence']
    if (archived[0]['source_evidence'] != evidence or archived[0]['question'] != question['text']
            or archived[0]['options'] != question['options'] or archived[0]['pair_sha256'] != image['sha256']):
        raise ValueError('validated question scope differs from the original reply')
    if (evidence['source_sha256'] != sha(paths['source']) or evidence['graph_sha256'] != sha(paths['graph'])
            or image['sha256'] != sha(paths['pair']) or evidence['pair_sha256'] != sha(paths['pair'])
            or answer.get('source_pair_sha256') != sha(paths['pair'])):
        raise ValueError('answer source, graph or original Pair differs')
    for key, field in [('overview', 'overview_sha256'), ('native_context', 'native_context_audit_sha256')]:
        if key in paths and evidence.get(field) != sha(paths[key]):
            raise ValueError('reviewed original context differs: ' + key)
    return question
