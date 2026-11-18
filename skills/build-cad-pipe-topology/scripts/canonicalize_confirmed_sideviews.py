"""Reuse a source-verified detail T instead of duplicating its confirmed main view.

This stage does not infer the identity of projected overlapping mains. It keeps
the detail network and its existing segmentation, archives the abbreviated
source expression, and invalidates downstream evidence. Unknown destinations
and connections at the detail network's ends remain unknown.
"""
import argparse
from collections import Counter
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from source_readability import read_source
from native_line_path_evidence import LAYERS, _on

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
TOL=.05
DECISION='对应同一组管路'

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'sideview-canonicalization-audit.json')
    if audit['script_sha256']!=sha(__file__):raise ValueError('stale side-view implementation')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('stale side-view input')
    with tempfile.TemporaryDirectory() as temp:
        out=Path(temp)/'replay';cmd=[sys.executable,'-X','utf8',str(Path(__file__))]
        for name,item in audit['inputs'].items():cmd.extend(['--'+name,item['path']])
        subprocess.run(cmd+['--output',str(out)],check=True,stdout=subprocess.DEVNULL)
        for name in ('graph_with_canonical_sideviews.json','assigned_edge_device_instances.csv'):
            if sha(out/name)!=sha(directory/name):raise ValueError('side-view replay differs: '+name)
    if sha(directory/'graph_with_canonical_sideviews.json')!=audit['output_graph_sha256']:raise ValueError('stale output graph')
    return audit

def point(node):return [node['x'],node['y']]

def source_expression_context(graph):
    """Read-only CAD expression context for historical glyph/frame diagnostics.

    Archived glyphs are available to geometry comparisons, never reinstated in
    the active physical graph or its connectivity. Full acceptance still needs
    the independently replayed canonicalization stage.
    """
    state=graph.get('confirmedSideviewCanonicalization')
    if state is None:return graph
    nodes=state.get('representation_only_nodes');edges=state.get('representation_only_edges')
    if not isinstance(nodes,list) or not isinstance(edges,list):raise ValueError('missing archived source expressions')
    active_nodes={n['node_id'] for n in graph['nodes']};active_edges={e['edge_id'] for e in graph['edges']}
    if (len({n['node_id'] for n in nodes})!=len(nodes) or len({e['edge_id'] for e in edges})!=len(edges)
        or any(n['node_id'] in active_nodes or n.get('node_type')=='equipment' for n in nodes)
        or any(e['edge_id'] in active_edges or e.get('equipment_names') or e.get('equipment_counts') for e in edges)):
        raise ValueError('archived expression overlaps active physical graph')
    context=copy.deepcopy(graph);context['nodes']+=copy.deepcopy(nodes);context['edges']+=copy.deepcopy(edges)
    context['source_expression_context_only']=True
    return context

def native_branch(doc,edge):
    if len(edge.get('source_handles',[]))!=1:raise ValueError('branch is not one witnessed native LINE')
    entity=doc.entitydb.get(edge['source_handles'][0])
    if (not entity or entity.dxftype()!='LINE' or entity not in doc.modelspace()
        or entity.dxf.layer!=LAYERS[edge['system']]):raise ValueError('native branch or service changed')
    actual=[[p.x,p.y] for p in (entity.dxf.start,entity.dxf.end)]
    paths=edge['attribute_paths']
    if (len(paths)!=1 or len(paths[0])!=2 or math.dist(*paths[0])<=TOL
        or not all(any(math.dist(p,q)<=TOL for q in actual) for p in paths[0])
        or abs(edge['path_length']-math.dist(*actual))>TOL):
        raise ValueError('branch source path changed')
    return entity

