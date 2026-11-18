"""Atomic restoration of a same-dataset expert backup, including manual values."""
import copy
import hashlib
import json
import math
from hil_server import ReviewError, now, safe_text


def checked_edit(raw):
    if not isinstance(raw, dict):
        raise ReviewError('Invalid edge edit in backup')
    edit = copy.deepcopy(raw)
    for key, maximum in [('note', 2000), ('noteAuthor', 200), ('noteUpdatedAt', 200)]:
        if key in edit:
            safe_text(edit[key], maximum)
    for field, number, unit in [('length', 'valueM', 'm'), ('diameters', 'nominalMm', 'mm'), ('reviewed', None, None)]:
        if field not in edit:
            continue
        items = edit[field]
        if not isinstance(items, dict):
            raise ReviewError('Invalid attribute in backup')
        if field == 'diameters':
            if set(items) - {'horizontal', 'vertical', 'whole_edge'}:
                raise ReviewError('Invalid diameter scope in backup')
            rows = list(items.items())
        else:
            rows = [(None, items)]
        for scope, row in rows:
            if not isinstance(row, dict):
                raise ReviewError('Invalid attribute in backup')
            if number:
                value = row.get(number)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                    raise ReviewError('Backup lengths and diameters must be finite positive numbers')
                if row.get('unit') != unit or row.get('source') != 'manual_user_override':
                    raise ReviewError('Invalid manual attribute unit or source in backup')
                if scope is not None and row.get('scope') != scope:
                    raise ReviewError('Diameter scope differs in backup')
            for key, maximum in [('note', 2000), ('author', 200), ('updatedAt', 200)]:
                if key in row:
                    safe_text(row[key], maximum)
    return edit


def _list(value, name, maximum=100000):
    if not isinstance(value, list) or len(value) > maximum or any(not isinstance(x, dict) for x in value):
        raise ReviewError('Invalid '+name+' in backup')
    return copy.deepcopy(value)


def _unique(rows):
    seen = set()
    result = []
    for row in rows:
        key = json.dumps(row, sort_keys=True, ensure_ascii=True, allow_nan=False)
        if key not in seen:
            seen.add(key)
            result.append(row)
    return result


def restore_backup(store, payload):
    with store.lock:
        current = store.read()
        if payload.get('baseRevision') != current['revision']:
            raise ReviewError('Review changed; reload before restoring a backup', 409)
        backup = copy.deepcopy(payload.get('document'))
        if not isinstance(backup, dict) or backup.get('datasetId') != store.dataset:
            raise ReviewError('Backup belongs to another dataset', 409)
        if backup.get('schemaVersion') != 1:
            raise ReviewError('Unsupported backup schema')
        # Validate all content before the first disk write. Backup revisions must
        # remain intact so their expert responses keep their original bindings.
        json.dumps(backup, allow_nan=False)
        errors = _list(backup.get('errors'), 'issues', 10000)
        retired = backup.get('retiredIssues', {})
        if not isinstance(retired, dict) or len(retired) > 10000:
            raise ReviewError('Invalid retired issues in backup')
        issues = errors + list(retired.values())
        for issue in issues:
            if not isinstance(issue, dict) or not isinstance(issue.get('issueRevision'), int) or isinstance(issue['issueRevision'], bool) or issue['issueRevision'] < 1:
                raise ReviewError('Invalid issue revision in backup')
            for key in ('createdAt', 'updatedAt', 'label'):
                safe_text(issue.get(key), 200)
        baseline = {'datasetId': store.dataset, 'errors': errors, 'retiredIssues': retired}
        checked = store.validate(baseline, baseline)
        for key, issue in retired.items():
            if not isinstance(issue, dict) or key != issue.get('id'):
                raise ReviewError('Invalid retired issue ID in backup')
            store.validate({'datasetId': store.dataset, 'errors': [issue]}, baseline)
        responses = _list(backup.get('historicalResponses', []), 'historical responses')
        for issue in issues:
            responses.extend(_list(issue.get('expertResponses', []), 'expert responses'))
        for response in responses:
            for key in ('responseId', 'datasetId', 'issueId', 'expertName', 'verdict', 'reason', 'expectedConnection', 'suggestion'):
                safe_text(response.get(key, ''), 20000)
            if not all(response.get(k) for k in ('responseId', 'datasetId', 'issueId')) or not isinstance(response.get('issueRevision'), int):
                raise ReviewError('Invalid expert response binding in backup')
        edits = backup.get('edgeEdits', {})
        if not isinstance(edits, dict) or set(edits) - store.edge_ids:
            raise ReviewError('Backup attributes reference unknown edges')
        edits = {key: checked_edit(value) for key, value in edits.items()}
        history = _list(backup.get('edgeEditHistory', []), 'attribute history')
        for row in history:
            safe_text(row.get('edgeId', ''), 200)
            for key in ('before', 'after'):
                if key in row:
                    checked_edit(row[key])
        result = copy.deepcopy(current)
        result['errors'] = checked
        result['retiredIssues'] = {**current.get('retiredIssues', {}), **retired}
        active = {e['id'] for e in checked}
        result['retiredIssues'].update({e['id']: e for e in current['errors'] if e['id'] not in active})
        result['historicalResponses'] = _unique(current.get('historicalResponses', []) + backup.get('historicalResponses', []))
        result['edgeEdits'] = edits
        result['edgeEditHistory'] = _unique(current.get('edgeEditHistory', []) + history)
        result['historicalConfirmations'] = _unique(current.get('historicalConfirmations', []) + _list(backup.get('historicalConfirmations', []), 'confirmation history'))
        for confirmation in (current.get('confirmation'), backup.get('confirmation')):
            if confirmation:
                result['historicalConfirmations'].append({**confirmation, 'invalidatedAt': now(), 'reason': 'backup_restored_requires_new_confirmation'})
        result['confirmation'] = None
        result.setdefault('backupRestoreHistory', []).append({'at': now(), 'sourceRevision': backup.get('revision'),
            'previousRevision': current['revision'], 'sha256': hashlib.sha256(json.dumps(backup, sort_keys=True).encode()).hexdigest()})
        result['revision'] = current['revision'] + 1
        result['updatedAt'] = now()
        return store.persist(result)
