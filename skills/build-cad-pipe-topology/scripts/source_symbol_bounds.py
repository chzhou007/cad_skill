"""Visible native symbol extents, with non-rendering attributes kept as metadata.

An INSERT's ordinary DXF bbox can include hidden instance ATTRIB values far
outside its actual valve body. Those values are source data, not pipe contacts.
"""
from ezdxf import bbox
from ezdxf.disassemble import recursive_decompose


def visible_symbol_bounds(insert):
    primitives = list(recursive_decompose([insert]))
    graphics = []
    metadata = []
    for primitive in primitives:
        kind = primitive.dxftype()
        text = None
        hidden = False
        if kind in ('ATTRIB', 'ATTDEF'):
            text = primitive.dxf.text
            hidden = bool(primitive.dxf.flags & 1)
        elif kind in ('TEXT', 'MTEXT'):
            text = primitive.plain_text()
        if text is not None and ('\ufffd'in text or any(0xd800<=ord(c)<=0xdfff for c in text)):
            raise ValueError('Unreadable native symbol text; verify Chinese before geometry trials')
        if hidden or (text is not None and not text.strip()):
            original = getattr(primitive, 'source_of_copy', None)
            handle = primitive.dxf.get('handle') or (original.dxf.handle if original is not None else None)
            metadata.append({'source_handle': handle, 'entity_type': kind,
                             'tag': primitive.dxf.tag if kind in ('ATTRIB', 'ATTDEF') else None,
                             'text': text, 'invisible': hidden,
                             'reason': 'invisible_attribute' if hidden else 'empty_text',
                             'semantics': 'Preserved native metadata; no component quantity, type or hydraulic ownership inferred.'})
        else:
            graphics.append(primitive)
    visible = bbox.extents(graphics)
    if not visible.has_data:
        raise ValueError('Declared inline symbol has no visible native geometry: ' + insert.dxf.name)
    complete = bbox.extents(primitives)
    bounds = [visible.extmin.x, visible.extmin.y, visible.extmax.x, visible.extmax.y]
    original_bounds = [complete.extmin.x, complete.extmin.y, complete.extmax.x, complete.extmax.y]
    return bounds, {'source_handle': insert.dxf.handle, 'source_block': insert.dxf.name,
                    'original_bounds': original_bounds, 'visible_bounds': bounds,
                    'nonrendering_metadata': metadata,
                    'bounds_changed': bounds != original_bounds,
                    'native_source_unchanged': True}
