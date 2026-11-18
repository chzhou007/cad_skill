"""Reproduce scoped equipment candidate TEXT as source evidence, never identity."""
import math


def extract(doc, nodes, source_sha256):
    modelspace = doc.modelspace()
    rows = {}
    for node in nodes:
        evidence = node.get('source_label_pair_evidence')
        if not evidence:
            continue
        if evidence.get('identity_confirmed') is not False or evidence.get('plan_source_sha256') != source_sha256:
            raise ValueError('equipment label evidence source or state mismatch')
        for candidate in evidence.get('alternatives', []):
            handle = candidate['plan_text_handle']
            entity = doc.entitydb.get(handle)
            if entity is None or entity.dxftype() != 'TEXT' or entity.dxf.owner != modelspace.block_record_handle:
                raise ValueError('equipment label must be native modelspace TEXT')
            text = entity.dxf.text
            if text != candidate['label'] or not text or any(ord(c) < 32 or c in '\ufffd\u202e\u202d\u2066\u2067\u2068\u2069' for c in text):
                raise ValueError('equipment label text mismatch or unreadable')
            d = entity.dxf
            p = d.insert
            if (d.get('halign', 0) != 0 or d.get('valign', 0) != 0 or d.get('text_generation_flag', 0) != 0
                    or d.get('invisible', 0) or abs(d.get('oblique', 0)) > 1e-9
                    or abs(p.z) > 1e-9 or tuple(d.get('extrusion', (0, 0, 1))) != (0, 0, 1)):
                raise ValueError('unsupported native equipment label layout')
            height, width, rotation = float(d.height), float(d.get('width', 1)), float(d.get('rotation', 0))
            if not all(math.isfinite(v) for v in (p.x, p.y, height, width, rotation)) or height <= 0 or width <= 0:
                raise ValueError('invalid native equipment label geometry')
            row = {'id': 'equipment-text-' + handle, 'source_handle': handle, 'text': text,
                   'position': [p.x, p.y], 'height': height, 'rotation': rotation, 'width_factor': width,
                   'source_layer': d.layer, 'source_style': d.get('style', 'Standard'),
                   'rendering': 'substitute_font_native_position_rotation_width_not_exact_glyphs',
                   'identity_binding': 'unconfirmed'}
            if handle in rows and rows[handle] != row:
                raise ValueError('conflicting equipment source label')
            rows[handle] = row
    return list(rows.values())
