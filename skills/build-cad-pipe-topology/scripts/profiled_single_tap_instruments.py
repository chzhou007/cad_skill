"""Inherited profile-driven native single-tap instrument assembly reader.

The recognition body is preserved from the historically verified profile rule.
It requires the native body class, one main tap and one complete labelled head.
Measurement leaders never create hydraulic connectivity.
"""
import math,collections
from ezdxf import bbox
import pipe_geometry as pg
from equipment_assemblies import native_primitives
from instrumentation import source_gauges

INHERITED_RECOGNIZER_AST_SHA256='d50c9a19494f6c883e47e1363e60c48879609ac997b0341fa0014fc207016988'

def single_tap_measurements(doc,segments,symbols,rules):
    groups=[];consumed=set();lines=list(doc.modelspace().query('LINE'));gauges=source_gauges(doc)
    def bb(e):
        b=bbox.extents([e]);return [b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y]
    for rule in rules:
        import re
        for symbol in symbols:
            if symbol['block']!=rule['source_block']:continue
            box=symbol['bounds'];diag=pg.dist(box[:2],box[2:]);entity=symbol['entity'];layer=entity.dxf.layer
            # The complete native body includes its own class letter, not a bare nearby box.
            body_texts=[p.dxf.text.strip()for p in native_primitives(entity)if p.dxftype()=='TEXT']
            if rule['body_text']not in body_texts:continue
            contacts=[];heads=[]
            for line in lines:
                if line.dxf.layer!=layer:continue
                a,b=pg.xy(line.dxf.start),pg.xy(line.dxf.end);length=pg.dist(a,b)
                if not pg.TOL<length<=diag*rule['maximum_leader_body_diagonals']:continue
                for at,other in [(a,b),(b,a)]:
                    if pg.point_bbox(at,box)>pg.TOL:continue
                    # Contact lies on the actual rectangular native body boundary.
                    if min(abs(at[0]-box[0]),abs(at[0]-box[2]),abs(at[1]-box[1]),abs(at[1]-box[3]))>pg.TOL:continue
                    mains=[s for s in segments if s.get('source_layer')in rule['main_layers']and pg.on(other,s['a'],s['b'])and abs(pg.dot(pg.sub(a,b),pg.sub(s['a'],s['b'])))<=.02*length*pg.dist(s['a'],s['b'])]
                    if mains:contacts.append({'point':other,'leader':line.dxf.handle,'mains':mains})
                    for gauge in gauges:
                        if not re.fullmatch(rule['tag_regex'],gauge['tag']):continue
                        if gauge['entity'].dxf.layer!=layer:continue
                        if abs(pg.dist(other,gauge['center'])-gauge['radius'])<=pg.TOL:heads.append((gauge,line.dxf.handle))
            if len(contacts)!=1 or len(heads)!=1:continue
            tap=contacts[0];gauge,headlead=heads[0];handles={symbol['handle'],tap['leader'],headlead,*gauge['handles']}
            for text in doc.modelspace().query('TEXT'):
                if text.dxf.layer!=layer:continue
                tb=bbox.extents([text]);center=((tb.extmin.x+tb.extmax.x)/2,(tb.extmin.y+tb.extmax.y)/2)
                if pg.dist(center,gauge['center'])<.85*gauge['radius']:handles.add(text.dxf.handle)
            groups.append({'id':'PIT-'+symbol['handle'],'label':rule['label'],'source_kind':'source_single_tap_instrument_assembly','source_handles':sorted(handles),'native_capillary_handles':[tap['leader']],'component_handles':[symbol['handle']],'attachment_points':[tap['point']],'display_center':gauge['center'],'source_tag':gauge['tag'],'hydraulic_connection':False,'rule':'native_body_class_text_one_native_main_tap_one_complete_tagged_head_two_exact_leaders'})
            consumed.add(symbol['handle'])
    return groups,consumed
