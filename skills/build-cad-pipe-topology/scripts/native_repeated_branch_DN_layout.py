"""Bind a crowded native DN to a repeated, independently readable block layout.

Learn the exact text profile, root linear pose, native child LINE and signed
normal offset from at least four other source instances. Targets never act as
controls. This is a local annotation ownership proof, not edge-wide DN fusion.
"""
import math
from ezdxf.disassemble import recursive_decompose
from calibrated_direct_dn_evidence import profile
from native_dn_text_position import supported
from native_line_path_evidence import LAYERS,_on
from source_direct_dn_evidence import _projection
from source_dn_bulk_screen import screen
from pipe_annotation_attributes import source_texts,parse_dn_annotation,recognize_f_leaders


def primitives(doc,graph):
    output=[]
    for root_handle in sorted({e.get('source_insert_handle') for e in graph['edges'] if e.get('source_insert_handle')}):
        root=doc.entitydb.get(root_handle)
        if root is None or not root.is_alive or root not in doc.modelspace():raise ValueError('missing graph-referenced native layout instance')
        if root.dxftype()!='INSERT':continue
        if tuple(root.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('unsupported repeated-layout root OCS')
        for line in recursive_decompose([root]):
            if line.dxftype()!='LINE' or line.dxf.layer not in LAYERS.values():continue
            source=line.source_of_copy
            if source is None:raise ValueError('native repeated-layout LINE lacks source provenance')
            output.append(dict(root_handle=root_handle,root_block=root.dxf.name,child_handle=source.dxf.handle,
                root_linear_pose=[root.dxf.get(k,d) for k,d in [('rotation',0),('xscale',1),('yscale',1),('zscale',1)]],
                XYZ=[list(line.dxf.start),list(line.dxf.end)],layer=line.dxf.layer))
    return output


def candidates(doc,graph,text,items):
    native=doc.entitydb[text['handle']]
    if not supported(native):raise ValueError('unsupported repeated-layout text transform')
    angle=math.radians(text['rotation']);u=[math.cos(angle),math.sin(angle)];normal=[-u[1],u[0]];result=[]
    model=[dict(root_handle=None,root_block=None,child_handle=line.dxf.handle,root_linear_pose=None,XYZ=[list(line.dxf.start),list(line.dxf.end)],layer=line.dxf.layer)
        for line in doc.modelspace().query('LINE') if line.dxf.layer in LAYERS.values()]
    for item in model+items:
        a,b=[p[:2] for p in item['XYZ']];length=math.dist(a,b)
        if length<=.05 or abs(u[0]*(b[1]-a[1])-u[1]*(b[0]-a[0]))/length>math.sin(math.radians(2)):continue
        q=_projection(text['position'],a,b)
        if not q or not 0<q[0]<1 or q[1]>2*text['height']:continue
        z=item['XYZ'][0][2]+q[0]*(item['XYZ'][1][2]-item['XYZ'][0][2]);tz=doc.entitydb[text['handle']].dxf.insert.z
        owners=[e['edge_id'] for e in graph['edges'] if e.get('source_insert_handle')==item['root_handle'] and e['system'] in LAYERS and LAYERS[e['system']]==item['layer']
            and any(_on(q[2],x,y,.05) and _on(x,a,b,.05) and _on(y,a,b,.05) for p in e.get('attribute_paths',[]) for x,y in zip(p,p[1:]))] if item['root_handle'] else []
        result.append(dict(item,projection=list(q[2]),fraction=q[0],distance=q[1],signed_normal_offset=sum((text['position'][i]-q[2][i])*normal[i] for i in (0,1)),
            text_source_Z=tz,line_source_Z=z,Z_coincident=abs(z-tz)<=.05,current_graph_owners=owners))
    return sorted(result,key=lambda x:(x['distance'],x['root_handle'] or '',x['child_handle']))


def signature(row):return row['root_block'],row['child_handle'],tuple(row['root_linear_pose'] or [])


def collect(doc,graph,handles,source_hash,graph_hash):
    if not handles or len(handles)!=len(set(handles)) or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('invalid repeated-layout DN source or target scope')
    texts=source_texts(doc,'axis',source_hash);by={t['handle']:t for t in texts}
    if not set(handles)<=by.keys():raise ValueError('missing repeated-layout source text')
    layers=sorted({by[h]['layer'] for h in handles});F={t['handle'] for f in recognize_f_leaders(doc,texts,[],graph['edges'],layers) for t in f['texts']}
    if F.intersection(handles):raise ValueError('F text requires its ordered leader rule')
    items=primitives(doc,graph)
    # The old bulk screen is only a discovery aid. Each control is independently
    # rechecked below against all modelspace and decomposed source competitors.
    bulk=screen(doc,graph,dict(source_layer_systems={v:k for k,v in LAYERS.items()},text_layers=layers,include_graph_insert_lines=True))
    controls=[]
    for row in bulk['records']:
        h=row['text_handle']
        if h in handles or h in F or row['status']!='unique_source_line_and_graph_segment_candidate':continue
        t=by[h];hits=candidates(doc,graph,t,items)
        if not hits or not hits[0]['root_handle'] or not hits[0]['Z_coincident'] or len(hits[0]['current_graph_owners'])!=1:continue
        if len(hits)>1 and hits[1]['distance']-hits[0]['distance']<=.5*t['height']:continue
        parsed=parse_dn_annotation(t['text'])
        if not parsed or not .05<abs(hits[0]['signed_normal_offset']):continue
        controls.append(dict(source_text=t,text_profile=profile(doc,doc.entitydb[h]),native_binding=hits[0]))
    records=[]
    for h in handles:
        t=by[h];parsed=parse_dn_annotation(t['text'])
        if not parsed:raise ValueError('repeated-layout DN must be a scalar annotation')
        hits=candidates(doc,graph,t,items);matches=[];rejected=[]
        for hit in hits:
            same=[c for c in controls if c['text_profile']==profile(doc,doc.entitydb[h]) and c['source_text']['rotation']==t['rotation']
                and signature(c['native_binding'])==signature(hit) and abs(c['native_binding']['signed_normal_offset']-hit['signed_normal_offset'])<=.05]
            independent={c['native_binding']['root_handle'] for c in same}
            if hit['root_handle'] in independent:raise ValueError('target native instance cannot also calibrate itself')
            if (hit['root_handle'] and len(independent)>=4 and hit['Z_coincident'] and len(hit['current_graph_owners'])==1
                and min(c['native_binding']['fraction'] for c in same)-.01<=hit['fraction']<=max(c['native_binding']['fraction'] for c in same)+.01):
                matches.append((hit,same))
            else:rejected.append(dict(candidate=hit,reason='does_not_match_independent_exact_native_instance_layout_and_source_owner'))
        if len(matches)!=1:raise ValueError('repeated native DN layout does not identify one source branch')
        hit,same=matches[0]
        records.append(dict(source_text=t,nominal_mm_candidate=parsed['nominal_mm'],source_chain=[hit['root_handle'],hit['child_handle']],
            current_edge_id=hit['current_graph_owners'][0],native_binding=hit,independent_control_text_handles=sorted(c['source_text']['handle'] for c in same),
            independent_control_roots=sorted({c['native_binding']['root_handle'] for c in same}),rejected_competing_source_pipes=rejected,
            scope='native_nested_branch_annotation_only_not_whole_edge_DN',whole_edge_DN_assigned=False,human_accepted=False))
    return dict(status='native_repeated_instance_layout_binds_selected_DN_to_other_branches',source_sha256=source_hash,graph_sha256=graph_hash,
        records=records,controls=controls,target_texts_used_as_controls=False,graph_mutated=False,physical_values_fused=False,human_accepted=False)
