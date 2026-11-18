"""Verify explicitly selected native floor/elevation datum markers.

This reports source annotation and datum differences only. It neither assigns
floors to remote isometric geometry nor establishes any pipe length or port.
"""
import argparse
import hashlib
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from source_readability import read_source

_FLOORS = {'一层': 1, '二层': 2, '三层': 3, '四层': 4, '五层': 5,
           '六层': 6, '七层': 7, '八层': 8, '九层': 9, '十层': 10}


def floor_number(text):
    if text in _FLOORS:
        return _FLOORS[text]
    match = re.fullmatch(r'([1-9]\d*)F', text, flags=re.I)
    return int(match.group(1)) if match else None


def elevation_value(text):
    match = re.fullmatch(r'([+\-±]?)(\d+\.\d{3})', text.strip())
    if not match:
        raise ValueError('unsupported elevation text')
    value = Decimal(match.group(2))
    if match.group(1) == '±' and value != 0:
        raise ValueError('plus-minus is only accepted for zero datum')
    return -value if match.group(1) == '-' else value


def _point(entity, attr):
    v = getattr(entity.dxf, attr)
    return (float(v.x), float(v.y))


def _close(a, b, tol):
    return math.dist(a, b) <= tol


def verify(doc, policy, source_sha256, tolerance=0.05):
    if policy.get('source_sha256') != source_sha256 or not re.fullmatch(r'[0-9a-f]{64}', source_sha256):
        raise ValueError('source hash mismatch')
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError('invalid tolerance')
    rows = policy['markers']; seen = set(); levels = []
    for r in rows:
        roles = ('floor_text', 'elevation_text', 'baseline', 'left_arm', 'right_arm', 'leader')
        ids = [r[k] for k in roles]
        if len(set(ids)) != len(ids) or set(ids) & seen:
            raise ValueError('source marker handles must be unique')
        seen.update(ids)
        entities = [doc.entitydb.get(h) for h in ids]
        if any(e is None for e in entities) or [e.dxftype() for e in entities] != ['TEXT', 'TEXT', 'LINE', 'LINE', 'LINE', 'LINE']:
            raise ValueError('source marker entity mismatch')
        ft, et, baseline, left, right, leader = entities
        if any(e.dxf.layer != r['annotation_layer'] for e in (ft, et, left, right, leader)) or baseline.dxf.layer != r['baseline_layer']:
            raise ValueError('source marker layer mismatch')
        floor_text, elev_text = ft.plain_text(), et.plain_text()
        floor = floor_number(floor_text); elev = elevation_value(elev_text)
        if floor is None or floor != r['floor_number'] or elev_text != r['elevation_text_expected']:
            raise ValueError('source marker text mismatch')
        if abs(float(ft.dxf.rotation)) > 1e-8 or abs(float(et.dxf.rotation)) > 1e-8:
            raise ValueError('rotated datum text requires separate verification')
        b0, b1 = _point(baseline, 'start'), _point(baseline, 'end')
        l0, l1 = _point(left, 'start'), _point(left, 'end')
        r0, r1 = _point(right, 'start'), _point(right, 'end')
        k0, k1 = _point(leader, 'start'), _point(leader, 'end')
        if abs(b0[1]-b1[1]) > tolerance or not _close(l0, r0, tolerance):
            raise ValueError('invalid datum baseline or arrow apex')
        if abs(l0[1]-b0[1]) > tolerance or not min(b0[0],b1[0]) <= l0[0] <= max(b0[0],b1[0]):
            raise ValueError('datum apex does not touch baseline')
        if not (l1[0] < l0[0] < r1[0]) or abs(l1[1]-r1[1]) > tolerance or l1[1] <= l0[1]:
            raise ValueError('invalid datum marker arms')
        if abs((l0[0]-l1[0])-(r1[0]-r0[0])) > tolerance or abs(k0[1]-k1[1]) > tolerance:
            raise ValueError('datum marker asymmetry')
        if not (_close(k0,r1,tolerance) or _close(k1,r1,tolerance)):
            raise ValueError('elevation leader is disconnected')
        fpos, epos = _point(ft, 'insert'), _point(et, 'insert')
        fh, eh = float(ft.dxf.height), float(et.dxf.height)
        if min(fh,eh) <= 0 or not (l0[0] < fpos[0] <= max(b0[0], b1[0])) or not (0 <= fpos[1]-b0[1] <= 2*fh):
            raise ValueError('floor text is not positioned at datum')
        lx = min(k0[0],k1[0])
        if abs(epos[0]-lx) > eh or not (0 <= epos[1]-k0[1] <= 2*eh):
            raise ValueError('elevation text is not positioned at leader')
        levels.append({'floor_number': floor, 'floor_text': floor_text, 'elevation_source_text': elev_text,
                       'elevation_numeric_decimal': str(elev), 'datum_y_drawing_units': b0[1],
                       'source_handles': dict(zip(roles,ids)), 'annotation_layer':r['annotation_layer'],
                       'baseline_layer':r['baseline_layer']})
    levels.sort(key=lambda x:x['floor_number'])
    if len(levels) < 2 or len({r['floor_number'] for r in levels}) != len(levels):
        raise ValueError('duplicate or insufficient floor markers')
    differences=[]
    for a,b in zip(levels,levels[1:]):
        delta=Decimal(b['elevation_numeric_decimal'])-Decimal(a['elevation_numeric_decimal'])
        if b['floor_number'] != a['floor_number']+1 or delta<=0 or b['datum_y_drawing_units']<=a['datum_y_drawing_units']:
            raise ValueError('floor sequence or source datum order mismatch')
        differences.append({'from_floor':a['floor_number'],'to_floor':b['floor_number'],
                            'elevation_difference_decimal':str(delta), 'physical_pipe_length':None})
    return {'source_sha256':source_sha256,'source_level_unit':'m (drawing convention; verify project notes)',
            'levels':levels,'consecutive_datum_differences':differences,
            'scope':'verified local native datum symbols only; no pipe floor attribution, length, cross-view mapping, or acceptance',
            'hil_ready':False}


def collect(source, policy_path):
    """Read and verify the selected datum markers without changing a graph."""
    source, policy_path = Path(source), Path(policy_path)
    doc, proof = read_source(source)
    policy = json.loads(policy_path.read_text(encoding='utf8'))
    result = verify(doc, policy, proof['source_sha256'])
    result['policy_sha256'] = hashlib.sha256(policy_path.read_bytes()).hexdigest()
    result['extractor_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result['text_preflight'] = {'status': proof['status'], 'actual_read_codec': proof['actual_read_codec'],
                                'native_chinese_entity_count': proof['native_chinese_entity_count']}
    return result


def write_new(result, output):
    """Create an evidence artifact without silently replacing earlier evidence."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    p = argparse.ArgumentParser()
    for name in ('source', 'policy', 'output'):
        p.add_argument('--' + name, required=True, type=Path)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('refusing to overwrite output')
    result = collect(a.source, a.policy)
    write_new(result, a.output)
    print(json.dumps({'markers': len(result['levels']), 'differences': len(result['consecutive_datum_differences']), 'hil_ready': False}))


if __name__ == '__main__':
    main()
