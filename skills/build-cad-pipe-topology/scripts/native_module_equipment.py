"""One equipment assembly from native modules sharing complete source sides.

This opt-in recognizer never groups by nearest caption or bounding box. The
closed exterior is traced from native sides after internal shared sides cancel.
No pipe or equipment contact is inferred here; nested_equipment_ports owns that.
"""
import collections
import math
import re

from ezdxf import bbox
from native_proxy_evidence import block_fingerprint
from nested_equipment_ports import inside, perimeter, readable, resolve_instance_chain


def area(points):
    # Translate first to avoid cancellation with large CAD world coordinates.
    origin = points[0]
    q = [[p[i] - origin[i] for i in (0, 1)] for p in points]
    return abs(sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(q, q[1:] + q[:1]))) / 2


def native_union(polygons, tolerance, maximum_overlap=0.):
    """Return shared-side components and exact native exterior rings.

    Vertex tolerance only reconciles native numerical precision. It never
    bridges a missing side or uses a component bbox as its physical outline.
    """
    if maximum_overlap:
        return rectangular_overlap_union(polygons, tolerance, maximum_overlap)
    points = []

    def vertex(p):
        matches = [i for i, q in enumerate(points) if math.dist(p, q) <= tolerance]
        if len(matches) > 1:
            raise ValueError('Ambiguous native module vertex precision')
        if matches:
            return matches[0]
        points.append(list(p))
        return len(points) - 1

    sides = collections.defaultdict(list)
    parent = list(range(len(polygons)))

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    for i, poly in enumerate(polygons):
        ids = [vertex(p) for p in poly]
        if len(set(ids)) != len(ids):
            raise ValueError('Degenerate native module contour')
        for a, b in zip(ids, ids[1:] + ids[:1]):
            sides[tuple(sorted((a, b)))].append(i)
    for owners in sides.values():
        if len(owners) > 2:
            raise ValueError('Overlapping or duplicate native module sides')
        if len(owners) == 2:
            parent[root(owners[0])] = root(owners[1])
    groups = collections.defaultdict(list)
    for i in range(len(polygons)):
        groups[root(i)].append(i)
    result = []
    for members in groups.values():
        selected = set(members)
        outer = [side for side, owners in sides.items()
                 if len(owners) == 1 and owners[0] in selected]
        adjacency = collections.defaultdict(list)
        for a, b in outer:
            adjacency[a].append(b)
            adjacency[b].append(a)
        if not adjacency or any(len(v) != 2 for v in adjacency.values()):
            raise ValueError('Native module union does not have one closed exterior')
        start = min(adjacency, key=lambda i: tuple(points[i]))
        ring = [start]
        previous = None
        current = start
        while True:
            nxt = next(i for i in adjacency[current] if i != previous)
            if nxt == start:
                break
            if nxt in ring:
                raise ValueError('Native module exterior self-intersects')
            ring.append(nxt)
            previous, current = current, nxt
        if len(ring) != len(adjacency):
            raise ValueError('Native module union has a hole or disconnected exterior')
        polygon = [points[i] for i in ring]
        expected = sum(area(polygons[i]) for i in members)
        if abs(area(polygon) - expected) > max(tolerance * tolerance, expected * 1e-8):
            raise ValueError('Native module union overlaps or lacks source area')
        result.append({'members': members, 'polygon': polygon,
                       'shared_side_count': sum(len(owners) == 2 and owners[0] in selected
                                                for owners in sides.values())})
    return result


