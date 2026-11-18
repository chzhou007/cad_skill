"""Replay axis DN inheritance on native through-riser segment domains.

Mixed local edges stay immutable. Private segment cuts stop at existing bends;
only the actual middle T propagates through the same source LINE. Horizontal
branches are independently checked frontiers, never vertical DN seed writers.
"""
import argparse,copy,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from crossview_equipment_branch_inventory import index_graph,native_tee
from native_line_path_evidence import collect as collect_lines,LAYERS,_on
from native_segment_dn_candidates_v2 import verify_output as verify_segment_DN,collect as collect_segment_DN
from native_scope_leader_isolation import collect as isolate_leaders,CatalogDocument
from native_repeated_branch_DN_layout import collect as bind_repeated_branch_DN
from plan_pipe_diameter_scopes import catalog
from checked_plan_DN_scope_attributes import attribute_checked_scope
from source_readability import read_source

MODE='native_axis_through_riser_segment_DN_scopes_v1'


def project(doc,graph,line_evidence,corridors,source_hash,graph_hash):
    nodes,edges,adj=index_graph(graph);witness={r['edge_id']:r for r in line_evidence['edges']}
    if (line_evidence.get('source_sha256')!=source_hash or line_evidence.get('graph_sha256')!=graph_hash
        or not corridors or len({c['corridor_id'] for c in corridors})!=len(corridors)):raise ValueError('invalid riser scope source or identities')
    projection=copy.deepcopy(graph);replaced={};fragments={};scope=[];contracts=[];used=set();taps=set();frontiers=set()
    for spec in corridors:
        nid=spec['junction'];node=nodes.get(nid);low=spec['lower'];high=spec['upper'];system=spec['system'];branch=spec['branch_frontier_edge']
        if (not node or node.get('node_type') not in ('tee','physical_junction') or node.get('review_required') is True
            or nid in taps or {e['edge_id'] for e in adj[nid]}!={low['edge_id'],high['edge_id'],branch}
            or len(adj[nid])!=3 or {e['system'] for e in adj[nid]}!={system}):raise ValueError('riser middle T differs from current local topology')
        taps.add(nid);frontiers.add(branch);proof=native_tee(doc,graph,nid,source_hash,graph_hash)
        rays=proof['junctions'][0]['source_rays'];through=[r for r in rays if r['edge_id']!=branch]
        if len(through)!=2 or any(r.get('source_line_handle')!=spec['source_line_handle'] for r in through):raise ValueError('vertical arms do not share one native through LINE')
        if next(r for r in rays if r['edge_id']==branch).get('source_line_handle')==spec['source_line_handle']:raise ValueError('branch cannot redefine through-riser role')
        ranges=[]
        for side,choice in [('lower',low),('upper',high)]:
            eid=choice['edge_id'];idx=choice['segment_index'];edge=edges.get(eid)
            if (eid in used or not edge or edge.get('system')!=system or not isinstance(idx,int) or isinstance(idx,bool)
                or edge.get('connection_mode')!='continuous_original_cad_pipe' or eid not in witness):raise ValueError('unsupported or repeated mixed riser edge')
            used.add(eid);paths=edge.get('attribute_paths');rows=witness[eid]['segments']
            if len(paths)!=1 or len(paths[0])<3 or len(rows)!=len(paths[0])-1 or not 0<=idx<len(rows):raise ValueError('mixed edge segment witness differs')
            points=paths[0];a,b=points[idx:idx+2];w=rows[idx]
            if (w['source_handle']!=spec['source_line_handle'] or abs(a[0]-b[0])>.05 or abs(a[1]-b[1])<=.05
                or w['graph_start']!=a or w['graph_end']!=b):raise ValueError('selected riser segment lacks vertical native source coverage')
            ends=[edge['start_node_id'],edge['end_node_id']]
            if nid not in ends or sorted(nodes[n]['floor'] for n in ends)!=choice['floor_pair'] or node['floor']!=choice['floor_pair'][1 if side=='lower' else 0]:raise ValueError('riser floor span differs')
            if math.dist([nodes[ends[0]]['x'],nodes[ends[0]]['y']],points[0])>.05 or math.dist([nodes[ends[1]]['x'],nodes[ends[1]]['y']],points[-1])>.05:raise ValueError('mixed edge does not reach original endpoints')
            # The actual T must terminate the selected vertical arm, not a
            # horizontal subpath or an invented cut in the middle of a pipe.
            tpoint=[node['x'],node['y']]
            if min(math.dist(tpoint,a),math.dist(tpoint,b))>.05:raise ValueError('vertical arm does not directly reach middle T')
            ids=[ends[0]]
            for pi,p in enumerate(points[1:-1],1):
                bid=f'DN-SEG-CUT:{eid}:{pi}'
                if bid in nodes:raise ValueError('read-only segment cut ID collides')
                projection['nodes'].append(dict(node_id=bid,node_type='read_only_attribute_cut_not_physical_node',x=p[0],y=p[1],floor=None));ids.append(bid)
            ids.append(ends[1]);replaced[eid]=[]
            for si,(p,q) in enumerate(zip(points,points[1:])):
                frag=f'DN-SEG:{eid}:{si}'
                if frag in edges:raise ValueError('read-only segment ID collides')
                if rows[si]['graph_start']!=p or rows[si]['graph_end']!=q:raise ValueError('source witness segment order differs')
                item=dict(edge_id=frag,start_node_id=ids[si],end_node_id=ids[si+1],system=system,
                    attribute_paths=[[copy.deepcopy(p),copy.deepcopy(q)]],source_handles=[rows[si]['source_handle']],
                    connection_mode='continuous_original_cad_pipe',source_local_edge_id=eid,source_segment_index=si,
                    read_only_attribute_projection=True)
                replaced[eid].append(item);fragments[frag]=(eid,si)
            fid=f'DN-SEG:{eid}:{idx}';scope.append(fid)
            ranges.append(dict(side=side,edge_id=eid,segment_index=idx,projection_edge_id=fid,floor_pair=choice['floor_pair'],
                source_line_handle=w['source_handle'],scope_points=[a,b],physical_length_mm=None))
        contracts.append(dict(corridor_id=spec['corridor_id'],system=system,middle_T=nid,native_middle_T_evidence=proof,
            through_source_LINE=spec['source_line_handle'],non_through_branch=branch,segments=ranges))
    if len(used)!=2*len(corridors) or len(frontiers)!=len(corridors):raise ValueError('overlapping riser scopes or branches')
    projection['edges']=[f for e in projection['edges'] for f in replaced.get(e['edge_id'],[e])]
    index_graph(projection)
    return projection,fragments,scope,contracts,taps,frontiers


