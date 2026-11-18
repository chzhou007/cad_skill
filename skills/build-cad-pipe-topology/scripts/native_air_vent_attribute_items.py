"""Inherit original air-vent normalization in a private attribute item view.

The physical graph, source entities and canonical component inventory remain
unchanged. Only source-proved, already-folded display legs are removed/trimmed
from the attribute reader's private LINE items; no new recognition kernel.
"""
import copy,dataclasses,math,runpy
from pathlib import Path
from confirm_crossview_paths import encode,sha
from axis_unbranched_vertical_DN import native_items,source_Z
from native_line_path_evidence import LAYERS,_on

MODE='inherited_native_air_vent_attribute_items_v1'


def replay(doc):
    path=Path(__file__).with_name('legacy_v17')/'analyze_graph.py'
    ns=runpy.run_path(str(path))
    ns['collect_pipe_segments'].__globals__['get_system_layers']=lambda current:{v:k for k,v in LAYERS.items()}
    layout=ns['infer_drawing_layout'](ns['equipment_labels'](doc))
    segments=ns['collect_pipe_segments'](doc);segments,overshoots=ns['trim_short_dangling_overshoots'](segments)
    segments,valves=ns['remove_turn_display_valve_stubs'](segments,ns['collect_turn_display_valve_regions'](doc))
    cleaned,removals=ns['remove_auto_air_vent_display_legs'](segments,ns['collect_auto_air_vent_ports'](doc),layout)
    return dict(removals=[dataclasses.asdict(r) for r in removals],source_kernel_sha256=sha(path),
        maximum_length=ns['MAX_AUTO_AIR_VENT_DISPLAY_LEG_LENGTH'],point_tolerance=ns['POINT_TOLERANCE'],labels=sorted(ns['AUTO_AIR_VENT_LABELS']),
        normalized_source_segments_before=len(segments),normalized_source_segments_after=len(cleaned),
        inherited_overshoot_removals=len(overshoots),inherited_turn_valve_removals=len(valves))


def overlap(a,b,c,d,tol=.05):
    v=[b[i]-a[i] for i in (0,1)];w=[d[i]-c[i] for i in (0,1)];length=math.hypot(*v);other=math.hypot(*w)
    if min(length,other)<=tol:return False
    if abs(v[0]*w[1]-v[1]*w[0])>1e-6*length*other:return False
    if abs(v[0]*(c[1]-a[1])-v[1]*(c[0]-a[0]))/length>tol:return False
    low,high=sorted(sum((p[i]-a[i])*v[i]/length for i in (0,1)) for p in (c,d))
    return min(length,high)-max(0,low)>tol


