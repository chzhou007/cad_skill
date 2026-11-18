"""Extract exact straight body segments for a native equipment insert.

This is source-geometry evidence only: a contact with an outline is not a port.
Unsupported and curved primitives are returned explicitly, not approximated.
"""
from collections import Counter
import math
from ezdxf.disassemble import recursive_decompose


def body_straight_segments(insert):
    segments = []
    omitted = Counter()
    for entity in recursive_decompose([insert]):
        typ = entity.dxftype()
        if typ == 'LINE':
            a, b = entity.dxf.start, entity.dxf.end
            segments.append(((float(a.x), float(a.y)), (float(b.x), float(b.y))))
        elif typ == 'LWPOLYLINE':
            points = list(entity.vertices_in_wcs())
            bulges = [float(item[4]) for item in entity.get_points('xyseb')]
            count = len(points) if entity.closed else max(0, len(points)-1)
            for i in range(count):
                if not math.isfinite(bulges[i]) or abs(bulges[i]) > 1e-12:
                    omitted['LWPOLYLINE_bulge_segment'] += 1
                    continue
                a, b = points[i], points[(i+1) % len(points)]
                segments.append(((float(a.x), float(a.y)), (float(b.x), float(b.y))))
        elif typ not in ('TEXT', 'MTEXT', 'ATTRIB', 'ATTDEF'):
            omitted[typ] += 1
    return segments, dict(omitted)


def point_segment_distance(p, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    den = dx*dx + dy*dy
    t = max(0., min(1., ((p[0]-a[0])*dx + (p[1]-a[1])*dy)/den)) if den else 0.
    return math.hypot(p[0]-a[0]-t*dx, p[1]-a[1]-t*dy)


def segments_intersect(a, b, c, d, tol=0.05):
    u = (b[0]-a[0], b[1]-a[1]); v = (d[0]-c[0], d[1]-c[1])
    den = u[0]*v[1] - u[1]*v[0]
    if abs(den) < 1e-10:
        return any(point_segment_distance(p, x, y) <= tol
                   for p, x, y in ((a, c, d), (b, c, d), (c, a, b), (d, a, b)))
    w = (c[0]-a[0], c[1]-a[1])
    t = (w[0]*v[1]-w[1]*v[0])/den
    q = (w[0]*u[1]-w[1]*u[0])/den
    return 0 <= t <= 1 and 0 <= q <= 1