def rectangular_overlap_union(polygons, tolerance, maximum_overlap):
    """True native union of calibrated, parallel rectangular module rows.

    A slight *actual overlap* may be accepted by a pinned source profile. Gaps
    are never bridged. Grid cells partition only the existing rectangle area;
    their union exterior therefore remains on real source boundary segments.
    """
    origin = polygons[0][0]
    direction = [polygons[0][1][i] - origin[i] for i in (0, 1)]
    size = math.hypot(*direction)
    u = [p / size for p in direction]
    v = [-u[1], u[0]]
    rectangles = []
    for polygon in polygons:
        projected = [[sum((p[i] - origin[i]) * axis[i] for i in (0, 1))
                      for axis in (u, v)] for p in polygon]
        bounds = [min(p[0] for p in projected), min(p[1] for p in projected),
                  max(p[0] for p in projected), max(p[1] for p in projected)]
        if any(min(abs(p[0] - bounds[i]) for i in (0, 2)) > tolerance or
               min(abs(p[1] - bounds[i]) for i in (1, 3)) > tolerance for p in projected):
            raise ValueError('Bounded overlap requires parallel native rectangles')
        rectangles.append(bounds)
    parent = list(range(len(rectangles)))

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    for i, a in enumerate(rectangles):
        for j, b in enumerate(rectangles[:i]):
            full_x = abs(a[0] - b[0]) <= tolerance and abs(a[2] - b[2]) <= tolerance
            full_y = abs(a[1] - b[1]) <= tolerance and abs(a[3] - b[3]) <= tolerance
            if full_x and full_y:
                raise ValueError('Duplicate native module contours')
            dx = min(a[2], b[2]) - max(a[0], b[0])
            dy = min(a[3], b[3]) - max(a[1], b[1])
            if (full_y and -tolerance <= dx <= maximum_overlap) or (full_x and -tolerance <= dy <= maximum_overlap):
                parent[root(i)] = root(j)
    groups = collections.defaultdict(list)
    for i in range(len(rectangles)):
        groups[root(i)].append(i)
    output = []
    for members in groups.values():
        xs = sorted({rectangles[j][i] for j in members for i in (0, 2)})
        ys = sorted({rectangles[j][i] for j in members for i in (1, 3)})
        # Collapse only numerical source precision; preserve the observed overlap.
        def unique(values):
            result = []
            for value in values:
                if not result or value - result[-1] > tolerance:
                    result.append(value)
            return result
        xs, ys = unique(xs), unique(ys)
        cells = []
        for left, right in zip(xs, xs[1:]):
            for bottom, top in zip(ys, ys[1:]):
                cx, cy = (left + right) / 2, (bottom + top) / 2
                if not any(rectangles[j][0] - tolerance < cx < rectangles[j][2] + tolerance and
                           rectangles[j][1] - tolerance < cy < rectangles[j][3] + tolerance for j in members):
                    continue
                cells.append([[origin[i] + x * u[i] + y * v[i] for i in (0, 1)]
                              for x, y in ((left, bottom), (right, bottom), (right, top), (left, top))])
        result = native_union(cells, tolerance)
        if len(result) != 1:
            raise ValueError('Native rectangle union is disconnected')
        outer = result[0]['polygon']
        output.append({'members': members, 'polygon': outer,
                       'shared_side_count': len(members) - 1,
                       'native_overlap_area': max(0., sum(area(polygons[j]) for j in members) - area(outer))})
    return output


def external_caption_matches(caption, polygon, maximum_gap_ratio, tolerance):
    """Native text immediately outside a parallel body face, never nearest text."""
    matches = []
    center = caption['center']
    direction = caption['direction']
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        vector = [b[i] - a[i] for i in (0, 1)]
        length = math.hypot(*vector)
        if length <= tolerance:
            continue
        unit = [p / length for p in vector]
        if abs(unit[0] * direction[1] - unit[1] * direction[0]) > 1e-6:
            continue
        along = sum((center[i] - a[i]) * unit[i] for i in (0, 1))
        if not -tolerance <= along <= length + tolerance:
            continue
        normal = [-unit[1], unit[0]]
        signed = [sum((p[i] - a[i]) * normal[i] for i in (0, 1)) for p in caption['extent_corners']]
        if min(signed) < -tolerance and max(signed) > tolerance:
            continue  # text straddles this face; not a qualified external caption
        gap = min(abs(p) for p in signed)
        if gap <= caption['height'] * maximum_gap_ratio:
            matches.append({'source_face': [a, b], 'native_text_face_gap': gap})
    return matches


def rectangle(entity, dimensions, tolerance):
    if entity.dxftype() != 'LWPOLYLINE' or not entity.closed or len(entity) != 4:
        return False
    if entity.has_width or any(abs(v[4]) > 1e-10 for v in entity.get_points()):
        return False
    points = [list(p)[:2] for p in entity.vertices_in_wcs()]
    vectors = [[b[i] - a[i] for i in (0, 1)]
               for a, b in zip(points, points[1:] + points[:1])]
    lengths = [math.hypot(*v) for v in vectors]
    if min(lengths) <= tolerance:
        return False
    if any(abs(sum(a[i] * b[i] for i in (0, 1))) > tolerance * max(lengths)
           for a, b in zip(vectors, vectors[1:] + vectors[:1])):
        return False
    return all(abs(a - b) <= tolerance for a, b in
               zip(sorted(lengths), sorted(dimensions * 2)))


