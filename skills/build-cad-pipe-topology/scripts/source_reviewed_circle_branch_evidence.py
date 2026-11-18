"""Replay the older source-reviewed circle schema without rewriting its graph.

The source branch may end at a circle rim and contain independently verified
opposite-system crossover gaps. Neither span is a measured connector.
"""
import copy,hashlib,math
from pathlib import Path
from source_reviewed_circle_connections import load_review,candidate
from native_line_path_evidence import LAYERS,_on
from confirm_crossview_paths import encode


def repair_root(graph,key,node_id,handle,binding_key,binding,source_hash):
    root=graph.get(key);seen=set();matches=[]
    while isinstance(root,dict):
        if id(root) in seen:raise ValueError('cyclic circle repair history')
        seen.add(id(root))
        records=[r for r in root.get('records',[]) if r.get('circle_handle')==handle and r.get('tee')==node_id]
        if records:
            if len(records)!=1 or root.get(binding_key)!=binding:raise ValueError('circle history has conflicting binding')
            matches.append(root)
        root=root.get('previous_repair')
    if len(matches)!=1:raise ValueError('circle lacks one source-bound historical repair')
    root=matches[0]
    if root.get('source_sha256')!=source_hash or root.get('supply_return_independent') is not True or root.get('physical_length')!='unknown':raise ValueError('reviewed circle source/root binding differs')
    return root


def historical_control_parent(graph,root,meta,row,source_hash):
    """A retired terminal is checked on its real immutable parent, never faked."""
    if not row.get('confirmed_plan_control'):return graph,None
    from confirm_crossview_paths import load,sha
    path=Path(meta['source_comparison']['review_manifest']).with_name('manifest.json')
    manifest=load(path);parent_path=Path(manifest['graph']);expected=root['input_graph_sha256']
    if (manifest.get('source_sha256')!=source_hash or manifest.get('graph_sha256')!=expected
        or meta.get('source_graph_sha256')!=expected or sha(parent_path)!=expected):raise ValueError('3D circle control historical parent changed')
    parent=load(parent_path)
    if parent.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('3D circle parent source differs')
    record=next(r for r in root['records'] if r.get('circle_handle')==meta['circle_handle'])
    before=next((e for e in parent['edges'] if e['edge_id']==record['branch_edge']),None)
    current=next((e for e in graph['edges'] if e['edge_id']==record['branch_edge']),None)
    terminal=next((n for n in parent['nodes'] if n['node_id']==record['retired_terminal']),None)
    node=next(n for n in graph['nodes'] if n['node_id']==record['tee'])
    if (not before or not current or not terminal or terminal.get('subtype')!='unresolved_source_terminal'
        or terminal.get('floor')!=node.get('floor') or row['branch_handle'] not in before.get('source_handles',[])
        or row['branch_handle'] not in current.get('source_handles',[]) or before.get('system')!=current.get('system')):raise ValueError('3D circle retired terminal/current branch binding differs')
    controls=[n for n in graph['nodes'] if n.get('user_confirmed_circle',{}).get('circle_handle')==row['confirmed_plan_control']['circle_handle']]
    if len(controls)!=1:raise ValueError('current 3D circle reference control is not unique')
    return parent,dict(parent_graph_sha256=expected,manifest_sha256=sha(path),retired_terminal=record['retired_terminal'],current_control_node_id=controls[0]['node_id'])


def recorded_z(doc,meta,circle,main,branch,rim):
    native_main=doc.entitydb[main['handle']];native_branch=doc.entitydb[branch['handle']]
    if any(not math.isfinite(v) for point in (circle.dxf.center,native_main.dxf.start,native_main.dxf.end,native_branch.dxf.start,native_branch.dxf.end) for v in point):raise ValueError('nonfinite native circle/pipe coordinate')
    a,b=native_main.dxf.start,native_main.dxf.end;dx,dy=b.x-a.x,b.y-a.y
    t=((circle.dxf.center.x-a.x)*dx+(circle.dxf.center.y-a.y)*dy)/(dx*dx+dy*dy)
    ends=[p for p in (native_branch.dxf.start,native_branch.dxf.end) if math.dist(list(p)[:2],rim)<=.05]
    if len(ends)!=1:raise ValueError('circle native rim endpoint ambiguous')
    actual=dict(circle_z=circle.dxf.center.z,main_z_at_center=a.z+t*(b.z-a.z),branch_z_at_rim=ends[0].z)
    if any(k in meta and (isinstance(meta[k],bool) or not isinstance(meta[k],(int,float)) or not math.isfinite(meta[k]) or abs(meta[k]-v)>.05) for k,v in actual.items()):raise ValueError('recorded native circle Z changed')
    return actual


