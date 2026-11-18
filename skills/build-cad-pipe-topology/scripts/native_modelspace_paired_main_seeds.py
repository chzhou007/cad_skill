"""Inherit the existing native pair owner as modelspace main DN seeds.

Pair geometry, not DN/parentheses or nearest text, owns each source LINE.
All old competitors, F priority and source Z checks remain in force.
"""
import ast,copy,inspect,types
from confirm_crossview_paths import encode
from native_paired_caption_geometry import collect as paired_geometry
from pipe_annotation_attributes import source_texts
from axis_unbranched_vertical_DN import source_Z,source_key,native_items
from axis_continuous_source_vertical_DN import through_line_evidence
from source_direct_dn_evidence import _projection
from native_line_path_evidence import _on,LAYERS
import native_multiline_main_T_DN as inherited

MODE='inherited_modelspace_paired_caption_main_seed_composition_v1'

def local_source_candidates(doc,current,entry,nodes,rows,items,candidates):
    point=[nodes[entry]['x'],nodes[entry]['y']];hits=[(pi,side)for pi,p in enumerate(current['attribute_paths'])for side in(0,-1)if sum((p[side][i]-point[i])**2 for i in(0,1))<=.05**2]
    if len(hits)!=1:raise ValueError('one source path at current main entry required')
    pi,side=hits[0];si=0 if side==0 else len(current['attribute_paths'][pi])-2;scope=rows[current['edge_id'],pi,si];_,proof=inherited.source_path_chain(current,entry,nodes,rows,items,scope);native=proof['native_chain'][0]
    local=[s for s in candidates if native['root_handle']is None and s['source_line_handle']==native['child_handle']]
    return local or candidates

def reader():
    """Adapt only seed selection; every original geometry/barrier statement stays.

    Fail closed if the upstream assignment changes. The old registered module
    and its receipts remain immutable; the adapter is a separately tested asset.
    """
    tree=ast.parse(inspect.getsource(inherited.collect));expected=ast.parse("on=[s for s in byedge[current_id]if s['system']==edge['system']]").body[0];hits=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Assign)and ast.dump(node,include_attributes=False)==ast.dump(expected,include_attributes=False):hits.append(node)
    if len(hits)!=1:raise ValueError('original main seed-selection seam changed; requalify adapter')
    original=hits[0].value;hits[0].value=ast.Call(func=ast.Name(id='local_source_candidates',ctx=ast.Load()),args=[ast.Name(id=n,ctx=ast.Load())for n in('doc','current','entry','nodes','rows','items')]+[original],keywords=[]);ast.fix_missing_locations(tree);namespace=dict(inherited.collect.__globals__,local_source_candidates=local_source_candidates);exec(compile(tree,__file__,'exec'),namespace);return namespace['collect']

