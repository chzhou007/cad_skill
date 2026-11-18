"""Inventory stored attribute records, distinct from edges and verification.

Multiple plan scopes can belong to one mixed edge. Evidence sidecars update
proof provenance; they must not be counted again as additional plan scopes.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

PLAN_FIELDS = {
    'batch_plan_attribute_scopes': 'object',
    'cross_view_attributes': 'object',
    'anchored_floor_main_attributes': 'object',
    'external_feed_plan_attributes': 'object',
    'network_named_lower_plan_attributes': 'object',
    'plan_segment_attributes': 'array',
}
AXIS_FIELDS = {'axis_riser_attributes': 'array'}
EVIDENCE_FIELDS = {'current_plan_scope_evidence': 'object', 'current_floor_plan_scope_evidence': 'object', 'current_named_prefix_source_evidence': 'object'}


def inventory(graph):
    if not isinstance(graph, dict) or not isinstance(graph.get('edges'), list):
        raise ValueError('Graph edge array required')
    seen, records = set(), []
    for edge in graph['edges']:
        eid = edge.get('edge_id') if isinstance(edge, dict) else None
        if not isinstance(eid, str) or not eid or eid in seen:
            raise ValueError('Unique stable edge IDs required')
        seen.add(eid)
        for category, fields in [('plan', PLAN_FIELDS), ('axis', AXIS_FIELDS), ('evidence', EVIDENCE_FIELDS)]:
            for field, shape in fields.items():
                value = edge.get(field)
                if value is None:
                    continue
                if shape == 'object':
                    if not isinstance(value, dict) or not value:
                        raise ValueError('Nonempty attribute object required: '+eid+'/'+field)
                    values = [value]
                else:
                    if not isinstance(value, list) or any(not isinstance(row, dict) or not row for row in value):
                        raise ValueError('Attribute object array required: '+eid+'/'+field)
                    values = value
                for ordinal, row in enumerate(values):
                    encoded = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
                    records.append(dict(category=category, edge_id=eid, field=field, ordinal=ordinal,
                        payload_sha256=hashlib.sha256(encoded).hexdigest()))
    records.sort(key=lambda r: (r['category'], r['edge_id'], r['field'], r['ordinal']))
    result = dict(status='structural_attribute_record_inventory_not_source_or_physical_acceptance',
        graph_edges=len(seen), field_shapes=dict(plan=PLAN_FIELDS, axis=AXIS_FIELDS, evidence=EVIDENCE_FIELDS), records=records)
    for category in ('plan', 'axis', 'evidence'):
        chosen = [row for row in records if row['category'] == category]
        result[category] = dict(records=len(chosen), edges=len({row['edge_id'] for row in chosen}),
            by_field=dict(Counter(row['field'] for row in chosen)))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    raw = args.graph.read_bytes()
    result = inventory(json.loads(raw.decode('utf-8-sig')))
    result['source_graph'] = dict(path=str(args.graph.resolve()), sha256=hashlib.sha256(raw).hexdigest())
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print({category: result[category] for category in ('plan', 'axis', 'evidence')})


if __name__ == '__main__':
    main()
