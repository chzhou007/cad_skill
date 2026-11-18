"""Compose proved native omission paths for vertical DN; never invent lengths.

An edge ID alone does not prove continuity. Replay both marker geometries,
original source bends and the original annotation owner before inheritance.
"""
import argparse, copy, collections, math, importlib
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from reconstruct_native_block_branches import marker_records, marker_distance
from axis_unbranched_vertical_DN import source_key, native_items, chain_evidence, annotation_index, annotation_guard, source_Z
from native_repeated_branch_DN_layout import collect as repeated_reader
from native_line_path_evidence import LAYERS, _on

MODE = 'native_axis_omission_vertical_DN_v1'


def owned_annotation_guard(doc,seeds,corridor,index,source_hash,edge,edges,replayed):
    """Exclude only independently re-owned captions of the opposite system.

    Scalar equality or text proximity never clears a transition. Same-system
    alternatives, F frames and unsupported captions retain the original guard.
    """
    excluded=[]
    for handle,proof in replayed.items():
        owner=edges.get(proof['current_edge_id']);binding=proof['native_binding']
        if (owner and owner['system']!=edge['system'] and owner['system'] in LAYERS
            and binding['layer']==LAYERS[owner['system']]
            and binding['current_graph_owners']==[owner['edge_id']]
            and proof['source_text']['source_sha256']==source_hash):
            excluded.append(dict(text_handle=handle,source_owner=copy.deepcopy(proof)))
    private=dict(index,probes=[t for t in index['probes'] if t['handle'] not in {x['text_handle'] for x in excluded}])
    result=annotation_guard(doc,seeds,corridor,private,source_hash,edge.get('source_insert_handle'))
    result['independently_replayed_opposite_system_annotations']=excluded
    return result


def omission_corridor(doc, graph, edge, target, seed, scopes, items, source_hash):
    binding = edge.get('source_native_block_branch', {})
    snapshot = binding.get('endpoint_snapshot', {})
    if (edge.get('connection_mode') != 'omission_pair_stitched_at_main_marker'
        or binding.get('source_sha256') != source_hash
        or any(snapshot.get(k) != edge.get(k) for k in ('start_node_id', 'end_node_id', 'system', 'attribute_paths'))):
        raise ValueError('current source-bound omission branch required')
    records = [r for r in graph.get('sourceNativeBlockBranchReconstruction', {}).get('records', []) if r['edge_id'] == edge['edge_id']]
    if len(records) != 1 or records[0]['source_paths'] != edge['attribute_paths']:
        raise ValueError('original omission reconstruction scope differs')
    old = records[0].get('omission')
    if not old or target['path_index'] == seed['path_index']:
        raise ValueError('two distinct omission-side paths required')
    root = doc.entitydb.get(edge.get('source_insert_handle'))
    if root is None or root.dxftype() != 'INSERT' or root not in doc.modelspace():
        raise ValueError('native omission INSERT missing')
    fresh = marker_records(root)
    if {tuple(m['source_chain']) for m in fresh} != {tuple(old[k]['source_chain']) for k in ('main_marker','remote_marker')}:
        raise ValueError('native omission marker identities differ')
    for marker in fresh:
        previous = next(old[k] for k in ('main_marker','remote_marker') if old[k]['source_chain'] == marker['source_chain'])
        if marker != previous:
            raise ValueError('native omission marker geometry changed')
    corridors = []; contacts = []; marker_ids = []
    for selected in (target, seed):
        pi = selected['path_index']; path = edge['attribute_paths'][pi]
        hits = [(mi, end) for mi,m in enumerate(fresh) for end in (0,len(path)-1) if marker_distance(path[end],m) <= .05]
        if len(hits) != 1:
            raise ValueError('path has no unique native omission port')
        mi,end = hits[0]; si = selected['segment_index']
        indices = range(0,si+1) if end == 0 else range(si,len(path)-1)
        chain = [scopes[edge['edge_id'],pi,i] for i in indices]
        proof = chain_evidence(chain, root.dxf.handle, items)
        # The port must be an actual LINE endpoint, not an interior glyph hit.
        item = proof['native_chain'][0 if end == 0 else -1]
        if not any(math.dist(path[end],p[:2]) <= .05 for p in item['XYZ']):
            raise ValueError('omission contact is not a native pipe endpoint')
        incident=[x for x in items if x['layer']==item['layer'] and _on(path[end],x['XYZ'][0][:2],x['XYZ'][1][:2],.05)
            and abs(source_Z(x,path[end])-source_Z(item,path[end]))<=.05]
        if len(incident)!=1:raise ValueError('omission port has competing same-system source arms')
        expected = old['main_pipe_contact'] if fresh[mi]['source_chain'] == old['main_marker']['source_chain'] else old['remote_pipe_contact']
        if math.dist(path[end],expected) > .05:
            raise ValueError('omission pipe contact differs from original owner')
        contacts.append(dict(path_index=pi,point_xy=path[end],source_Z=next(p[2] for p in item['XYZ'] if math.dist(path[end],p[:2]) <= .05)))
        marker_ids.append(mi); corridors.append(dict(scopes=chain,source_continuity=proof))
    if len(set(marker_ids)) != 2 or abs(contacts[0]['source_Z']-contacts[1]['source_Z']) > .05:
        raise ValueError('separate paired same-Z omission ports required')
    return dict(markers=fresh,contacts=contacts,corridors=corridors,physical_length_mm=None,
                inline_joint_crossed=False,physical_T_crossed=False,source='original_native_omission_pair_replayed')


