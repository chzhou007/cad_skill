"""Source-driven two-arm circle continuity; original pipe fragments remain separate.

The original CAD is authoritative. This reconstructs affected paths from
source-proved endpoint constraints and keeps every original edge as lineage.
The standalone owner independently replays its parent; family/mapping consumers remain separate.
"""
import collections
import copy
import math


def normalize(graph, records):
    selected = records
    if not selected or any(r.get('blockers') for r in selected) or len({r['circle_handle'] for r in selected}) != len(selected):
        raise ValueError('Explicit unique source-proved circle constraints required')
    out = copy.deepcopy(graph)
    nodes = {n['node_id']:n for n in graph['nodes']}
    edges = {e['edge_id']:e for e in graph['edges']}
    degree = collections.Counter(n for e in edges.values() for n in [e['start_node_id'],e['end_node_id']])
    bridges = {}; affected = set(); evidence_by_node = {}
    for row in sorted(selected,key=lambda r:r['circle_handle']):
        if row['shape'] not in ['corner','straight'] or len(row['contacts'])!=2:
            raise ValueError('Only native two-arm marker constraints are supported')
        ends = []
        for contact in row['contacts']:
            owners = contact['graph_endpoint_owners']
            if len(owners)!=1:
                raise ValueError('Source endpoint ownership is not unique')
            owner = owners[0]; nid = owner['node_id']; eid = owner['edge_id']
            if (nid not in nodes or eid not in edges or degree[nid]!=1
                    or nodes[nid].get('subtype')!='unresolved_source_terminal'
                    or edges[eid]['system']!=row['system']
                    or nid not in [edges[eid]['start_node_id'],edges[eid]['end_node_id']]
                    or contact['handle'] not in edges[eid].get('source_handles',[])
                    or math.dist([nodes[nid]['x'],nodes[nid]['y']],contact['endpoint'][:2])>.05):
                raise ValueError('Current source endpoint no longer matches the proof')
            if nid in bridges:
                raise ValueError('Endpoint is claimed by more than one circle')
            ends.append(nid); affected.add(eid)
        if len({nodes[n]['floor'] for n in ends})!=1:raise ValueError('Circle continuation cannot join floors')
        if ends[0]==ends[1]:
            raise ValueError('Circle endpoints collapse')
        bridges[ends[0]]=ends[1]; bridges[ends[1]]=ends[0]
        for nid in ends:evidence_by_node[nid]=copy.deepcopy(row)
    incidence=collections.defaultdict(list)
    for eid in affected:
        for nid in [edges[eid]['start_node_id'],edges[eid]['end_node_id']]:incidence[nid].append(eid)
    todo=set(affected);chains=[]
    while todo:
        seed=min(todo);component=set();queue=[seed]
        while queue:
            eid=queue.pop()
            if eid in component:continue
            component.add(eid)
            for nid in [edges[eid]['start_node_id'],edges[eid]['end_node_id']]:
                if nid in bridges:queue.extend(incidence[bridges[nid]])
        outside=sorted(n for e in component for n in [edges[e]['start_node_id'],edges[e]['end_node_id']] if n not in bridges)
        if len(outside)!=2 or outside[0]==outside[1]:
            raise ValueError('Affected edges must form a simple open path')
        current=outside[0];ordered=[];used=set();circle_handles=set();points=[];paths=[]
        while True:
            choices=[eid for eid in incidence[current] if eid in component and eid not in used]
            if len(choices)!=1:raise ValueError('Ambiguous affected path order')
            eid=choices[0];edge=edges[eid];forward=edge['start_node_id']==current
            end=edge['end_node_id'] if forward else edge['start_node_id']
            chunks=copy.deepcopy(edge['attribute_paths'])
            display=copy.deepcopy(edge.get('path_points',edge.get('path')))
            if not forward:
                chunks=[list(reversed(p)) for p in reversed(chunks)];display=list(reversed(display))
            if not display or math.dist(display[0],[nodes[current]['x'],nodes[current]['y']])>.05 or math.dist(display[-1],[nodes[end]['x'],nodes[end]['y']])>.05:
                raise ValueError('Original display path endpoint differs')
            points.extend(display if not points or points[-1]!=display[0] else display[1:]);paths.extend(chunks)
            ordered.append(eid);used.add(eid)
            if end not in bridges:
                if end!=outside[1] or used!=component:raise ValueError('Open path did not cover every source edge')
                break
            circle_handles.add(evidence_by_node[end]['circle_handle']);current=bridges[end]
        systems={edges[eid]['system'] for eid in ordered}
        if len(systems)!=1:raise ValueError('Supply and return cannot be merged')
        new_id='E-CIRCLE-PATH-'+'-'.join(sorted(circle_handles))
        if new_id in edges:raise ValueError('Normalized edge ID already exists')
        handles=[];names=[];counts=collections.Counter()
        for eid in ordered:
            e=edges[eid]
            for h in e.get('source_handles',[]):
                if h not in handles:handles.append(h)
            names.extend(e.get('equipment_names',[]));counts.update(e.get('equipment_counts',{}))
        if len(names)!=len(set(names)):raise ValueError('An inline component is assigned to multiple input edges')
        pipe_xy=sum(math.dist(a,b) for p in paths for a,b in zip(p,p[1:]))
        edge=dict(edge_id=new_id,start_node_id=outside[0],end_node_id=outside[1],system=next(iter(systems)),
                  start_floor=nodes[outside[0]]['floor'],end_floor=nodes[outside[1]]['floor'],
                  path=points,path_points=points,attribute_paths=paths,path_length=pipe_xy,
                  drawing_path_length=sum(math.dist(a,b) for a,b in zip(points,points[1:])),
                  source_handles=handles,equipment_names=names,equipment_counts=dict(counts),
                  path_length_complete=False,path_length_scope='known_native_pipe_fragments_excludes_circle_marker_interiors',
                  physical_length='unknown',physical_length_mm=None,
                  connection_mode='source_proved_two_arm_circle_continuation',
                  source_circle_continuity=dict(circle_handles=sorted(circle_handles),prior_edge_ids=ordered,
                      prior_edge_snapshots=[copy.deepcopy(edges[eid]) for eid in ordered],
                      semantic_bends_not_Ts=True,physical_connector_lengths_unknown=True,human_accepted=False))
        chains.append(edge);todo-=component
    retired=set(bridges);aliases={eid:e['edge_id'] for e in chains for eid in e['source_circle_continuity']['prior_edge_ids']}
    out['nodes']=[n for n in out['nodes'] if n['node_id'] not in retired]
    out['edges']=[e for e in out['edges'] if e['edge_id'] not in affected]+chains
    from edge_endpoint_semantics import reconcile
    one,_=reconcile(dict(nodes=out['nodes'],edges=chains,boundary_anchors=out.get('boundary_anchors',[])))
    normalized={e['edge_id']:e for e in one['edges']}
    out['edges']=[normalized.get(e['edge_id'],e) for e in out['edges']]
    # Unknown endpoints are retired only after a complete native marker proof;
    # do not silently retain their old ports as phantom equipment interfaces.
    old_ports=[p for p in out.get('virtual_equipment_ports',[]) if p.get('node_id') in retired or p.get('virtual_equipment_id') in retired]
    out['virtual_equipment_ports']=[p for p in out.get('virtual_equipment_ports',[]) if p not in old_ports]
    out['sourceTwoArmCircleContinuity']=dict(status='local_source_continuity_reconstructed_formal_consumers_pending',
        records=copy.deepcopy(selected),retired_nodes=[copy.deepcopy(nodes[n]) for n in sorted(retired)],
        retired_virtual_ports=old_ports,edge_id_aliases=aliases,new_edge_ids=[e['edge_id'] for e in chains],
        physical_Ts_added=0,physical_connector_lengths_assigned=0,human_accepted=False)
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='native two-arm circle continuations change local paths and endpoint roles',
        recompute=['source_comparison','T_and_port_audit','component_assignment','inventory','crossview_mapping','DN_scope','length_attributes','HIL'],
        historical_annotations_preserved=True)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='local_circle_continuity_changed_full_replay_pending')
    for e in out['edges']:
        if e['edge_id'] not in normalized and e!=edges[e['edge_id']]:raise ValueError('Unaffected edge changed')
    if len(out['nodes'])!=len(graph['nodes'])-len(retired) or len(out['edges'])!=len(graph['edges'])-len(selected):
        raise ValueError('Normalized graph inventory differs from the proved constraints')
    return out,aliases


