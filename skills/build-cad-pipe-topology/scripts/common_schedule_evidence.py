"""Verify an exact native-source phrase common to all supplied candidate profiles.

This produces reference evidence only: it never selects a variant, identifies an
installed device, verifies a physical port, or changes topology.
"""
from collections import Counter


def common_phrase(profiles, candidate_ids, doc, phrase):
    if not isinstance(phrase, str) or not phrase or '\ufffd' in phrase:
        raise ValueError('readable phrase required')
    if not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError('nonempty distinct candidate profiles required')
    counts = Counter(p['profile_id'] for p in profiles)
    lookup = {p['profile_id']: p for p in profiles}
    if any(counts[c] != 1 for c in candidate_ids):
        raise ValueError('missing or duplicate candidate profile')
    witnesses = []
    for candidate in sorted(candidate_ids):
        prop = lookup[candidate].get('properties', {}).get('requirements', {})
        sources = prop.get('source', {}).get('entities', [])
        matches = [e for e in sources if phrase in str(e.get('text', ''))]
        if not matches:
            return {'status': 'not_common_or_missing_evidence', 'phrase': phrase,
                    'candidate_profiles': sorted(candidate_ids), 'witnesses': [],
                    'instance_connection_verified': False}
        for match in matches:
            entity = doc.entitydb.get(match.get('handle'))
            if entity is None or not entity.is_alive or entity.dxftype() not in ('TEXT', 'MTEXT'):
                raise ValueError('native source text missing')
            if entity.plain_text() != match['text']:
                raise ValueError('native source text changed')
            witnesses.append({'candidate_profile': candidate, 'source_handle': entity.dxf.handle,
                              'source_text': entity.plain_text()})
    return {'status': 'common_candidate_reference_only', 'phrase': phrase,
            'candidate_profiles': sorted(candidate_ids), 'witnesses': witnesses,
            'instance_connection_verified': False}