def canonical_detail_branch(doc,graph,branch):
    """Exclude a witnessed circle radius still counted in an older detail edge."""
    result=copy.deepcopy(branch)
    try:
        native_branch(doc,result)
        return result
    except ValueError:
        pass
    if len(branch.get('source_handles',[]))!=1:raise ValueError('ambiguous detail line')
    line=doc.entitydb.get(branch['source_handles'][0])
    if not line or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[branch['system']] or line not in doc.modelspace():
        raise ValueError('missing native detail pipe')
    path=branch['path']
    if len(path)!=2 or branch['attribute_paths']!=[path]:raise ValueError('detail native-path repair is not scoped')
    nodes={n['node_id']:n for n in graph['nodes']}
    tees=[nodes[n] for n in (branch.get('start_node_id'),branch.get('end_node_id')) if n in nodes and nodes[n].get('node_type')=='tee']
    if len(tees)!=1:raise ValueError('detail has no unique T')
    center=point(tees[0]);circle_end=0 if math.dist(path[0],center)<=TOL else 1 if math.dist(path[-1],center)<=TOL else None
    if circle_end is None:raise ValueError('detail center is not a branch endpoint')
    leaf=path[1-circle_end];ends=[[p.x,p.y] for p in (line.dxf.start,line.dxf.end)]
    if min(math.dist(leaf,p) for p in ends)>TOL:raise ValueError('detail endpoint disagrees with native line')
    rim=min(ends,key=lambda p:math.dist(p,center));radius=math.dist(rim,center)
    if radius<=TOL or not _on(rim,center,leaf,TOL):raise ValueError('native rim is outside detail branch')
    circles=[c for c in doc.modelspace().query('CIRCLE') if math.dist([c.dxf.center.x,c.dxf.center.y],center)<=TOL and abs(c.dxf.radius-radius)<=TOL]
    if len(circles)!=1:raise ValueError('detail circle witness missing or ambiguous')
    native_length=math.dist(*ends)
    if abs(branch['path_length']-native_length-radius)>TOL:raise ValueError('detail drawing length is not native plus circle radius')
    if any(k.startswith('diameter_') or k in ('physical_length','physical_length_mm','source_segment_dimensions') for k in branch):
        raise ValueError('detail attributes need explicit recomputation')
    native_path=[rim,leaf] if circle_end==0 else [leaf,rim]
    result.update(attribute_paths=[native_path],path_length=native_length,path_length_complete=False,
        path_length_scope='source_drawn_pipe_only_circle_interior_unknown',
        source_detail_circle_length_evidence=dict(source_circle_handle=circles[0].dxf.handle,
            source_line_handle=line.dxf.handle,circle_center=center,line_contact=rim,circle_radius_drawing_units=radius,
            circle_center_to_rim_is_display_only=True,physical_connection_length='unknown'))
    native_branch(doc,result)
    return result

def verify_tee(doc,graph,branch,terminal_id):
    branch=canonical_detail_branch(doc,graph,branch)
    ends=[branch.get('start_node_id'),branch.get('end_node_id')]
    boundaries=[branch.get('start_boundary_id'),branch.get('end_boundary_id')]
    if terminal_id not in ends+boundaries:raise ValueError('detail terminal is not on its branch')
    ids=[n for n in ends if n and n!=terminal_id]
    if len(ids)!=1:raise ValueError('detail branch does not have one main landing')
    nodes={n['node_id']:n for n in graph['nodes']};tee=nodes[ids[0]]
    if tee.get('node_type')!='tee' or tee.get('system')!=branch['system']:raise ValueError('detail landing is not a same-system T')
    incident=[e for e in graph['edges'] if tee['node_id'] in (e.get('start_node_id'),e.get('end_node_id'))]
    if len(incident)!=3 or any(e['system']!=branch['system'] for e in incident):raise ValueError('detail main was not rebuilt into three incident edges')
    center=point(tee);native_branch(doc,branch);rays=[];witnesses=[]
    for edge in incident:
        if edge['edge_id']==branch['edge_id']:edge=branch
        path=edge['path'] if edge['start_node_id']==tee['node_id'] else list(reversed(edge['path']))
        if math.dist(path[0],center)>TOL:raise ValueError('T edge misses its node')
        tip=next((p for p in path[1:] if math.dist(center,p)>TOL),None)
        if tip is None:raise ValueError('empty T ray')
        length=math.dist(center,tip);unit=[(tip[i]-center[i])/length for i in (0,1)]
        natives=[]
        for h in edge.get('source_handles',[]):
            e=doc.entitydb.get(h)
            if not e or e.dxftype()!='LINE' or e not in doc.modelspace() or e.dxf.layer!=LAYERS[edge['system']]:continue
            a,b=([v.x,v.y] for v in (e.dxf.start,e.dxf.end))
            if _on(center,a,b,TOL) and _on([center[i]+unit[i]*min(1.,length/2) for i in (0,1)],a,b,TOL):natives.append(h)
        if edge['edge_id']==branch['edge_id'] and not natives:
            proof=branch.get('source_detail_circle_length_evidence',{})
            circle=doc.entitydb.get(proof.get('source_circle_handle',''))
            contact=proof.get('line_contact',[])
            if (not circle or circle.dxftype()!='CIRCLE' or circle not in doc.modelspace()
                or math.dist([circle.dxf.center.x,circle.dxf.center.y],center)>TOL
                or len(contact)!=2 or abs(math.dist(contact,center)-circle.dxf.radius)>TOL
                or proof.get('source_line_handle') not in branch['source_handles']
                or math.dist(contact,branch['attribute_paths'][0][0])>TOL
                or sum((contact[i]-center[i])*unit[i] for i in (0,1))<=0):
                raise ValueError('detail circle-to-rim branch is not native witnessed')
            natives=[proof['source_line_handle']]
        if not natives:raise ValueError('detail main ray has no native witness')
        rays.append(unit);witnesses.append(dict(edge_id=edge['edge_id'],native_handles=natives))
    if any(math.dist(a,b)<.001 for i,a in enumerate(rays) for b in rays[i+1:]):raise ValueError('duplicate T rays')
    return dict(tee=tee['node_id'],incident_edges=[e['edge_id'] for e in incident],native_rays=witnesses),branch