def seeds(doc,graph,route,sh,gh,items=None):
    before=encode(graph),encode(route);old=inherited.modelspace_seeds(doc,graph,route,sh,gh);paired=paired_geometry(doc);texts={t['handle']:t for t in source_texts(doc,'axis',sh)};anchors=[];new=[];held=[];expanded=[];cache={};seen={(source_key(s),o['source_text']['handle'])for s in old['records']for o in s['observations']};items=native_items(doc,graph)if items is None else items
    def eligible(line,system):
        return[s for s in route['records']if s['system']==system and s['native_source_status']=='single_source_line_covers'and s['native_witnesses'][0]['scope']=='modelspace'and s['native_witnesses'][0]['source_handle']==line.dxf.handle and all(_on(p,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)for p in s['scope_points'])]
    for pair in paired['pairs']:
        if pair['DN_or_level_used_to_choose_pipe']is not False or pair['physical_level_or_units_inferred']is not False:raise ValueError('pair owner must remain geometric only')
        for observation in pair['observations']:
            t=observation['text'];pipe=observation['native_pipe'];line=doc.entitydb.get(pipe['source_LINE']);entity=doc.entitydb.get(t['handle'])
            if line is None or line not in doc.modelspace()or line.dxftype()!='LINE'or entity is None or entity not in doc.modelspace():raise ValueError('original modelspace source pair changed')
            item=dict(XYZ=[list(line.dxf.start),list(line.dxf.end)]);text=texts[t['handle']]
            if line.dxf.layer!=LAYERS[pipe['system']]or abs(entity.dxf.insert.z-source_Z(item,t['position']))>.05:held.append(dict(text_handle=t['handle'],reason='native source caption Z or layer mismatch'));continue
            scopes=eligible(line,pipe['system'])
            if not scopes:held.append(dict(text_handle=t['handle'],reason='native pair has no original graph segment'));continue
            owners=[s for s in old['records']if any(o['source_text']['handle']==t['handle']for o in s['observations'])]
            if any(s['source_line_handle']!=line.dxf.handle or s['system']!=pipe['system']for s in owners):raise ValueError('original direct and paired native owners disagree')
            if owners:continue
            a,b=item['XYZ'];projection=_projection(t['position'],a[:2],b[:2])
            if projection is None:raise ValueError('native pair source LINE degenerate')
            point=projection[2]if 0<=projection[0]<=1 else min((a[:2],b[:2]),key=lambda p:sum((p[i]-t['position'][i])**2 for i in(0,1)))
            local=[s for s in scopes if _on(point,*s['scope_points'],.05)]
            if len(local)!=1:held.append(dict(text_handle=t['handle'],reason='pair projection lacks one original local annotation scope'));continue
            s=local[0];anchors.append(dict(edge_id=s['edge_id'],path_index=s['path_index'],segment_index=s['segment_index'],scope_points=copy.deepcopy(s['scope_points']),system=s['system'],direction_class=s['direction_class'],nominal_mm=t['nominal_mm'],source_line_handle=line.dxf.handle,source_Z=source_Z(item,point),observations=[dict(source_text=copy.deepcopy(text),nominal_mm=t['nominal_mm'],native_evidence=dict(pair=copy.deepcopy(pair),observation=copy.deepcopy(observation),original_pair_geometry_replayed=True))],horizontal_final_value_assigned=False))
    # Direct and paired owners have equal source-LINE priority. A local direct
    # caption must not lose to a remote different-LINE seed merely because only
    # paired captions were expanded to the current T cuts.
    for seed in old['records']+anchors:
        line=doc.entitydb[seed['source_line_handle']]
        for s in eligible(line,seed['system']):
            h=seed['observations'][0]['source_text']['handle'];k=source_key(s),h
            if k in seen:continue
            try:
                evidence=through_line_evidence(doc,graph,s,seed,items,sh,gh,cache)
                row=copy.deepcopy(seed);row.update(edge_id=s['edge_id'],path_index=s['path_index'],segment_index=s['segment_index'],scope_points=copy.deepcopy(s['scope_points']),direction_class=s['direction_class'],source_scope_expansion=evidence);new.append(row);seen.add(k);expanded.append(dict(text_handle=h,source_domain=list(source_key(seed)),target_domain=list(source_key(s)),source_LINE=line.dxf.handle,native_continuity=evidence))
            except ValueError as exc:held.append(dict(text_handle=h,target_domain=list(source_key(s)),reason=str(exc)))
    if before!=(encode(graph),encode(route)):raise ValueError('source graph or routing mutated')
    return dict(old,records=old['records']+new,inherited_modelspace_pair_geometry=paired,new_paired_caption_anchors=anchors,new_source_LINE_seeds=new,source_LINE_scope_expansions=expanded,source_T_cache=cache,paired_source_held=held,old_direct_seeds_preserved=True,direct_and_paired_LINE_priority_equal=True,new_values_are_seed_evidence_only=True,physical_lengths_assigned=0)

def collect(doc,graph,route,parent,items,sh,gh):
    # The original main/T/bend/barrier owner is called unchanged. It checks full
    # root-main LINE extents and the complete target branch after pairing.
    def source_seeds(*args):return seeds(*args,items=items)
    original=reader();adapted=types.FunctionType(original.__code__,dict(original.__globals__,modelspace_seeds=source_seeds),original.__name__,original.__defaults__,original.__closure__)
    result=adapted(doc,graph,route,parent,items,sh,gh);result.update(mode=MODE,inherited_pair_geometry_main_seeds=True,original_native_geometry_and_barriers_unchanged=True,source_local_seed_priority_applied=True);return result