def collect(doc,graph,node_id,source_hash,graph_hash):
    nodes={n['node_id']:n for n in graph['nodes']};node=nodes[node_id]
    incident=[e for e in graph['edges'] if node_id in (e.get('start_node_id'),e.get('end_node_id'))]
    if (node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True
        or len(incident)!=3 or len({e['edge_id'] for e in incident})!=3
        or {e.get('system') for e in incident}!={node.get('system')} or node.get('system') not in LAYERS):raise ValueError('reviewed circle T incidence unresolved or mixed')
    meta=node.get('source_reviewed_circle',{})
    comparison=meta.get('source_comparison',{})
    root=repair_root(graph,'sourceReviewedCircleJunctionRepair',node_id,meta.get('circle_handle'),'source_comparison',comparison,source_hash)
    if comparison.get('human_accepted') is not False:raise ValueError('reviewed circle source/root binding differs')
    review=load_review(dict(comparison,source_sha256=source_hash),source_hash)
    handle=meta.get('circle_handle');row=review.get(handle)
    records=[r for r in root.get('records',[]) if r.get('circle_handle')==handle and r.get('tee')==node_id]
    if not row or len(records)!=1:raise ValueError('reviewed circle lacks unique native review/repair')
    record=records[0];branches=[e for e in incident if e['edge_id']==record.get('branch_edge')]
    if len(branches)!=1 or record.get('system')!=node['system']:raise ValueError('reviewed branch identity differs')
    branch=branches[0]
    if branch.get('source_reviewed_circle_connection')!=meta:raise ValueError('reviewed circle node/branch evidence differs')
    circle=doc.entitydb.get(handle)
    if circle is None or circle.dxftype()!='CIRCLE':raise ValueError('reviewed native circle missing')
    reverse={v:k for k,v in LAYERS.items()}
    spec=dict(handle=handle,system=reverse.get(circle.dxf.layer),center=(circle.dxf.center.x,circle.dxf.center.y),radius=circle.dxf.radius)
    segments=[dict(handle=l.dxf.handle,system=reverse[l.dxf.layer],a=list(l.dxf.start)[:2],b=list(l.dxf.end)[:2]) for l in doc.modelspace().query('LINE') if l.dxf.layer in reverse]
    parent,parent_evidence=historical_control_parent(graph,root,meta,row,source_hash)
    if parent_evidence:parent_evidence['current_control_evidence']=collect_user(doc,graph,parent_evidence['current_control_node_id'],source_hash,graph_hash)
    main,(native_branch,_,rim)=candidate(doc,spec,segments,review,graph=parent)
    z_evidence=recorded_z(doc,meta,circle,main,native_branch,rim)
    p=[node['x'],node['y']]
    if (row['system']!=node['system'] or math.dist(p,spec['center'])>.05 or math.dist(p,meta.get('center',[]))>.05
        or math.dist(rim,meta.get('source_rim',[]))>.05 or meta.get('line_system')!=node['system']
        or meta.get('graphic_radius_is_physical_length') is not False or meta.get('physical_length')!='unknown'
        or native_branch['handle'] not in branch.get('source_handles',[])
        or meta.get('source_graph_sha256')!=root.get('input_graph_sha256') or meta.get('screen_sha256')!=root.get('screen_sha256')):raise ValueError('reviewed circle current geometry/provenance differs')
    rays=circle_rays(doc,graph,node,incident,branch,record,main,native_branch,rim,source_hash)
    return dict(status='native_historical_circle_ray_evidence_unreviewed',source_sha256=source_hash,graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id,system=node['system'],position=p,source_rays=rays,status='source_circle_contact_replayed_not_human_accepted')],
        source_review=dict(comparison,pair_sha256=row['pair_sha256']),historical_control_parent=parent_evidence,native_Z=z_evidence,graph_mutated=False,hil_ready=False)