def reassign_components(rows, aliases, output_edges):
    result=copy.deepcopy(rows);before=collections.Counter(row['device_name'] for row in rows)
    if any(count!=1 for count in before.values()):raise ValueError('Input component identities are not unique')
    edges={e['edge_id']:e for e in output_edges}
    for row in result:
        old=row['edge_id'];row['edge_id']=aliases.get(old,old)
        if row['edge_id'] and row['edge_id'] not in edges:raise ValueError('Component refers to missing output edge')
        if old in aliases and row['device_name'] not in edges[row['edge_id']]['equipment_names']:
            raise ValueError('Source component inventory differs from the merged graph')
    if collections.Counter(row['device_name'] for row in result)!=before:raise ValueError('Component was lost or duplicated')
    return result


def collect(doc, graph, handles, tolerance=.05):
    from ezdxf import bbox
    from ezdxf.addons.drawing import RenderContext
    from source_circle_rim_tee_screen import LAYERS
    from cad_ceiling_native_rules import match_out_of_plane_symbol
    if not handles or len(handles)!=len(set(handles)):raise ValueError('Explicit unique circle scope required')
    nodes={n['node_id']:n for n in graph['nodes']}
    degree=collections.Counter(n for e in graph['edges'] for n in [e['start_node_id'],e['end_node_id']])
    lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer in LAYERS]
    other=[e for e in doc.modelspace() if e.dxf.layer in LAYERS and e.dxftype() not in ('LINE','CIRCLE')]
    circles=list(doc.modelspace().query('CIRCLE'))
    glyphs=[dict(handle=e.dxf.handle,a=(e.dxf.start.x,e.dxf.start.y),b=(e.dxf.end.x,e.dxf.end.y)) for e in doc.modelspace().query('LINE') if e.dxf.layer=='空调立管、水平支管']
    context=RenderContext(doc); cache=bbox.Cache();result=[]
    def distance(p,a,b):
        v=[b[i]-a[i] for i in range(2)];ll=sum(x*x for x in v)
        t=max(0,min(1,sum((p[i]-a[i])*v[i] for i in range(2))/ll)) if ll else 0
        return math.dist(p,[a[i]+t*v[i] for i in range(2)])
    for handle in sorted(handles):
        circle=doc.entitydb.get(handle)
        if circle is None or not circle.is_alive or circle.dxftype()!='CIRCLE' or circle.dxf.layer not in LAYERS:raise ValueError('Declared native pipe marker missing')
        normal=tuple(circle.dxf.get('extrusion',(0,0,1)))
        if abs(normal[0])>1e-10 or abs(normal[1])>1e-10 or abs(abs(normal[2])-1)>1e-10:raise ValueError('Circle plane unsupported')
        center=list(circle.ocs().to_wcs(circle.dxf.center));p=center[:2];radius=circle.dxf.radius
        if not all(math.isfinite(v) for v in center) or not math.isfinite(radius) or radius<=0:raise ValueError('Invalid circle geometry')
        if match_out_of_plane_symbol(dict(center=p,radius=radius),glyphs,tolerance):raise ValueError('Equipment/out-of-plane glyph is not a pipe corner')
        for entity in other:
            box=bbox.extents([entity],cache=cache)
            if not box.has_data:raise ValueError('Unhandled pipe geometry cannot be bounded')
            if not (box.extmax.x<p[0]-radius-tolerance or box.extmin.x>p[0]+radius+tolerance or box.extmax.y<p[1]-radius-tolerance or box.extmin.y>p[1]+radius+tolerance):raise ValueError('Additional nearby pipe geometry needs its own reader')
        for neighbour in circles:
            if neighbour.dxf.handle!=handle and neighbour.dxf.layer in LAYERS:
                q=neighbour.ocs().to_wcs(neighbour.dxf.center)
                if math.dist(p,[q.x,q.y])<=tolerance:raise ValueError('Coincident circle markers are ambiguous')
        contacts=[]
        for line in lines:
            a,b=list(line.dxf.start),list(line.dxf.end)
            if distance(p,a[:2],b[:2])>radius+tolerance:continue
            da,db=math.dist(p,a[:2]),math.dist(p,b[:2]);endpoint,far=(a,b) if da<db else (b,a);near=min(da,db)
            kind='center' if near<=tolerance else 'rim' if abs(near-radius)<=tolerance else 'other'
            vector=[far[i]-p[i] for i in range(2)];norm=math.hypot(*vector)
            if not norm:raise ValueError('Degenerate source arm')
            if kind=='rim' and distance(endpoint[:2],p,far[:2])>tolerance:kind='non_radial_rim'
            contacts.append(dict(handle=line.dxf.handle,system=LAYERS[line.dxf.layer],layer=line.dxf.layer,effective_colour=context.resolve_all(line).color,endpoint=endpoint,other_endpoint=far,contact=kind,direction=[v/norm for v in vector]))
        if len(contacts)!=2 or sorted(c['contact'] for c in contacts)!=['center','rim']:raise ValueError('Circle does not have exactly two center/rim pipe arms')
        if len({c['system'] for c in contacts})!=1 or len({c['effective_colour'] for c in contacts})!=1:raise ValueError('Circle must not join pipe systems or colours')
        if any(abs(v[2]-center[2])>tolerance for c in contacts for v in [c['endpoint'],c['other_endpoint']]):raise ValueError('Native Z disagreement needs separate evidence')
        cosine=sum(contacts[0]['direction'][i]*contacts[1]['direction'][i] for i in range(2))
        if abs(cosine)>1e-7 and abs(cosine+1)>1e-7:raise ValueError('Two source arms are not a qualified corner or continuation')
        if any(handle in b.get('source_marker_handles',[]) for b in graph.get('boundary_anchors',[])):raise ValueError('Reviewed source boundary is protected')
        system=contacts[0]['system']
        for contact in contacts:
            owners=[]
            for edge in graph['edges']:
                if edge['system']!=system or contact['handle'] not in edge.get('source_handles',[]):continue
                for nid in [edge['start_node_id'],edge['end_node_id']]:
                    n=nodes[nid]
                    if math.dist([n['x'],n['y']],contact['endpoint'][:2])<=tolerance:owners.append(dict(edge_id=edge['edge_id'],node_id=nid,degree=degree[nid],subtype=n.get('subtype')))
            if len(owners)!=1 or owners[0]['degree']!=1 or owners[0]['subtype']!='unresolved_source_terminal':raise ValueError('Native endpoint owner is not uniquely unresolved')
            contact['graph_endpoint_owners']=owners
        result.append(dict(circle_handle=handle,circle_layer=circle.dxf.layer,circle_layer_matches_lines=LAYERS[circle.dxf.layer]==system,system=system,center_WCS=center,radius=radius,shape='corner' if abs(cosine)<1e-7 else 'straight',contacts=contacts,blockers=[],physical_T_proven=False,physical_connector_length_mm=None,graph_modified=False))
    return result


