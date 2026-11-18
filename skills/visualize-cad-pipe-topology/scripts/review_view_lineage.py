"""Read current sideview lineage before treating historical candidates as HIL.

This does not reconstruct a graph or replay CAD. Its input graph must come from
the topology owner's source gate; equivalence, ownership and main identity are
separate facts. Original questions, answers and local graphs remain unchanged.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def unique(rows, key, label):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError('Duplicate ' + label)
        result[value] = row
    return result


def audit(graph, review, expected_source_sha256):
    if not isinstance(expected_source_sha256, str) or not re.fullmatch('[0-9a-f]{64}', expected_source_sha256):
        raise ValueError('Exact source SHA256 required')
    nodes = unique(graph['nodes'], 'node_id', 'node ID')
    edges = unique(graph['edges'], 'edge_id', 'edge ID')
    history = graph.get('sourceDetailComparison', {})
    candidates = history.get('pairs', [])
    if candidates and history.get('source_sha256') != expected_source_sha256:
        raise ValueError('Historical candidates use another source')
    root = graph.get('confirmedSideviewCanonicalization')
    records = []
    if root:
        if root.get('source_sha256') != expected_source_sha256:
            raise ValueError('Canonical sideview uses another source')
        canonical = {}
        for row in root['records']:
            key = (row['abbreviated_edge'], row['system'])
            if key in canonical:
                raise ValueError('Duplicate canonical sideview relation')
            canonical[key] = row
        retired_edges = unique(root['representation_only_edges'], 'edge_id', 'retired edge')
        retired_nodes = unique(root['representation_only_nodes'], 'node_id', 'retired node')
    else:
        canonical, retired_edges, retired_nodes = {}, {}, {}
    ownership = graph.get('sourceSideviewEquipmentOwnership', {})
    if ownership and ownership.get('source_sha256') != expected_source_sha256:
        raise ValueError('Current equipment ownership uses another source')
    owners = {}
    for row in ownership.get('records', []):
        key = (row['edge_id'], row['system'])
        if key in owners:
            raise ValueError('Duplicate current equipment owner')
        owners[key] = row
    questions = {}
    for section in review.get('sections', []):
        for q in section.get('questions', []):
            if q['id'] in questions:
                raise ValueError('Duplicate original question')
            questions[q['id']] = (q, section['image']['sha256'])
    answers = review.get('received_feedback', {}).get('answers', {})
    reopened = set(review.get('review_workflow', {}).get('reopened_question_ids', []))
    seen = set()
    for old in candidates:
        key = (old['upper_edge'], old['system'])
        if key in seen:
            raise ValueError('Duplicate historical candidate')
        seen.add(key)
        row = canonical.get(key)
        if row is None:
            records.append(dict(historical_upper_edge=old['upper_edge'], system=old['system'],
                                status='candidate_not_adopted_current_equivalence_unknown',
                                historical_target_currently_present=old['upper_edge'] in edges,
                                sideview_relation_proved=False, new_HIL_question_created=False))
            continue
        qid = row['question_id']
        if qid in reopened:
            records.append(dict(historical_upper_edge=old['upper_edge'], system=old['system'],
                                original_question_id=qid, status='relation_reopened_source_reconciliation_required',
                                sideview_relation_proved=False, rebuilt_graph_human_accepted=False,
                                prior_answer_retained_as_history=True, new_HIL_question_created=False))
            continue
        if qid not in questions or answers.get(qid) != row['answer']:
            raise ValueError('Current received answer differs from adopted relation: ' + qid)
        question, pair_sha = questions[qid]
        if row['answer'].get('decision') != '对应同一组管路' or row['answer']['decision'] not in question['options']:
            raise ValueError('Explicit positive sideview answer required')
        if row['pair_sha256'] != pair_sha:
            raise ValueError('Original Pair differs from adopted relation')
        eid = root['edge_aliases'].get(old['upper_edge'])
        if eid != row['canonical_edge'] or eid not in edges:
            raise ValueError('Current canonical edge missing or alias changed')
        if old['upper_edge'] in edges or old['upper_terminal'] in nodes:
            raise ValueError('Retired abbreviated representation is still active')
        if old['upper_edge'] not in retired_edges or old['upper_terminal'] not in retired_nodes:
            raise ValueError('Original abbreviated snapshots were lost')
        if old['upper_pipe'] not in retired_edges[old['upper_edge']].get('source_handles', []):
            raise ValueError('Retired snapshot has another source pipe')
        tee = old['detail_tee']
        edge = edges[eid]
        ends = {edge['start_node_id'], edge['end_node_id']}
        if row['verified_detail_tee']['tee'] != tee or tee not in nodes or tee not in ends or edge['system'] != old['system']:
            raise ValueError('Current detail T or service differs')
        owner = owners.get((eid, old['system']))
        if owner:
            did = owner['equipment_id']
            if (owner.get('source_sha256') != expected_source_sha256 or did not in nodes or did not in ends
                    or owner.get('original_canonical_interface_id') != row['canonical_interface']):
                raise ValueError('Current canonical equipment owner disagrees with endpoints')
        else:
            did = None
            if row['canonical_interface'] not in nodes or row['canonical_interface'] not in ends:
                raise ValueError('Unowned current canonical interface missing')
        records.append(dict(historical_upper_edge=old['upper_edge'], historical_upper_terminal=old['upper_terminal'],
                            system=old['system'], status='sideview_confirmed_owner_known' if did else 'sideview_confirmed_owner_unresolved',
                            current_canonical_edge=eid, current_detail_T=tee, equipment_owner=did,
                            original_question_id=qid, original_pair_sha256=pair_sha,
                            sideview_relation_proved=True, repeated_sideview_question_needed=False,
                            projected_main_identity=row.get('projected_main_identity', 'unknown'),
                            whole_main_correspondence_proven=False, physical_ports_verified=False,
                            installed_length_mm=None, rebuilt_graph_human_accepted=False))
    adopted = [r for r in records if r['sideview_relation_proved']]
    return dict(status='historical_candidates_reconciled_against_current_sideview_lineage_not_CAD_replay',
                source_sha256=expected_source_sha256, historical_candidates=len(records),
                adopted_sideview_relations=len(adopted), owner_known=sum(r['equipment_owner'] is not None for r in adopted),
                owner_unresolved=sum(r['equipment_owner'] is None for r in adopted),
                not_adopted_candidates=len(records)-len(adopted), records=records,
                explicitly_reopened_relations=sum(r['status']=='relation_reopened_source_reconciliation_required' for r in records),
                native_source_replay=False, local_graphs_modified=False, questions_or_answers_modified=False,
                new_HIL_questions=0, human_accepted=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', type=Path, required=True)
    parser.add_argument('--graph-sha256', required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Retain previous evidence; use a new output path')
    raw = args.graph.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.graph_sha256:
        raise ValueError('Current graph SHA256 differs')
    text = args.review.read_text('utf-8-sig')
    if text.startswith('window.REVIEW_CASES = '):
        text = text.removeprefix('window.REVIEW_CASES = ').strip().removesuffix(';')
    result = audit(json.loads(raw.decode('utf-8-sig')), json.loads(text), args.source_sha256)
    result['current_graph'] = dict(path=str(args.graph.resolve()), sha256=args.graph_sha256)
    result['review_sha256'] = hashlib.sha256(args.review.read_bytes()).hexdigest()
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
