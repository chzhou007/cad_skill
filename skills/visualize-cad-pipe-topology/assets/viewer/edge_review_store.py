"""User attribute authority and notes; never rewrite CAD graph attributes."""
import copy
import math
from hil_server import ReviewError, now, safe_text


def edge_note(edit, history=(), edge_id=None):
    """Explicit new notes (including clears) win; recover old invisible notes."""
    if 'note' in edit:
        return edit['note']
    for field in ('length', 'reviewed'):
        if edit.get(field, {}).get('note'):
            return edit[field]['note']
    for row in reversed(history):
        if row.get('edgeId') == edge_id and row.get('note'):
            return row['note']
    return ''


def save_edge_review(store, payload):
    with store.lock:
        doc = store.read()
        if payload.get('datasetId') != store.dataset:
            raise ReviewError('Dataset changed; reload before editing.', 409)
        if payload.get('baseRevision') != doc['revision']:
            raise ReviewError('Another window saved changes. Reload before saving.', 409)
        key = payload.get('edgeId')
        if key not in store.edge_ids:
            raise ReviewError('Unknown edge')
        action = payload.get('action')
        if action not in ('setLength', 'resetLength', 'setDiameter', 'resetDiameter', 'saveNote', 'review', 'unreview'):
            raise ReviewError('Unknown edge action')
        result = copy.deepcopy(doc)
        edit = result.setdefault('edgeEdits', {}).setdefault(key, {})
        before = copy.deepcopy(edit)
        author = safe_text(payload.get('author', ''), 200).strip()
        note = safe_text(payload.get('note', edge_note(edit, doc.get('edgeEditHistory', []), key)), 2000)
        if action == 'setLength':
            value = payload.get('lengthM')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ReviewError('Length must be a finite positive number in metres.')
            edit['length'] = {'valueM': value, 'unit': 'm', 'source': 'manual_user_override',
                              'author': author, 'note': note, 'updatedAt': now()}
            # An attribute edit does not certify the edge or its mapping.
            edit.pop('reviewed', None)
        elif action == 'resetLength':
            edit.pop('length', None)
            edit.pop('reviewed', None)
        elif action in ('setDiameter', 'resetDiameter'):
            scope = payload.get('diameterScope')
            if scope not in ('horizontal', 'vertical', 'whole_edge'):
                raise ReviewError('Diameter scope must be horizontal, vertical or whole_edge.')
            diameters = edit.setdefault('diameters', {})
            if action == 'setDiameter':
                value = payload.get('diameterMm')
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                    raise ReviewError('Diameter must be a finite positive number in millimetres.')
                diameters[scope] = {'nominalMm': value, 'unit': 'mm', 'scope': scope,
                    'source': 'manual_user_override', 'author': author, 'note': note, 'updatedAt': now()}
            else:
                diameters.pop(scope, None)
            edit.pop('reviewed', None)
        elif action == 'saveNote':
            edit.pop('reviewed', None)
        elif action == 'review':
            edit['reviewed'] = {'author': author, 'note': note, 'updatedAt': now()}
        else:
            edit.pop('reviewed', None)
        edit['note'] = note
        edit['noteAuthor'] = author
        edit['noteUpdatedAt'] = now()
        result.setdefault('edgeEditHistory', []).append({'edgeId': key, 'action': action,
            'before': before, 'after': copy.deepcopy(edit), 'author': author, 'note': note, 'at': now()})
        if result.get('confirmation'):
            result.setdefault('historicalConfirmations', []).append({**result['confirmation'],
                'invalidatedAt': now(), 'reason': 'edge_attribute_or_review_changed', 'edgeId': key})
        result['confirmation'] = None
        result['revision'] += 1
        result['updatedAt'] = now()
        return store.persist(result)