def main_membership(graph,edge,record,source_hash):
    if edge['edge_id'] in record.get('main_child_edges',[]):return
    from confirm_crossview_paths import load,sha
    from repair_confirmed_circle_junctions import slice_path
    split=edge.get('split_source_edge',{});parent_id=split.get('edge_id')
    if parent_id not in record.get('main_child_edges',[]):raise ValueError('reviewed main child identity differs')
    roots=[];root=graph.get('sourceReviewedCircleJunctionRepair');seen=set()
    while isinstance(root,dict):
        if id(root) in seen:raise ValueError('cyclic main split history')
        seen.add(id(root))
        if root.get('input_graph_sha256')==split.get('source_graph_sha256'):
            matches=[r for r in root.get('records',[]) if r.get('main_source_edge')==parent_id and edge['edge_id'] in r.get('main_child_edges',[])]
            if matches:roots.append(root)
        root=root.get('previous_repair')
    if len(roots)!=1 or roots[0].get('source_sha256')!=source_hash:raise ValueError('main descendant lacks one source-reviewed split')
    root=roots[0];review=load_review(dict(root['source_comparison'],source_sha256=source_hash),source_hash)
    if not review:raise ValueError('main split source review missing')
    manifest=load(Path(root['source_comparison']['review_manifest']).with_name('manifest.json'));path=Path(manifest['graph'])
    if manifest.get('source_sha256')!=source_hash or manifest.get('graph_sha256')!=split['source_graph_sha256'] or sha(path)!=split['source_graph_sha256']:raise ValueError('main split historical parent changed')
    parent=load(path);old=next((e for e in parent['edges'] if e['edge_id']==parent_id),None);interval=split.get('interval_native_units')
    if not old or old['system']!=edge['system'] or not isinstance(interval,list) or len(interval)!=2:raise ValueError('main split parent/interval differs')
    expected=slice_path(old['path'],*interval);actual=edge.get('path')
    if not actual or len(actual)!=len(expected) or any(math.dist(a,b)>.05 for a,b in zip(actual,expected)) or not set(edge.get('source_handles',[]))<=set(old.get('source_handles',[])):raise ValueError('current main descendant leaves source parent interval')


def circle_rays(doc,graph,node,incident,branch,record,main,native_branch,rim,source_hash):
    p=[node['x'],node['y']];rays=[];directions=[];handle=doc.entitydb.get(node.get('source_reviewed_circle',node.get('user_confirmed_circle',{})).get('circle_handle')).dxf.handle
    for edge in incident:
        if edge is branch:
            ends=[]
            for path in edge.get('attribute_paths',[]):
                if len(path)<2:raise ValueError('invalid reviewed branch path')
                if math.dist(path[0],rim)<=.05:ends.append((path[0],path[1]))
                if math.dist(path[-1],rim)<=.05:ends.append((path[-1],path[-2]))
            if len(ends)!=1:raise ValueError('reviewed rim is not a unique source endpoint')
            a,b=ends[0]
            if not all(_on(q,native_branch['a'],native_branch['b'],.05) for q in (a,b)):raise ValueError('reviewed rim ray leaves native branch')
            item=dict(edge_id=edge['edge_id'],scope='historical_source_reviewed_circle_rim',source_branch_line_handle=native_branch['handle'],source_main_line_handle=main['handle'],circle_handle=handle,branch_rim=list(rim),physical_connector_length=None)
        else:
            main_membership(graph,edge,record,source_hash)
            touches=[]
            for path in edge.get('attribute_paths',[]):
                for a,b in zip(path,path[1:]):
                    if math.dist(a,p)<=.05 and math.dist(b,p)>.05:touches.append((a,b))
                    elif math.dist(b,p)<=.05 and math.dist(a,p)>.05:touches.append((b,a))
            if len(touches)!=1:raise ValueError('reviewed main graph ray ambiguous')
            a,b=touches[0]
            hits=[l.dxf.handle for l in doc.modelspace().query('LINE') if l.dxf.layer==LAYERS[node['system']] and _on(a,list(l.dxf.start)[:2],list(l.dxf.end)[:2],.05) and _on(b,list(l.dxf.start)[:2],list(l.dxf.end)[:2],.05)]
            if hits!=[main['handle']] or main['handle'] not in edge.get('source_handles',[]):raise ValueError('reviewed native main ray ambiguous or changed')
            item=dict(edge_id=edge['edge_id'],source_line_handle=main['handle'])
        length=math.dist(a,b)
        if length<=.05:raise ValueError('zero reviewed circle ray')
        direction=[(b[i]-a[i])/length for i in (0,1)]
        if any(sum(x*y for x,y in zip(direction,v))>math.cos(math.radians(.1)) for v in directions):raise ValueError('coincident reviewed circle rays')
        directions.append(direction);rays.append(dict(item,graph_segment=[a,b],direction=direction))
    return rays


