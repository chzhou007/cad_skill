"""Inventory complete source glyphs that did not become graph interfaces.

Near endpoints are diagnostic only; this module never changes graph topology.
"""
import math
from cad_ceiling_native_rules import match_out_of_plane_symbol


def identify(circles, segments, loaded_circle_handles, *, tolerance=0.05, diagnostic_radius=1.0):
    if not math.isfinite(tolerance) or not math.isfinite(diagnostic_radius) or tolerance <= 0 or diagnostic_radius < tolerance:
        raise ValueError('invalid source diagnostic tolerance')
    handles = [c['handle'] for c in circles]
    if len(handles) != len(set(handles)):
        raise ValueError('duplicate source circle handle')
    loaded = set(loaded_circle_handles)
    if not loaded <= set(handles):
        raise ValueError('loaded interface refers to missing source circle')
    glyphs = [s for s in segments if s.get('layer') == '空调立管、水平支管']
    rows = []
    for c in circles:
        if c['handle'] in loaded:
            continue
        match = match_out_of_plane_symbol(c, glyphs, tolerance)
        if match is None:
            continue
        center = c['center']; endpoints = []; other_endpoints = []
        for s in segments:
            if s.get('excluded_circle_local_geometry') or s.get('system') not in ('supply', 'return'):
                continue
            for side in ('a', 'b'):
                distance = math.dist(center, s[side])
                if distance <= diagnostic_radius:
                    target = endpoints if s['system'] == c['system'] else other_endpoints
                    target.append({'source_handle': s['handle'], 'side': side, 'system': s['system'],
                                   'distance_to_circle_center': distance, 'point': s[side]})
        exact_opposite = any(e['distance_to_circle_center'] <= tolerance for e in other_endpoints)
        rows.append({'circle_handle': c['handle'], 'center': center, 'radius': c['radius'],
                     'system': c['system'],
                     'glyph_handles': [s['handle'] for group in match for s in group],
                     'near_same_system_source_endpoints': sorted(endpoints, key=lambda e: (e['source_handle'], e['side'])),
                     'near_opposite_system_source_endpoints': sorted(other_endpoints, key=lambda e: (e['source_handle'], e['side'])),
                     'source_system_conflict': 'exact_opposite_system_endpoint' if exact_opposite else 'not_observed_at_circle_center',
                     'status': 'complete_glyph_not_loaded_as_interface',
                     'connectivity': 'unverified', 'diagnostic_radius': diagnostic_radius})
    return sorted(rows, key=lambda r: r['circle_handle'])
