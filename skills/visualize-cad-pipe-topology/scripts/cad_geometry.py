"""Source CAD vector export shared by the viewer builder."""
import ezdxf
from ezdxf.disassemble import recursive_decompose
from ezdxf.path import make_path, from_hatch
from ezdxf.render import TraceBuilder

RENDER_WARNINGS=[]

def strokes(entity, tolerance=1):
    """Return flattened source outlines and their CAD fill intent."""
    kind = entity.dxftype()
    if kind in ('TEXT', 'MTEXT', 'ATTDEF', 'ATTRIB', 'POINT', 'DIMENSION'):
        return []
    try:
        if kind in ('LWPOLYLINE', 'POLYLINE') and entity.has_width:
            # CAD constant/variable-width polylines are areas, not hairline outlines.
            # Ball valves and gauge root valves use this representation rather than HATCH.
            trace = TraceBuilder.from_polyline(entity, segments=96)
            elevation = entity.dxf.get('elevation', 0)
            if not isinstance(elevation, (int, float)):
                elevation = elevation.z
            result=[]
            for poly in trace.polygons_wcs(entity.ocs(), elevation):
                if not poly:
                    RENDER_WARNINGS.append({'source_handle':entity.dxf.get('handle',''),'layer':entity.dxf.layer,'entity_type':kind,'reason':'empty_width_polyline_trace_polygon; no renderable area; source unchanged'})
                    continue
                result.append(([(p.x,p.y)for p in poly]+[(poly[0].x,poly[0].y)],True))
            return result
        if kind in ('SOLID', 'TRACE', '3DFACE'):
            pts = list(entity.wcs_vertices())
            return [([(p.x, p.y) for p in pts] + [(pts[0].x, pts[0].y)], True)] if pts else []
        if kind == 'HATCH':
            return [([(v.x, v.y) for v in p.flattening(tolerance)], True) for p in from_hatch(entity)]
        p = make_path(entity)
        return [([(v.x, v.y) for v in p.flattening(tolerance)], False)]
    except (TypeError, ValueError, AttributeError, NotImplementedError):
        return []

def svg_shapes(items, transform):
    parts = []
    for pts, fill in items:
        if len(pts) < 2:
            continue
        xy = [transform(x, y) for x, y in pts]
        d = 'M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in xy)
        parts.append(f'<path d="{d}" fill="{"currentColor" if fill else "none"}"/>')
    return ''.join(parts)

def symbol(doc, block_name, cabinet=False):
    if block_name not in doc.blocks:
        raise ValueError(f'Missing source block {block_name}')
    items = []
    for entity in recursive_decompose(doc.blocks[block_name]):
        if cabinet and entity.dxf.get('color', 256) != 1:
            continue
        # Block geometry is only a few native units wide, unlike model space.
        items.extend(strokes(entity, tolerance=.001))
    return normalize_symbol(items, block_name)

def normalize_symbol(items, block_name):
    points = [p for pts, _ in items for p in pts]
    if not points:
        raise ValueError(f'No source geometry in {block_name}')
    x0, x1 = min(x for x,y in points), max(x for x,y in points)
    y0, y1 = min(y for x,y in points), max(y for x,y in points)
    scale = 54 / max(x1-x0, y1-y0, 1e-12)
    transform = lambda x,y: (32+(x-(x0+x1)/2)*scale, 32-(y-(y0+y1)/2)*scale)
    return {'block': block_name, 'markup': svg_shapes(items, transform), 'primitiveCount': len(items)}