def attribute(doc,graph,line_evidence,segment_policy,policy,source_hash,graph_hash):
    projection,fragments,scope,contracts,taps,frontiers=project(doc,graph,line_evidence,policy['corridors'],source_hash,graph_hash)
    ph=__import__('hashlib').sha256(encode(projection)).hexdigest();reverse={(eid,si):fid for fid,(eid,si) in fragments.items()}
    seeds=[]
    for selection in segment_policy['selections']:
        fid=reverse.get((selection['edge_id'],selection['segment_index']))
        if fid in scope:seeds.append(dict(text_handle=selection['text_handle'],edge_id=fid,source_line_handle=
            next(w['source_handle'] for w in next(r for r in line_evidence['edges'] if r['edge_id']==selection['edge_id'])['segments'] if w['segment_index']==selection['segment_index']),expected_text=selection['expected_text']))
    if len(seeds)!=len(contracts) or len({s['edge_id'] for s in seeds})!=len(seeds):raise ValueError('each riser requires one independently attributed segment seed')
    paths=[p for e in projection['edges'] if e['edge_id'] in set(scope)|frontiers for p in e['attribute_paths']]
    isolation=isolate_leaders(doc,paths,source_hash)
    texts,inventory=catalog(CatalogDocument(doc,isolation),projection,sorted(set(scope)|frontiers),source_hash,ph)
    inventory['native_LEADER_isolation']=isolation
    layout_handles=policy.get('native_branch_DN_layout_text_handles',[])
    if layout_handles:
        layout=bind_repeated_branch_DN(doc,graph,layout_handles,source_hash,graph_hash)
        for row in layout['records']:
            if row['current_edge_id'] in {fragments[f][0] for f in scope}|frontiers:raise ValueError('a riser or branch-frontier DN cannot be excluded as an unrelated instance annotation')
            point=row['native_binding']['projection']
            if any(_on(point,a,b,.05) for path in paths for a,b in zip(path,path[1:])):raise ValueError('qualified other-branch annotation still reaches selected riser scope')
        texts=[t for t in texts if t['handle'] not in set(layout_handles)]
        inventory['other_branch_repeated_native_DN_layout']=layout
    raw_edges=index_graph(graph)[1]
    def direct(native,current,selection,sh,gh):
        if native is not doc or current is not projection or sh!=source_hash or gh!=ph:raise ValueError('segment collector used outside exact read-only projection')
        choices=[];owner_by_projection={};extra_witness=[]
        for s in selection['selections']:
            fid=s['edge_id']
            if fid in fragments:eid,si=fragments[fid]
            else:
                if fid not in frontiers:raise ValueError('DN source outside declared segment or actual branch frontier')
                edge=raw_edges[fid];points=edge['attribute_paths'][0];handles=[]
                for a,b in zip(points,points[1:]):
                    hits=[line.dxf.handle for line in doc.modelspace().query('LINE') if line.dxf.layer==LAYERS[edge['system']]
                        and _on(a,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05) and _on(b,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)]
                    if len(hits)!=1:raise ValueError('branch frontier source path not uniquely witnessed')
                    handles.append(hits[0])
                indices=[i for i,h in enumerate(handles) if h==s['source_line_handle']]
                if len(indices)!=1:raise ValueError('branch annotation segment owner ambiguous')
                eid=fid;si=indices[0]
                if eid not in {r['edge_id'] for r in extra_witness}:
                    proof=collect_lines(doc,graph,dict(source_sha256=sh,graph_sha256=graph_hash,selections=[dict(edge_id=eid,line_handles=handles)]),sh,graph_hash)
                    extra_witness.extend(proof['edges'])
            owner_by_projection[fid]=(eid,si)
            row=dict(text_handle=s['text_handle'],edge_id=eid,segment_index=si,expected_text=s['expected_text'])
            actual=next(r for r in line_evidence['edges']+extra_witness if r['edge_id']==eid)['segments'][si]
            if s['source_line_handle']!=actual['source_handle']:raise ValueError('segment seed native LINE differs')
            choices.append(row)
        evidence=copy.deepcopy(line_evidence);evidence['edges'].extend(extra_witness);lh=__import__('hashlib').sha256(encode(evidence)).hexdigest()
        fresh=collect_segment_DN(doc,graph,evidence,dict(segment_policy,selections=choices,withheld_candidates=[],line_evidence_sha256=lh),source_hash,graph_hash,lh)
        out=[]
        for s,r in zip(selection['selections'],fresh['observations']):
            if (r['edge_id'],r['segment_index'])!=owner_by_projection[s['edge_id']]:raise ValueError('source observation outside declared segment')
            out.append(dict(r,edge_id=s['edge_id'],nominal_mm=r['nominal_mm_candidate'],source_local_edge_id=r['edge_id']))
        return dict(observations=out)
    pnodes,_,_=index_graph(projection);junctions={t:native_tee(doc,projection,t,source_hash,ph) for t in sorted(taps)}
    checked=attribute_checked_scope(doc,projection,dict(group_id=policy['scope_id'],branches=[],main_edges=scope,seeds=seeds),texts,source_hash,ph,
        set(inventory['F_text_handles']),junctions=junctions,verified_taps=taps,branch_frontier_edges=frontiers,direct_collector=direct)
    records=[]
    for r in checked['records']:
        eid,si=fragments[r['edge_id']];row=copy.deepcopy(r)
        row.update(projection_edge_id=r['edge_id'],edge_id=eid,segment_index=si,source_line_handle=next(c['through_source_LINE'] for c in contracts if any(s['projection_edge_id']==r['edge_id'] for s in c['segments'])),
            scope='native_axis_through_riser_drawn_vertical_segment_only',physical_direction='not_inferred_from_drawing_orientation_alone',
            status=r['status'].replace('_plan_DN','_axis_segment_DN'),physical_length_mm=None,whole_local_edge_DN_assigned=False)
        records.append(row)
    return dict(mode=MODE,status='source_checked_axis_through_riser_segment_DN_human_pending',source_sha256=source_hash,graph_sha256=graph_hash,
        records=records,through_contracts=contracts,source_annotation_inventory=inventory,checked_DN_scope=checked,
        read_only_segment_projection_sha256=ph,local_graph_mutated=False,physical_values_fused=False,
        floor_interface_correspondence_confirmed=False,installed_lengths_assigned=0,whole_edge_DN_assigned=0,human_accepted=False)