def collect_user(doc,graph,node_id,source_hash,graph_hash):
    from cad_ceiling_native_rules import radial_circle_connection_candidate,match_out_of_plane_symbol,on
    node=next(n for n in graph['nodes'] if n['node_id']==node_id);meta=node.get('user_confirmed_circle',{});confirmation=meta.get('confirmation',{})
    if confirmation.get('confirmed_by')!='user' or not confirmation.get('question') or not confirmation.get('answer'):raise ValueError('circle lacks explicit historical user confirmation')
    handle=meta.get('circle_handle');root=repair_root(graph,'userConfirmedCircleJunctionRepair',node_id,handle,'confirmation',confirmation,source_hash)
    records=[r for r in root['records'] if r.get('circle_handle')==handle and r.get('tee')==node_id];record=records[0]
    incident=[e for e in graph['edges'] if node_id in (e.get('start_node_id'),e.get('end_node_id'))]
    if node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True or len(incident)!=3 or {e.get('system') for e in incident}!={node.get('system')}:raise ValueError('user circle current incidence differs')
    branch=next((e for e in incident if e['edge_id']==record['branch_edge']),None);circle=doc.entitydb.get(handle)
    if (not branch or branch.get('source_user_circle_connection')!=meta or record.get('system')!=node.get('system')
        or not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace() or tuple(circle.dxf.extrusion)!=(0.,0.,1.)
        or circle.dxf.layer not in LAYERS.values() or circle.dxf.layer!=meta.get('circle_layer') or meta.get('line_system')!=node.get('system') or node.get('system') not in LAYERS
        or meta.get('source_graph_sha256')!=root.get('input_graph_sha256') or meta.get('screen_sha256')!=root.get('screen_sha256')
        or meta.get('graphic_radius_is_physical_length') is not False or meta.get('physical_length')!='unknown'):raise ValueError('user circle source/graph binding differs')
    reverse={v:k for k,v in LAYERS.items()};segments=[dict(handle=l.dxf.handle,system=reverse[l.dxf.layer],a=list(l.dxf.start)[:2],b=list(l.dxf.end)[:2]) for l in doc.modelspace().query('LINE') if l.dxf.layer in reverse]
    spec=dict(handle=handle,system=node['system'],center=list(circle.dxf.center)[:2],radius=circle.dxf.radius)
    match=radial_circle_connection_candidate(spec,segments)
    if match is None:raise ValueError('user circle native contact no longer unique')
    main,(native_branch,_,rim)=match;p=[node['x'],node['y']]
    if math.dist(p,spec['center'])>.05 or math.dist(p,meta.get('center',[]))>.05 or math.dist(rim,meta.get('source_rim',[]))>.05 or native_branch['handle'] not in branch.get('source_handles',[]):raise ValueError('user circle native geometry changed')
    glyphs=[dict(a=list(e.dxf.start)[:2],b=list(e.dxf.end)[:2]) for e in doc.modelspace().query('LINE') if e.dxf.layer=='空调立管、水平支管']
    if match_out_of_plane_symbol(spec,glyphs) or any(min(math.dist(p,g['a']),math.dist(p,g['b']))<=circle.dxf.radius+.05 for g in glyphs):raise ValueError('user circle has interface glyph interference')
    if any(s['system']!=node['system'] and on(p,s['a'],s['b']) is not None for s in segments):raise ValueError('opposite system crosses user circle center')
    z=recorded_z(doc,meta,circle,main,native_branch,rim);rays=circle_rays(doc,graph,node,incident,branch,record,main,native_branch,rim,source_hash)
    return dict(status='native_user_confirmed_circle_ray_evidence_replayed',source_sha256=source_hash,graph_sha256=graph_hash,
        junctions=[dict(node_id=node_id,system=node['system'],position=p,source_rays=rays,status='historical_user_circle_contact_replayed')],native_Z=z,graph_mutated=False,hil_ready=False,physical_ports_verified=False,human_accepted=False)