def apply(doc,graph,rows,manifest,reply,selections,source_hash,graph_hash):
    if graph['metadata']['source_sha256']!=source_hash or manifest['source_sha256']!=source_hash or manifest['graph_sha256']!=graph_hash:
        raise ValueError('source or graph changed since the reviewed Pair')
    questions={};images={}
    for section in reply['sections']:
        for q in section['questions']:
            if q['id'] in questions:raise ValueError('duplicate reply question')
            questions[q['id']]=q;images[q['id']]=section['image']['sha256']
    nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
    if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph IDs')
    anchors={a['boundary_id']:a for a in graph.get('boundary_anchors',[])}
    retired_nodes=set();retired_edges=set();records=[];canonical_branches={}
    if not selections or len(set(selections))!=len(selections):raise ValueError('empty or repeated selection')
    for qid in selections:
        q=questions.get(qid)
        if not q or q.get('answer',{}).get('decision')!=DECISION:raise ValueError('missing explicit same-pipe correspondence')
        found=[(image,row) for image in manifest['images'] if image['sha256']==images[qid] for row in image['rows']
               if row['label'] in q['text'] and all(nid in q['text'] for nid,_ in row['upper']+row['detail'])]
        if len(found)!=1:raise ValueError('reply does not identify one exact reviewed Pair row')
        image,row=found[0]
        if not row['upper'] or len(row['upper'])!=len(row['detail']):raise ValueError('Pair row has unequal service lists')
        for (uid,ueid),(did,deid) in zip(row['upper'],row['detail']):
            upper,detail=edges[ueid],edges[deid]
            if upper['system']!=detail['system'] or uid not in nodes:raise ValueError('service or interface changed')
            interface=nodes[uid]
            if interface.get('subtype')!='out_of_plane_interface':raise ValueError('cannot retire an actual equipment instance')
            if sum(uid in (e.get('start_node_id'),e.get('end_node_id')) for e in graph['edges'])!=1:raise ValueError('upper interface has other connections')
            other=[x for x in (upper.get('start_node_id'),upper.get('end_node_id')) if x!=uid]
            if len(other)!=1 or other[0] not in nodes:raise ValueError('upper branch landing changed')
            terminal=nodes[other[0]]
            if terminal.get('subtype')!='unresolved_source_terminal' or sum(terminal['node_id'] in (e.get('start_node_id'),e.get('end_node_id')) for e in graph['edges'])!=1:
                raise ValueError('upper expression is not an isolated abbreviated branch')
            wave=upper.get('source_wave_terminal',{});entity=doc.entitydb.get(wave.get('source_wave_handle',''))
            if (not entity or entity.dxftype()!='INSERT' or entity not in doc.modelspace()
                or wave.get('endpoint_node_id')!=terminal['node_id'] or wave.get('source_sha256')!=source_hash):
                raise ValueError('upper source omission evidence changed')
            native_branch(doc,upper)
            if any(r['edge_id']==ueid for r in rows) or upper.get('equipment_names') or upper.get('equipment_counts'):
                raise ValueError('upper components require explicit instance correspondence before replacement')
            destination=nodes.get(did) or anchors.get(did)
            if not destination or destination.get('system')!=detail['system']:raise ValueError('detail interface or non-node boundary changed')
            proof,canonical_branch=verify_tee(doc,graph,detail,did)
            if deid in canonical_branches:raise ValueError('repeated canonical branch requires explicit many-to-one scope')
            canonical_branches[deid]=canonical_branch
            if uid in retired_nodes or terminal['node_id'] in retired_nodes or ueid in retired_edges:raise ValueError('repeated upper expression')
            retired_nodes.update((uid,terminal['node_id']));retired_edges.add(ueid)
            records.append(dict(question_id=qid,answer=copy.deepcopy(q['answer']),pair_sha256=image['sha256'],
                system=detail['system'],canonical_edge=deid,canonical_interface=did,
                canonical_interface_kind='node' if did in nodes else 'non_node_boundary',
                abbreviated_edge=ueid,abbreviated_interface=uid,retired_wave_terminal=terminal['node_id'],
                verified_detail_tee=proof,physical_length='unknown',projected_main_identity='not_inferred'))
    g=copy.deepcopy(graph)
    g['nodes']=[n for n in g['nodes'] if n['node_id'] not in retired_nodes]
    g['edges']=[canonical_branches.get(e['edge_id'],e) for e in g['edges'] if e['edge_id'] not in retired_edges]
    g['virtual_equipment_ports']=[p for p in g.get('virtual_equipment_ports',[]) if p['virtual_equipment_id'] not in retired_nodes]
    g['confirmedSideviewCanonicalization']=dict(source_sha256=source_hash,input_graph_sha256=graph_hash,
        records=records,representation_only_nodes=[copy.deepcopy(nodes[n]) for n in sorted(retired_nodes)],
        representation_only_edges=[copy.deepcopy(edges[e]) for e in sorted(retired_edges)],
        node_aliases={r['abbreviated_interface']:r['canonical_interface'] for r in records},
        edge_aliases={r['abbreviated_edge']:r['canonical_edge'] for r in records},
        physical_ends='remain_unknown_unless_separately_proved',unknown_lengths='not_added_across_views')
    if 'sourceDetailComparison' in g:
        g['sourceDetailComparison'].update(current_graph_status='historical_candidate_snapshot_superseded_by_scoped_confirmed_sideviews',
            superseded_by='confirmedSideviewCanonicalization',does_not_certify_projected_main_identity=True)
    g['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_semantic_change')
    g['preHilComparison']=dict(status='pending',reason='confirmed side-view canonical topology requires new source coverage, mapping and attribute evidence',previous_comparison=graph.get('preHilComparison'))
    g['derivedEvidenceInvalidation']=dict(input_graph_sha256=graph_hash,reason='active graph changed by confirmed representation replacement',
        recompute=['source_coverage','diameter_inheritance','segment_dimensions','cross_view_mapping','human_acceptance'],historical_evidence_preserved=True)
    if Counter(n['node_id'] for n in g['nodes'] if n.get('node_type')=='equipment')!=Counter(n['node_id'] for n in graph['nodes'] if n.get('node_type')=='equipment'):
        raise ValueError('actual equipment conservation failed')
    return g,dict(records=records,retired_abbreviated_nodes=len(retired_nodes),retired_abbreviated_edges=len(retired_edges),
        component_rows_unchanged=len(rows),source_coverage_requires_rebuild=True,hil_ready=False,
        corrected_circle_display_lengths=[dict(edge_id=eid,old_drawing_length=edges[eid]['path_length'],
            native_drawing_length=branch['path_length'],circle_handle=branch['source_detail_circle_length_evidence']['source_circle_handle'])
            for eid,branch in canonical_branches.items() if branch['path_length']!=edges[eid]['path_length']])