def compute(paths,policy):
    for key in ('segment_DN','segment_receipt'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('riser DN dependency changed '+key)
    directory=Path(paths['segment_DN']).resolve().parent
    if Path(paths['segment_DN']).resolve()!=directory/'segment-DN-evidence.json' or Path(paths['segment_receipt']).resolve()!=directory/'source-segment-DN-receipt.json':raise ValueError('noncanonical segment DN evidence')
    verified=verify_segment_DN(directory);receipt=load(paths['segment_receipt']);inputs={k:v['path'] for k,v in receipt['inputs'].items()}
    doc,preflight=read_source(inputs['source']);graph=load(inputs['graph']);result=attribute(doc,graph,load(inputs['line_evidence']),load(inputs['policy']),policy,sha(inputs['source']),sha(inputs['graph']))
    result.update(source_preflight=preflight,segment_DN_evidence_sha256=sha(paths['segment_DN']))
    return result


def implementation_hashes():
    from paired_plan_DN_scopes import implementation_hashes as inherited
    from native_segment_dn_candidates_v2 import implementation_hashes as segments
    hashes=inherited();hashes.update(segments())
    for name in ('native_axis_riser_DN_scopes.py','native_scope_leader_isolation.py','native_repeated_branch_DN_layout.py','source_dn_bulk_screen.py'):hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'axis-riser-DN-scope-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('riser DN scope implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('riser DN scope input changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'axis-riser-DN-scopes.json').read_bytes() or sha(directory/'axis-riser-DN-scopes.json')!=receipt['output_sha256']:raise ValueError('riser DN scope native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('segment-DN-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(segment_DN=a.segment_DN_run/'segment-DN-evidence.json',segment_receipt=a.segment_DN_run/'source-segment-DN-receipt.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'axis-riser-DN-scopes.json').write_bytes(encode(result))
    (a.output/'axis-riser-DN-scope-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'axis-riser-DN-scopes.json'),human_accepted=False)))
    print(dict(records=len(result['records']),known_DN=sum(r['nominal_mm'] is not None for r in result['records']),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