def branch_coverage(doc,graph,edge,source_hash,graph_hash):
    """Recheck every real path and every excluded crossover using old rules.

    Explicit current projections have their own hashes. They are not relabelled
    as the old source-gap or fragment artifacts cited by the edge's history.
    """
    from reconstruct_native_block_branches import projected_coverage
    from correct_plan_crossover_lengths import apply
    paths=edge.get('attribute_paths',[]);gaps=edge.get('source_normalized_crossovers',[])
    if not paths or len(paths)!=len(gaps)+1:raise ValueError('unexplained reviewed branch path discontinuity')
    coverage=projected_coverage(doc,graph,edge['edge_id'],source_hash)
    if any(s['status']!='single_source_line_covers' for p in coverage for s in p['coverage']['segments']):raise ValueError('reviewed branch lacks unique source path coverage')
    adjacency={i:set() for i in range(len(paths))};replays=[]
    for entry in gaps:
        if entry.get('source_sha256')!=source_hash or len(entry.get('crossings',[]))!=1:raise ValueError('stale or ambiguous reviewed crossover')
        projected_gap=dict(id=entry['source_gap_id'],source_handles=entry['source_handles'],status='applied',crossing_connectivity=entry['crossing_connectivity'],a=entry['a'],b=entry['b'])
        fragment=dict(normalization='source_straight_crossover_gap',source_handles=entry['source_handles'],a=entry['a'],b=entry['b'],crossing_connectivity=entry['crossing_connectivity'],system=edge['system'],crossings=entry['crossings'])
        digest=lambda v:hashlib.sha256(encode(v)).hexdigest()
        gh,fh=digest([projected_gap]),digest([fragment])
        policy=dict(source_sha256=source_hash,graph_sha256=graph_hash,gaps_sha256=gh,fragments_sha256=fh,gap_ids=[entry['source_gap_id']])
        _,audit=apply(doc,graph,[projected_gap],[fragment],policy,source_hash,graph_hash,gh,fh)
        if audit['records']!=[dict(gap_id=entry['source_gap_id'],edge_id=edge['edge_id'],status='already_excluded',gap_drawing_units=math.dist(entry['a'],entry['b']))]:raise ValueError('reviewed crossover was not already excluded')
        hits=[[i for i,path in enumerate(paths) if min(math.dist(q,path[0]),math.dist(q,path[-1]))<=.05] for q in (entry['a'],entry['b'])]
        if any(len(x)!=1 for x in hits) or hits[0]==hits[1]:raise ValueError('reviewed crossover endpoints ambiguous')
        a,b=hits[0][0],hits[1][0]
        if b in adjacency[a]:raise ValueError('repeated reviewed crossover connection')
        adjacency[a].add(b);adjacency[b].add(a)
        replays.append(dict(source_gap_id=entry['source_gap_id'],projection_gap_sha256=gh,projection_fragment_sha256=fh,native_replay=audit))
    seen=set();stack=[0]
    while stack:
        i=stack.pop()
        if i not in seen:seen.add(i);stack.extend(adjacency[i]-seen)
    if len(seen)!=len(paths) or any(len(v)>2 for v in adjacency.values()):raise ValueError('reviewed source paths are not one crossover-linked chain')
    return dict(status='native_source_paths_and_excluded_crossovers_replayed',paths=coverage,crossovers=replays,physical_length_mm=None,graph_mutated=False)
