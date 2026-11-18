"""Carry a source-owned axis DN across native two-arm bends, only to verticals.

This is local source continuity inside one original attribute path. It does not
infer across a T, a drawing gap, an inline symbol, a different path, or views.
Existing annotation owners still decide the seed; no new nearest-text binding.
"""
import collections,copy,math
from ezdxf.disassemble import recursive_decompose
from confirm_crossview_paths import encode
from native_repeated_branch_DN_layout import primitives
from native_line_path_evidence import _on,LAYERS
from pipe_annotation_attributes import source_texts,direct_diameters,parse_dn_annotation,recognize_f_leaders,contact
from native_paired_caption_geometry import collect as paired_captions
from axis_vertical_DN_batch import MODE as ANNOTATION_MODE
MODE='native_axis_unbranched_vertical_DN_inheritance_v1'

def source_key(row):return row['edge_id'],row['path_index'],row['segment_index']
def native_items(doc,graph):
    return primitives(doc,graph)+[dict(root_handle=None,child_handle=e.dxf.handle,XYZ=[list(e.dxf.start),list(e.dxf.end)],layer=e.dxf.layer)
        for e in doc.modelspace().query('LINE')if e.dxf.layer in LAYERS.values()]
def identity(item):return item['root_handle'],item['child_handle']
def source_Z(item,point):
    a,b=item['XYZ']
    if any(len(p)!=3 or any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)for v in p)for p in(a,b)):raise ValueError('finite native source XYZ required')
    d=[b[i]-a[i]for i in(0,1)];den=sum(v*v for v in d)
    if den<=.05**2:raise ValueError('degenerate native LINE in inheritance corridor')
    t=sum((point[i]-a[i])*d[i]for i in(0,1))/den
    return a[2]+t*(b[2]-a[2])

def chain_evidence(scopes,root,items):
    chain=[];bends=[]
    for s in scopes:
        if s.get('native_source_status')!='single_source_line_covers':raise ValueError('unwitnessed or ambiguous source chain')
        matches=[x for x in items if x['root_handle']==root and x['layer']==LAYERS[s['system']]and all(_on(p,x['XYZ'][0][:2],x['XYZ'][1][:2],.05)for p in s['scope_points'])]
        if len(matches)!=1:raise ValueError('native segment child identity not unique')
        chain.append(matches[0])
    for i,(left,right)in enumerate(zip(chain,chain[1:])):
        point=scopes[i]['scope_points'][1]
        if math.dist(point,scopes[i+1]['scope_points'][0])>.05:raise ValueError('original path has a drawing gap')
        z=source_Z(left,point)
        if abs(z-source_Z(right,point))>.05:raise ValueError('native XYZ bend does not contact')
        incident=[x for x in items if x['layer']==left['layer']and _on(point,x['XYZ'][0][:2],x['XYZ'][1][:2],.05)and abs(source_Z(x,point)-z)<=.05]
        arms=sum(sum(math.dist(point,p[:2])>.05 for p in x['XYZ'])for x in incident)
        if arms!=2 or {identity(x)for x in incident}!={identity(x)for x in(left,right)}:raise ValueError('bend contains another source arm or duplicate')
        bends.append(dict(point_xy=list(point),source_Z=z,source_arms=arms,native_primitives=copy.deepcopy(incident),physical_T_crossed=False))
    return dict(native_chain=copy.deepcopy(chain),bends=bends,original_path_index=scopes[0]['path_index'],segment_indexes=[s['segment_index']for s in scopes],
        native_cuts_are_not_physical_nodes=True,source_Z_used_as_length=False)

def annotation_index(doc,graph,source_hash):
    texts=source_texts(doc,'axis',source_hash)
    if any('\ufffd'in t['text']for t in texts):raise ValueError('axis Chinese is unreadable')
    probes=[dict(t,text='DN1')for t in texts if'DN'in t['text'].upper()];layers={t['layer']for t in texts};claims=paired_captions(doc)['F_owned_texts']
    frames=recognize_f_leaders(doc,texts,[],graph['edges'],layers);strokes=[(a,b)for f in frames for a,b in zip(f['stem'],f['stem'][1:])]
    handles={str(c[k])for cc in claims.values()for c in cc for k in('stem',)if c.get('kind')=='native_exploded_F_frame_candidate'and c.get(k)}
    for h in handles:
        entity=doc.entitydb.get(h)
        if entity is None or entity.dxftype()!='LINE':raise ValueError('reserved exploded F source changed')
        strokes.append((list(entity.dxf.start)[:2],list(entity.dxf.end)[:2]))
    nested={}
    for root in {e.get('source_insert_handle')for e in graph['edges']if e.get('source_insert_handle')}:
        nested[root]=any(e.dxftype()in('TEXT','MTEXT')and'DN'in e.plain_text().upper()for e in recursive_decompose([doc.entitydb[root]]))
    return dict(probes=probes,claims=claims,F_strokes=strokes,nested_DN=nested)