def qualify(doc,graph,inventory,normalization):
    before=encode(graph),encode(inventory);raw=native_items(doc,graph);private=copy.deepcopy(raw);records=[];used=set();names=set()
    edges={e['edge_id']:e for e in graph['edges']};tol=normalization['point_tolerance']
    if tol>.2 or normalization['maximum_length']>1000:raise ValueError('inherited air-vent limits cannot be widened')
    canonical=[r for r in inventory if r.get('equipment_type') in ('自动放气阀','自动排气阀') and str(r.get('source_kind','')).startswith('semantic_attdef_folded_')]
    for removal in normalization['removals']:
        system=removal['system'];port=removal['vent_port'];corner=removal['junction'];action=removal['action']
        if system not in LAYERS or action not in ('trim','remove') or not tol<removal['length']<=normalization['maximum_length']:
            raise ValueError('unsupported inherited vent removal')
        anchors=[e for e in doc.modelspace().query('ATTDEF') if e.dxf.tag.upper()=='WHAT' and e.dxf.text.strip() in normalization['labels']
            and math.dist(list(e.dxf.insert)[:2],port)<=.05]
        if len(anchors)!=1 or '\ufffd' in anchors[0].dxf.text:raise ValueError('unique readable native air-vent semantic anchor required')
        choices=[]
        for i,item in enumerate(raw):
            if item['root_handle'] is not None or item['layer']!=LAYERS[system]:continue
            ends=item['XYZ'];ports=[j for j,p in enumerate(ends) if math.dist(p[:2],port)<=tol]
            if len(ports)!=1 or not _on(corner,ends[0][:2],ends[1][:2],.05):continue
            pi=ports[0];other=ends[1-pi]
            if (action=='remove')!=(math.dist(other[:2],corner)<=.05):continue
            choices.append((i,item,pi))
        if len(choices)!=1:raise ValueError('folded display leg lacks one original modelspace LINE')
        index,item,pi=choices[0]
        if index in used:raise ValueError('multiple vent folds require a composed source-LINE owner')
        used.add(index);z=source_Z(item,corner);port_z=anchors[0].dxf.insert.z
        if abs(port_z-item['XYZ'][pi][2])>.05 or abs(z-port_z)>.05:raise ValueError('vent stem native Z is not coincident')
        # A real continuation attached to the vent end cannot be silently
        # discarded even if the inherited 2D fold kernel found a candidate.
        for j,other in enumerate(raw):
            if j==index or other['layer']!=item['layer']:continue
            if _on(item['XYZ'][pi][:2],other['XYZ'][0][:2],other['XYZ'][1][:2],tol) and abs(source_Z(other,item['XYZ'][pi][:2])-port_z)<=.05:
                raise ValueError('air-vent display endpoint reaches another real source pipe')
        matches=[r for r in canonical if r['system_hint']==system and r['source_kind']=='semantic_attdef_folded_'+action
            and math.dist([float(r['x']),float(r['y'])],port)<=.05 and math.dist([float(r['assignment_x']),float(r['assignment_y'])],corner)<=.05]
        if len(matches)!=1 or matches[0]['assignment_status']!='assigned':raise ValueError('canonical folded vent owner differs')
        component=matches[0];edge=edges.get(component['edge_id'])
        if edge is None or edge['system']!=system:raise ValueError('folded vent has no current same-system edge')
        named=[n for row in edge.get('equipment_inventory',[]) if row['equipment_type'] in ('自动放气阀','自动排气阀') for n in row['device_names']]
        if named.count(component['device_name'])!=1 or component['device_name'] in names:raise ValueError('canonical vent identity not uniquely conserved')
        names.add(component['device_name'])
        corners=[dict(edge_id=e['edge_id'],path_index=px,vertex_index=vi) for e in graph['edges'] if e['system']==system
            for px,path in enumerate(e['attribute_paths']) for vi,p in enumerate(path[1:-1],1) if math.dist(p,corner)<=.05]
        if len(corners)!=1 or corners[0]['edge_id']!=edge['edge_id']:raise ValueError('folded vent does not own one surviving graph corner')
        if any(n.get('node_type') in ('tee','physical_junction') and math.dist([n['x'],n['y']],corner)<=.05 for n in graph['nodes']):
            raise ValueError('graph still represents a physical T at the folded display corner')
        for e in graph['edges']:
            if e['system']!=system:continue
            if any(overlap(corner,item['XYZ'][pi][:2],a,b) for path in e['attribute_paths'] for a,b in zip(path,path[1:])):
                raise ValueError('folded display span remains an active graph pipe')
        normalized=None
        if action=='trim':
            normalized=copy.deepcopy(item);normalized['XYZ'][pi]=[corner[0],corner[1],z]
            normalized['original_native_XYZ']=copy.deepcopy(item['XYZ'])
            normalized['attribute_item_role']='original_air_vent_display_tail_trimmed_in_private_view'
            private[index]=normalized
        else:private[index]=None
        records.append(dict(original_removal=copy.deepcopy(removal),source_line_handle=item['child_handle'],original_native_XYZ=copy.deepcopy(item['XYZ']),
            normalized_native_XYZ=normalized['XYZ'] if normalized else None,native_anchor=dict(handle=anchors[0].dxf.handle,text=anchors[0].dxf.text,position=list(anchors[0].dxf.insert)),
            canonical_component=copy.deepcopy(component),current_graph_corner=corners[0],physical_length_mm=None))
    if names!={r['device_name'] for r in canonical}:raise ValueError('complete already-folded canonical vent cohort not replayed')
    if before!=(encode(graph),encode(inventory)):raise ValueError('graph or canonical component inventory changed')
    items=[x for x in private if x is not None]
    return items,dict(mode=MODE,records=records,normalization=normalization,canonical_components=len(inventory),canonical_folded_vents=len(canonical),
        original_native_items_sha256=__import__('hashlib').sha256(encode(raw)).hexdigest(),attribute_items_sha256=__import__('hashlib').sha256(encode(items)).hexdigest(),
        source_or_graph_mutated=False,components_reassigned=0,physical_lengths_assigned=0,human_accepted=False)


def collect(doc,graph,inventory):return qualify(doc,graph,inventory,replay(doc))