def compute(paths, policy):
    import csv
    from pathlib import Path
    from confirm_crossview_paths import load,sha
    from source_readability import read_source
    from reconstruct_sideview_equipment_ownership import verify_output as verify_parent
    for key in ('source','graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('Two-arm normalization input changed '+key)
    parent=verify_parent(Path(paths['graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('Native ownership parent differs')
    doc,preflight=read_source(paths['source']);graph=load(paths['graph']);records=collect(doc,graph,policy['circle_handles'])
    with Path(paths['devices']).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    out,aliases=normalize(graph,records);assigned=reassign_components(rows,aliases,out['edges'])
    return out,assigned,fields,dict(source_preflight=preflight,records=records,edge_id_aliases=aliases,parent_graph_sha256=sha(paths['graph']),components_conserved=len(rows),physical_Ts_added=0,physical_lengths_assigned=0,parent_native_replayed=True,human_accepted=False)


def implementation_hashes():
    from pathlib import Path
    from confirm_crossview_paths import sha
    names=('normalize_two_arm_circle_continuity.py','source_circle_rim_tee_screen.py','cad_ceiling_native_rules.py','edge_endpoint_semantics.py','source_readability.py')
    return {name:sha(Path(__file__).with_name(name)) for name in names}


def verify_output(directory):
    import csv
    from pathlib import Path
    from confirm_crossview_paths import load,sha,encode
    directory=Path(directory);audit=load(directory/'two-arm-circle-continuity-audit.json')
    if audit['implementation_sha256']!=implementation_hashes():raise ValueError('Two-arm continuity implementation changed')
    for row in audit['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('Two-arm continuity dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};out,components,fields,proof=compute(paths,load(paths['policy']))
    if encode(out)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or proof!=audit['proof']:raise ValueError('Native continuity replay differs')
    with (directory/'assigned_edge_device_instances.csv').open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=fields or list(reader)!=components:raise ValueError('Component assignment replay differs')
    return audit


def main():
    import argparse,csv
    from pathlib import Path
    from confirm_crossview_paths import load,sha,encode
    parser=argparse.ArgumentParser()
    for key in ('source','graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args();paths={k:getattr(args,k) for k in ('source','graph','devices','policy')}
    if args.output.exists():raise FileExistsError(args.output)
    out,components,fields,proof=compute(paths,load(args.policy));args.output.mkdir()
    (args.output/'graph_with_edges.json').write_bytes(encode(out))
    with (args.output/'assigned_edge_device_instances.csv').open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(components)
    audit=dict(mode='native_two_arm_circle_continuity_v1',inputs={k:dict(path=str(p.resolve()),sha256=sha(p)) for k,p in paths.items()},implementation_sha256=implementation_hashes(),proof=proof,output_graph_sha256=sha(args.output/'graph_with_edges.json'),family_entry_integrated=False,crossview_inventory_and_attributes_invalidated=True,human_accepted=False)
    (args.output/'two-arm-circle-continuity-audit.json').write_bytes(encode(audit));print(dict(circles=len(proof['records']),new_paths=len(set(proof['edge_id_aliases'].values())),components=len(components),family_entry_integrated=False))

if __name__=='__main__':main()