def annotation_guard(doc,seeds,scopes,index,source_hash,root):
    if root and index['nested_DN'].get(root):raise ValueError('nested native DN needs its original annotation owner')
    allowed=set();lineage=[]
    for seed in seeds:
        for observation in seed['observations']:
            text=observation['source_text'];entity=doc.entitydb.get(text['handle']);parsed=parse_dn_annotation(text['text'])
            if(text['source_sha256']!=source_hash or not parsed or parsed['nominal_mm']!=seed['nominal_mm']or entity is None
                or entity not in doc.modelspace()or entity.dxftype()not in('TEXT','MTEXT')or entity.plain_text()!=text['text']):raise ValueError('original qualified seed annotation changed')
            if text['handle']in index['claims']:raise ValueError('F-owned seed requires its ordered annotation owner')
            allowed.add(text['handle']);lineage.append(copy.deepcopy(observation))
    if not allowed:raise ValueError('independently qualified source annotation required')
    paths=[s['scope_points']for s in scopes]
    if any(contact(a,b,x,y)is not None for a,b in index['F_strokes']for path in paths for x,y in zip(path,path[1:])):raise ValueError('ordered F leader crosses inheritance corridor')
    other=[t for t in index['probes']if t['handle']not in allowed]
    assigned,pending=direct_diameters(other,[dict(edge_id='private_native_corridor',attribute_paths=paths)],set(),{t['layer']for t in other})
    if assigned or any(p['candidate_edge_ids']for p in pending):raise ValueError('another in-scope DN requires its ownership or transition reader')
    return dict(seed_observations=lineage,seed_text_handles=sorted(allowed),other_in_scope_DN_annotations=[],F_crossings=[],
        nested_annotation_scope_clear=True,another_annotated_diameter_blocks_inheritance=True)

def collect(doc,graph,raw,route,annotations,source_hash,graph_hash):
    if(annotations.get('mode')!=ANNOTATION_MODE or annotations.get('source_sha256')!=source_hash or annotations.get('graph_sha256')!=graph_hash
        or graph['metadata']['source_sha256']!=source_hash or annotations.get('graph_mutated')is not False or annotations.get('human_accepted')is not False):raise ValueError('current native annotation and graph scope required')
    before=encode(graph),encode(raw),encode(route),encode(annotations)
    edges={e['edge_id']:e for e in graph['edges']};rows={source_key(r):r for r in route['records']};known={source_key(r):r for r in annotations['records']}
    if len(rows)!=len(route['records'])or len(known)!=len(annotations['records']):raise ValueError('duplicate original source domains')
    retained={}
    for e in raw['edges']:
        for value in e.get('axis_riser_attributes',[]):
            key=e['edge_id'],value['path_index'],value['segment_index'];scope=rows.get(key)
            if not scope or scope['direction_class']!='vertical'or scope['scope_points']!=e['attribute_paths'][key[1]][key[2]:key[2]+2]:raise ValueError('retained vertical scope differs from original route')
            if key in known and known[key]['nominal_mm']!=value['nominal_mm']:raise ValueError('previous vertical DN conflicts with original annotation')
            retained[key]=copy.deepcopy(value)
    existing=set(known)|set(retained);seeds=collections.defaultdict(list);old_pending={source_key(p):p for p in annotations['pending']}
    for key,seed in known.items():
        value=seed['nominal_mm']
        if isinstance(value,bool)or not isinstance(value,(int,float))or not math.isfinite(value)or value<=0:raise ValueError('invalid original source annotation DN')
        if rows[key]['scope_points']!=seed['scope_points']or rows[key]['system']!=seed['system']:raise ValueError('qualified seed source domain differs')
        seeds[key[0],key[1]].append(seed)
    items=native_items(doc,graph);index=annotation_index(doc,graph,source_hash);records=[];pending=[]
    for key,target in rows.items():
        if target['direction_class']!='vertical'or key in existing:continue
        try:
            if abs(target['scope_points'][1][0]-target['scope_points'][0][0])>.05:raise ValueError('target is not an axis vertical segment')
            prior=old_pending.get(key)
            if not prior or prior['reason']!='no_qualified_axis_annotation_on_this_vertical_segment':raise ValueError('original annotation or source ambiguity retained')
            choices=seeds[key[0],key[1]]
            if len({s['nominal_mm']for s in choices})!=1:raise ValueError('no unique independently qualified seed on same original path')
            seed=min(choices,key=lambda s:(abs(s['segment_index']-key[2]),s['segment_index']));low,high=sorted((seed['segment_index'],key[2]))
            scopes=[rows[key[0],key[1],i]for i in range(low,high+1)];root=edges[key[0]].get('source_insert_handle')
            continuity=chain_evidence(scopes,root,items);guard=annotation_guard(doc,choices,scopes,index,source_hash,root)
            records.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],scope_points=copy.deepcopy(target['scope_points']),system=target['system'],
                floor_start=target['floor_start'],floor_end=target['floor_end'],nominal_mm=seed['nominal_mm'],status='native_axis_vertical_DN_inherited_through_unbranched_bends',
                seed_record=copy.deepcopy(seed),continuity_evidence=continuity,annotation_guard=guard,native_witnesses=copy.deepcopy(target['native_witnesses']),
                source='axis_11_native_qualified_annotation_and_unbranched_source_continuity',whole_edge_DN_assigned=False,physical_length_mm=None,whole_edge_physical_length_mm=None,human_accepted=False))
        except ValueError as exc:pending.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],reason=str(exc),original_reason=old_pending.get(key,{}).get('reason')))
    if before!=(encode(graph),encode(raw),encode(route),encode(annotations)):raise ValueError('original topology or annotation evidence mutated')
    count=sum(r['direction_class']=='vertical'for r in route['records'])
    if len(existing)+len(records)+len(pending)!=count:raise ValueError('vertical domain conservation differs')
    return dict(mode=MODE,records=records,pending=pending,counts=dict(vertical_segments=count,previous_known_vertical_domains=len(existing),new_inherited_vertical_domains=len(records),
        current_known_vertical_domains=len(existing)+len(records),remaining_unknown_vertical_domains=len(pending),same_floor_new_domains=sum(r['floor_start']==r['floor_end']for r in records)),
        original_annotation_records_preserved=True,original_axis_graphs_unchanged=True,horizontal_plan_attributes_changed=False,all_vertical_values_from11=True,
        crossed_physical_Ts=0,crossview_values_used_as_seeds=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False)