def recognize(doc, rules):
    instances = []
    ledger = []
    for rule in rules:
        matrix, parent = resolve_instance_chain(doc, rule['source_chain'])
        block = doc.blocks[parent.dxf.name]
        if block_fingerprint(block) != rule['fingerprint']:
            raise ValueError('Native module source prototype changed')
        tol = rule['module_contact_tolerance']
        outline_tolerance = rule.get('outline_contact_tolerance')
        if outline_tolerance is not None:
            if outline_tolerance > min(rule['module_dimensions']) * .001 or not rule.get('outline_precision_evidence'):
                raise ValueError('Module outline precision needs bounded source calibration')
        maximum_overlap = rule.get('maximum_native_module_overlap', 0.)
        if maximum_overlap and (maximum_overlap > min(rule['module_dimensions']) * .002 or
                                not rule.get('native_overlap_evidence')):
            raise ValueError('Native module overlap needs bounded source calibration')
        outside_ratio = rule.get('maximum_external_caption_gap_text_heights', 0.)
        if outside_ratio and (outside_ratio > .1 or not rule.get('external_caption_evidence')):
            raise ValueError('External caption placement needs bounded source calibration')
        modules = [e for e in block if rectangle(e, rule['module_dimensions'], tol)]
        unsupported = [e.dxf.handle for e in block
                       if e.dxftype() == 'LWPOLYLINE' and e not in modules]
        if unsupported:
            ledger.append({'status': 'pending_unsupported_module_geometry',
                           'source_chain': rule['source_chain'], 'source_handles': unsupported})
        polygons = [[list(matrix.transform(p))[:2] for p in e.vertices_in_wcs()]
                    for e in modules]
        texts = []
        for e in block.query('TEXT MTEXT'):
            text = readable(e.plain_text()).strip()
            if not re.fullmatch(rule['tag_regex'], text):
                continue
            extent = bbox.extents([e])
            if not extent.has_data:
                continue
            # Native text extent is used only for local caption association.
            # Hydraulic ownership always uses the traced native exterior.
            center = (extent.extmin + extent.extmax) / 2
            direction = matrix.transform_direction((math.cos(math.radians(e.dxf.get('rotation', 0))),
                                                    math.sin(math.radians(e.dxf.get('rotation', 0))), 0))
            norm = math.hypot(direction.x, direction.y)
            corners = [[x, y, center.z] for x, y in ((extent.extmin.x, extent.extmin.y),
                       (extent.extmax.x, extent.extmin.y), (extent.extmax.x, extent.extmax.y),
                       (extent.extmin.x, extent.extmax.y))]
            texts.append({'handle': e.dxf.handle, 'text': text,
                          'center': list(matrix.transform(center))[:2],
                          'extent_corners': [list(matrix.transform(p))[:2] for p in corners],
                          'direction': [direction.x / norm, direction.y / norm],
                          'height': math.hypot(*list(matrix.transform_direction((0, e.dxf.height if e.dxftype()=='TEXT' else e.dxf.char_height, 0))))})
        groups = native_union(polygons, tol, maximum_overlap)
        caption_owners = collections.defaultdict(list)
        for i, group in enumerate(groups):
            for caption in texts:
                if inside(caption['center'], group['polygon']) or perimeter(caption['center'], group['polygon']) <= tol:
                    caption_owners[caption['handle']].append(i)
        outside_evidence = {}
        if outside_ratio:
            for caption in texts:
                if caption_owners[caption['handle']]:
                    continue
                for i, group in enumerate(groups):
                    proof = external_caption_matches(caption, group['polygon'], outside_ratio, tol)
                    if proof:
                        caption_owners[caption['handle']].append(i)
                        outside_evidence[(caption['handle'], i)] = proof
        for i, group in enumerate(groups):
            members = [modules[j] for j in group['members']]
            handles = [e.dxf.handle for e in members]
            captions = [t for t in texts if i in caption_owners[t['handle']]]
            row = {'source_chain': rule['source_chain'], 'source_handles': handles,
                   'module_count': len(members), 'source_captions': captions,
                   'outer_polygon': group['polygon'], 'shared_side_count': group['shared_side_count']}
            if group.get('native_overlap_area'):row['native_overlap_area']=group['native_overlap_area']
            if len(captions) != 1 or len(caption_owners[captions[0]['handle']]) != 1:
                row['status'] = 'pending_missing_or_competing_native_caption'
                ledger.append(row)
                continue
            caption = captions[0]
            if (caption['handle'], i) in outside_evidence:
                row['caption_placement']='source_calibrated_external_face'
                row['external_caption_evidence']=outside_evidence[(caption['handle'], i)]
            polygon = group['polygon']
            identity = 'EQ-' + rule['floor'] + '-' + rule['source_chain'][-1] + '-' + min(handles)
            item = {'node_id': identity, 'source_chain': rule['source_chain'],
                    'source_block': parent.dxf.name, 'floor': rule['floor'],
                    'source_members': handles + [caption['handle']],
                    'tag': caption['text'], 'source_tag_handle': caption['handle'], 'texts': captions,
                    'polygon': polygon,
                    'primitives': [{'source_handle': e.dxf.handle, 'points': polygons[j], 'closed': True}
                                   for e, j in zip(members, group['members'])],
                    'subtype': rule['label'], 'subtype_zh': rule['label_zh'], 'symbol_key': rule['symbol_key'],
                    'body_assembly_kind': 'native_shared_side_modules', 'native_module_count': len(members),
                    'class_reference': rule.get('class_reference'),
                    'enclosed_terminal_ownership': bool(rule.get('enclosed_terminal_ownership')),
                    'bounds': [min(p[0] for p in polygon), min(p[1] for p in polygon),
                               max(p[0] for p in polygon), max(p[1] for p in polygon)]}
            if outline_tolerance is not None:
                item.update(outline_contact_tolerance=outline_tolerance,
                            outline_precision_evidence=rule['outline_precision_evidence'])
            instances.append(item)
            row.update(status='verified_native_module_body_and_unique_caption', node_id=identity)
            ledger.append(row)
        for caption in texts:
            if not caption_owners[caption['handle']]:
                ledger.append({'status': 'pending_caption_outside_native_bodies',
                               'source_chain': rule['source_chain'], 'source_handles': [caption['handle']],
                               'source_caption': caption['text'], 'caption_center': caption['center']})
    return instances, ledger