def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','manifest','reply','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();policy=load(a.policy)
    for name in ('source','graph','devices','manifest','reply'):
        if sha(getattr(a,name))!=policy[name+'_sha256']:raise ValueError('changed '+name)
    if a.output.exists():raise ValueError('output exists')
    doc,preflight=read_source(a.source);manifest=load(a.manifest)
    for image in manifest['images']:
        if sha(image['image'])!=image['sha256']:raise ValueError('reviewed Pair changed')
    with a.devices.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    g,audit=apply(doc,load(a.graph),rows,manifest,load(a.reply),policy['question_ids'],sha(a.source),sha(a.graph))
    a.output.mkdir(parents=True)
    target=a.output/'graph_with_canonical_sideviews.json';target.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (a.output/'assigned_edge_device_instances.csv').write_bytes(a.devices.read_bytes())
    audit.update(source_preflight=preflight['status'],output_graph_sha256=sha(target),script_sha256=sha(__file__),
        inputs={name:dict(path=str(getattr(a,name).resolve()),sha256=sha(getattr(a,name))) for name in ('source','graph','devices','manifest','reply','policy')})
    (a.output/'sideview-canonicalization-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(groups=len(policy['question_ids']),correspondences=len(audit['records']),nodes=len(g['nodes']),edges=len(g['edges']),components=len(rows),hil_ready=False)))

if __name__=='__main__':main()