def collect(doc,graph,route,annotations,prior,source_hash,graph_hash):
    before = encode(graph),encode(route),encode(annotations),encode(prior)
    if graph['metadata']['source_sha256'] != source_hash or annotations['source_sha256'] != source_hash or annotations['graph_sha256'] != graph_hash:
        raise ValueError('source annotation graph binding differs')
    edges={e['edge_id']:e for e in graph['edges']}; scopes={source_key(r):r for r in route['records']}
    if len(scopes)!=len(route['records']):raise ValueError('duplicate native route domains')
    for r in route['records']:
        edge=edges[r['edge_id']]
        if edge['system']!=r['system'] or edge['attribute_paths'][r['path_index']][r['segment_index']:r['segment_index']+2]!=r['scope_points']:
            raise ValueError('native route differs from actual graph segment')
    for parent in (route,prior):
        if parent['inputs']['source']['sha256']!=source_hash or parent['inputs']['graph']['sha256']!=graph_hash:
            raise ValueError('parent source/graph identity differs')
    known=annotations['records']+prior['records']; by=collections.defaultdict(list)
    for r in known: by[r['edge_id']].append(r)
    candidates=[]
    for p in prior['pending']:
        choices=by[p['edge_id']]
        if p.get('original_reason') == 'no_qualified_axis_annotation_on_this_vertical_segment' and len({r['nominal_mm'] for r in choices}) == 1:
            direct=[s for s in annotations['records'] if s['edge_id']==p['edge_id'] and s['path_index']!=p['path_index']]
            if direct: candidates.append((p,direct))
    # Re-execute the original native repeated-layout owner. Receipt presence or
    # same-edge membership is not a substitute for this independent source read.
    handles=sorted({o['source_text']['handle'] for _,seeds in candidates for s in seeds for o in s['observations']})
    replay=[];replayed={}
    for batch in annotations.get('repeated_native_qualification',[]):
        for piece in batch['pieces']:
            if piece['status']!='passed' or not set(handles).intersection(piece['handles']):continue
            fresh=repeated_reader(doc,graph,piece['handles'],source_hash,graph_hash)
            if fresh!=piece['result']['ownership']:raise ValueError('original repeated seed cohort replay differs')
            replay.append(fresh)
            replayed.update({r['source_text']['handle']:r for r in fresh['records']})
    items=native_items(doc,graph); index=annotation_index(doc,graph,source_hash)
    records=[]; attempted={}; diagnostics=[]
    for pending,seeds in candidates:
        key=source_key(pending); target=scopes[key]; edge=edges[key[0]]
        try:
            if target['direction_class']!='vertical': raise ValueError('only vertical target domains permitted')
            for seed in seeds:
                for obs in seed['observations']:
                    if obs['reader']!='inherited_repeated_native_branch_layout_and_segment_domain' or replayed.get(obs['source_text']['handle'])!=obs['native_evidence']:
                        raise ValueError('original native seed ownership differs')
            seed=sorted(seeds,key=source_key)[0]
            evidence=omission_corridor(doc,graph,edge,target,seed,scopes,items,source_hash)
            corridor=[s for c in evidence['corridors'] for s in c['scopes']]
            guard=owned_annotation_guard(doc,seeds,corridor,index,source_hash,edge,edges,replayed)
            records.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],scope_points=copy.deepcopy(target['scope_points']),
                system=target['system'],floor_start=target['floor_start'],floor_end=target['floor_end'],nominal_mm=seed['nominal_mm'],
                status='native_axis_vertical_DN_inherited_across_proved_omission',source='axis_11_native_annotation_and_omission',
                seed_record=copy.deepcopy(seed),continuity_evidence=evidence,annotation_guard=guard,
                physical_length_mm=None,whole_edge_DN_assigned=False,human_accepted=False))
            attempted[key]='qualified'
        except ValueError as exc:
            attempted[key]=str(exc);diagnostics.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],reason=str(exc)))
    new={source_key(r) for r in records}
    remaining=[copy.deepcopy(p) for p in prior['pending'] if source_key(p) not in new]
    if before != (encode(graph),encode(route),encode(annotations),encode(prior)): raise ValueError('input evidence mutated')
    return dict(mode=MODE,records=records,pending=remaining,candidate_diagnostics=diagnostics,
        counts=dict(previous_known=prior['counts']['current_known_vertical_domains'],screened_pending=len(prior['pending']),
            omission_candidates=len(candidates),new_known=len(records),current_known=prior['counts']['current_known_vertical_domains']+len(records),remaining_unknown=len(remaining)),
        seed_native_replay=replay,graph_mutated=False,horizontal_attributes_changed=False,physical_lengths_assigned=0,human_accepted=False)


def compute(m):
    inputs=m['inputs']
    def check():
        if any(sha(v['path'])!=v['sha256'] for v in inputs.values()):raise ValueError('pinned batch inputs changed')
    check();doc,preflight=read_source(inputs['axis_source']['path'])
    result=collect(doc,load(inputs['axis_graph']['path']),load(inputs['routing']['path']),load(inputs['vertical_annotations']['path']),
        load(inputs['vertical_DN_proof']['path']),inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'])
    check();result.update(inputs=inputs,source_preflight=preflight,published=False)
    return result


def implementation_hashes():
    names=('axis_unbranched_vertical_DN','native_repeated_branch_DN_layout','reconstruct_native_block_branches',
        'pipe_annotation_attributes','source_readability','native_line_path_evidence','native_paired_caption_geometry')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__) for n in names})


def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);target=output/'omission-vertical-DN.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),
        implementation_sha256=implementation_hashes(),output_sha256=sha(target))))
    return result


def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'omission-vertical-DN.json'
    if (receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()
        or sha(m['path'])!=m['sha256'] or sha(target)!=receipt['output_sha256']):raise ValueError('source, code or output changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('fresh source omission inheritance replay differs')
    return fresh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    print(produce(a.manifest,a.output)['counts'],flush=True)
