"""Use original axis annotation owners on continuous native pipe domains.

Horizontal captions are seed evidence only. Every emitted value belongs to an
original vertical segment. A same-source LINE may pass a checked through-T;
branch captions do not seed the main and ordinary crossings never add links.
"""
import argparse,collections,copy,hashlib,importlib,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from axis_vertical_DN_batch import projection,recursive_qualification
from native_segment_dn_candidates_v2 import collect as source_reader
from pipe_annotation_attributes import source_texts,direct_diameters,recognize_f_leaders
from native_paired_caption_geometry import collect as paired_captions
from axis_unbranched_vertical_DN import source_key,native_items,chain_evidence,annotation_index,annotation_guard,source_Z
from native_line_path_evidence import LAYERS,_on
from crossview_equipment_branch_inventory import native_tee,index_graph

MODE='native_continuous_axis_source_vertical_DN_v1'


def modelspace_seeds(doc,graph,route,source_hash,graph_hash):
    private,index,lines,ph=projection(graph,route);texts=source_texts(doc,'axis',source_hash);layers={t['layer'] for t in texts}
    if any('\ufffd' in t['text'] for t in texts):raise ValueError('native Chinese unreadable')
    F={t['handle'] for f in recognize_f_leaders(doc,texts,[],graph['edges'],layers) for t in f['texts']}|set(paired_captions(doc)['F_owned_texts'])
    # The legacy discovery function excludes text IDs, not bare source handles.
    excluded={t['id'] for t in texts if t['handle'] in F}
    assigned,pending=direct_diameters(texts,private['edges'],excluded,layers);selected={}
    for row in assigned:
        scope=index[row['edge_id']]
        if scope['native_source_status']!='single_source_line_covers' or scope['native_witnesses'][0]['scope']!='modelspace':continue
        selected[row['text']['handle']]=dict(scope=scope,spec=dict(text_handle=row['text']['handle'],edge_id=row['edge_id'],segment_index=0,expected_text=row['text']['text']))
    lh=hashlib.sha256(encode(lines)).hexdigest()
    def reader(handles):
        policy=dict(source_sha256=source_hash,graph_sha256=ph,line_evidence_sha256=lh,text_layers=sorted(layers),selections=[selected[h]['spec'] for h in handles])
        return source_reader(doc,private,lines,policy,source_hash,ph,lh)
    pieces=recursive_qualification(sorted(selected),reader);records=[];held=[]
    for piece in pieces:
        if piece['status']!='passed':
            held.extend(dict(text_handle=h,reason=piece['reason']) for h in piece['handles']);continue
        for observation in piece['result']['observations']:
            scope=selected[observation['source_text']['handle']]['scope'];line=doc.entitydb[observation['source_line_handle']]
            primitive=dict(XYZ=[list(line.dxf.start),list(line.dxf.end)])
            z=source_Z(primitive,observation['graph_projection'])
            if abs(doc.entitydb[observation['source_text']['handle']].dxf.insert.z-z)>.05:
                held.append(dict(text_handle=observation['source_text']['handle'],reason='native caption and pipe Z differ'));continue
            records.append(dict(edge_id=scope['edge_id'],path_index=scope['path_index'],segment_index=scope['segment_index'],scope_points=scope['scope_points'],
                system=scope['system'],direction_class=scope['direction_class'],nominal_mm=observation['nominal_mm_candidate'],source_line_handle=observation['source_line_handle'],
                observations=[dict(source_text=observation['source_text'],nominal_mm=observation['nominal_mm_candidate'],native_evidence=observation)],
                source_Z=z,horizontal_final_value_assigned=False))
    return dict(records=records,held=held,original_reader_pieces=pieces,private_graph_sha256=ph,source_graph_sha256=graph_hash,
        F_owned_text_handles=sorted(F),discovery_pending=len(pending),horizontal_values_assigned=0)


def overlaps_pipe(line,scopes):
    """Positive collinear overlap, not a crossing or a near parallel caption."""
    a,b=[list(line.dxf.start)[:2],list(line.dxf.end)[:2]];v=[b[i]-a[i] for i in (0,1)];length=math.hypot(*v)
    if length<=.05:return False
    for scope in scopes:
        c,d=scope['scope_points'];w=[d[i]-c[i] for i in (0,1)];other=math.hypot(*w)
        if other<=.05 or abs(v[0]*w[1]-v[1]*w[0])/length/other>1e-6:continue
        if abs(v[0]*(c[1]-a[1])-v[1]*(c[0]-a[0]))/length>.05:continue
        lo,hi=sorted(sum((p[i]-a[i])*v[i]/length for i in (0,1)) for p in (c,d))
        if min(length,hi)-max(0,lo)>.05:return True
    return False


def scoped_guard(doc,seeds,scopes,index,source_hash,root,all_seeds):
    system=scopes[0]['system'];excluded=[];allowed=list(seeds);allowed_handles={o['source_text']['handle'] for s in seeds for o in s['observations']}
    for other in all_seeds:
        line=doc.entitydb.get(other['source_line_handle'])
        if line is None or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[other['system']]:raise ValueError('other-system source owner changed')
        overlap=overlaps_pipe(line,scopes)
        if other['system']!=system or not overlap:
            excluded.extend(dict(text_handle=o['source_text']['handle'],edge_id=other['edge_id'],source_line_handle=line.dxf.handle,system=other['system'],
                relation='other_system' if other['system']!=system else 'independently_owned_nonoverlapping_pipe') for o in other['observations'])
        elif all(other['nominal_mm']==s['nominal_mm'] for s in seeds):
            handles={o['source_text']['handle'] for o in other['observations']}
            if not handles<=allowed_handles:allowed.append(other);allowed_handles.update(handles)
    private=dict(index,probes=[t for t in index['probes'] if t['handle'] not in {x['text_handle'] for x in excluded}])
    guard=annotation_guard(doc,allowed,scopes,private,source_hash,root)
    guard['freshly_qualified_other_pipe_source_captions']=excluded
    return guard


def through_line_evidence(doc,graph,target,seed,items,source_hash,graph_hash,tee_cache):
    if target['native_source_status']!='single_source_line_covers' or target['native_witnesses'][0]['scope']!='modelspace':
        raise ValueError('target needs one original modelspace pipe LINE')
    handle=target['native_witnesses'][0]['source_handle']
    if handle!=seed['source_line_handle']:raise ValueError('seed and target do not share the original LINE')
    line=doc.entitydb.get(handle)
    if line is None or line.dxftype()!='LINE' or line not in doc.modelspace() or line.dxf.layer!=LAYERS[target['system']]:
        raise ValueError('original same-system continuous LINE missing')
    ends=[list(line.dxf.start),list(line.dxf.end)];points=target['scope_points']+seed['scope_points']
    if not all(_on(p,ends[0][:2],ends[1][:2],.05) for p in points):raise ValueError('source LINE does not cover both domains')
    axis=0 if abs(ends[1][0]-ends[0][0])>abs(ends[1][1]-ends[0][1]) else 1
    low=min(points,key=lambda p:p[axis]);high=max(points,key=lambda p:p[axis]);nodes,_,adj=index_graph(graph);junctions=[]
    represented=[]
    for nid,node in sorted(nodes.items()):
        if node.get('node_type') not in ('tee','physical_junction') or not any(e['system']==target['system'] for e in adj[nid]):continue
        point=[node['x'],node['y']]
        if not _on(point,low,high,.05) or min(math.dist(point,p) for p in (low,high))<=.05:continue
        if nid not in tee_cache:
            try:tee_cache[nid]=dict(proof=native_tee(doc,graph,nid,source_hash,graph_hash))
            except (ValueError,KeyError,TypeError) as exc:tee_cache[nid]=dict(reason=str(exc))
        cached=tee_cache[nid]
        if 'proof' not in cached:raise ValueError('intervening T lacks current source evidence: '+cached['reason'])
        proof=cached['proof'];rays=proof.get('junctions',[{}])[0].get('source_rays',[])
        through=[r for r in rays if r.get('source_line_handle')==handle]
        if len(through)!=2 or len(rays)!=3:raise ValueError('source LINE is not the two through arms of the actual T')
        if {e['system'] for e in adj[nid]}!={target['system']}:raise ValueError('mixed-system T cannot inherit')
        junctions.append(copy.deepcopy(proof));represented.append(point)
    # A missing graph T must not disappear merely because the two main arms
    # happen to share a continuous source LINE. Ordinary interior crossings do
    # not become contacts here; unrepresented same-system endpoint contacts hold.
    main_item=dict(XYZ=ends)
    for item in items:
        if item['layer']!=line.dxf.layer or (item['root_handle'] is None and item['child_handle']==handle):continue
        a,b=item['XYZ'];v=[ends[1][i]-ends[0][i] for i in (0,1)];w=[b[i]-a[i] for i in (0,1)]
        if abs(v[0]*w[1]-v[1]*w[0])<=1e-6*math.hypot(*v)*math.hypot(*w):continue
        for p in (a,b):
            if (_on(p[:2],low,high,.05) and min(math.dist(p[:2],q) for q in (low,high))>.05
                and abs(p[2]-source_Z(main_item,p[:2]))<=.05 and not any(math.dist(p[:2],q)<=.05 for q in represented)):
                raise ValueError('native endpoint contact has no checked graph T')
    if target['edge_id']!=seed['edge_id'] and not junctions:raise ValueError('different graph edges lack an intervening verified through T')
    return dict(source_line_handle=handle,native_XYZ=ends,scope_points=[list(low),list(high)],junctions=junctions,
        source='same_original_LINE_through_current_native_Ts',branch_DN_used_as_main_seed=False,physical_length_mm=None)


def collect(doc,graph,route,prior,source_hash,graph_hash):
    before=encode(graph),encode(route),encode(prior)
    if graph['metadata']['source_sha256']!=source_hash or route['inputs']['source']['sha256']!=source_hash or route['inputs']['graph']['sha256']!=graph_hash:
        raise ValueError('source graph route binding differs')
    seeds=modelspace_seeds(doc,graph,route,source_hash,graph_hash);scopes={source_key(s):s for s in route['records']};edges={e['edge_id']:e for e in graph['edges']}
    if len(scopes)!=len(route['records']):raise ValueError('duplicate source route identities')
    for s in route['records']:
        e=edges[s['edge_id']]
        if e['system']!=s['system'] or e['attribute_paths'][s['path_index']][s['segment_index']:s['segment_index']+2]!=s['scope_points']:
            raise ValueError('route differs from original graph segment')
    index=annotation_index(doc,graph,source_hash);items=native_items(doc,graph);tee_cache={};records=[];pending=[];held=[]
    for p in prior['pending']:
        key=source_key(p);target=scopes[key]
        if p.get('original_reason')!='no_qualified_axis_annotation_on_this_vertical_segment':pending.append(copy.deepcopy(p));continue
        if target['direction_class']!='vertical':raise ValueError('pending target is not vertical')
        choices=[];failures=[]
        for seed in seeds['records']:
            if seed['system']!=target['system']:continue
            same_path=(seed['edge_id'],seed['path_index'])==(key[0],key[1])
            # A main can turn after the T: first find the source-owned through
            # arm on this original path, then replay its two-arm bends to the
            # vertical target. Comparing the seed only with the final vertical
            # LINE would miss this common composition.
            connectors=[s for s in route['records'] if (s['edge_id'],s['path_index'])==(key[0],key[1])
                and s['native_source_status']=='single_source_line_covers' and s['native_witnesses'][0]['scope']=='modelspace'
                and s['native_witnesses'][0]['source_handle']==seed['source_line_handle']]
            if not same_path and not connectors:continue
            try:
                if same_path:
                    low,high=sorted((seed['segment_index'],key[2]));corridor=[scopes[key[0],key[1],i] for i in range(low,high+1)]
                    continuity=chain_evidence(corridor,edges[key[0]].get('source_insert_handle'),items)
                    continuity['source']='same_original_attribute_path_and_two_arm_bends'
                    guard=scoped_guard(doc,[seed],corridor,index,source_hash,edges[key[0]].get('source_insert_handle'),seeds['records'])
                else:
                    qualified=[];rejected=[]
                    for connector in connectors:
                        try:
                            through=through_line_evidence(doc,graph,connector,seed,items,source_hash,graph_hash,tee_cache)
                            low,high=sorted((connector['segment_index'],key[2]));bend_scopes=[scopes[key[0],key[1],i] for i in range(low,high+1)]
                            bends=chain_evidence(bend_scopes,None,items)
                            corridor=[dict(target,scope_points=through['scope_points'])]+bend_scopes
                            guard=scoped_guard(doc,[seed],corridor,index,source_hash,None,seeds['records'])
                            qualified.append((dict(source='same_original_LINE_through_T_and_native_two_arm_bends',through=through,bends=bends,physical_length_mm=None),guard))
                        except ValueError as exc:rejected.append(str(exc))
                    if not qualified:raise ValueError('; '.join(sorted(set(rejected))))
                    continuity,guard=qualified[0]
                choices.append(dict(seed=seed,continuity_evidence=continuity,annotation_guard=guard))
            except ValueError as exc:failures.append(dict(seed_domain=list(source_key(seed)),reason=str(exc)))
        if choices and len({c['seed']['nominal_mm'] for c in choices})==1:
            records.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],scope_points=target['scope_points'],system=target['system'],
                floor_start=target['floor_start'],floor_end=target['floor_end'],nominal_mm=choices[0]['seed']['nominal_mm'],
                status='native_axis_continuous_source_vertical_DN',source='axis11_original_annotation_and_continuous_source',
                candidate_evidence=choices,physical_length_mm=None,whole_edge_DN_assigned=False,human_accepted=False))
        else:
            pending.append(copy.deepcopy(p));held.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],
                reason='conflicting_native_scope_seeds' if choices else 'no_source_qualified_continuous_seed_corridor',candidate_failures=failures))
    if before!=(encode(graph),encode(route),encode(prior)):raise ValueError('original inputs mutated')
    if len(records)+len(pending)!=len(prior['pending']):raise ValueError('pending domain conservation differs')
    return dict(mode=MODE,records=records,pending=pending,candidate_diagnostics=held,native_seed_qualification=seeds,
        counts=dict(previous_known=prior['counts']['current_known'],previous_unknown=len(prior['pending']),new_known=len(records),
            current_known=prior['counts']['current_known']+len(records),remaining_unknown=len(pending),
            fresh_horizontal_seed_domains=sum(s['direction_class']=='horizontal' for s in seeds['records']),fresh_vertical_seed_domains=sum(s['direction_class']=='vertical' for s in seeds['records'])),
        graph_mutated=False,horizontal_final_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)


def compute(manifest):
    inputs=manifest['inputs']
    def check():
        if any(sha(v['path'])!=v['sha256'] for v in inputs.values()):raise ValueError('fixed native input changed')
    check();prior=load(inputs['prior_omission_DN']['path']);route=load(inputs['routing']['path'])
    provider=load(inputs['parent_provider']['path']);viewer=load(inputs['parent_viewer_manifest']['path'])
    if (prior['inputs']['axis_source']['sha256']!=inputs['axis_source']['sha256'] or prior['inputs']['axis_graph']['sha256']!=inputs['axis_graph']['sha256']
        or provider['counts']['all_current_vertical_DN_domains']!=prior['counts']['current_known']
        or viewer['attributeValueContext']['omission_vertical_DN']['all_current_vertical_domains']!=prior['counts']['current_known']
        or len({source_key(p) for p in prior['pending']})!=len(prior['pending'])
        or prior['counts']['current_known']+len(prior['pending'])!=sum(s['direction_class']=='vertical' for s in route['records'])):
        raise ValueError('current published vertical parent population differs')
    doc,preflight=read_source(inputs['axis_source']['path'])
    result=collect(doc,load(inputs['axis_graph']['path']),route,prior,inputs['axis_source']['sha256'],inputs['axis_graph']['sha256'])
    check();result.update(inputs=inputs,source_preflight=preflight,published=False);return result

def implementations():
    names=('axis_unbranched_vertical_DN','axis_vertical_DN_batch','native_segment_dn_candidates_v2','native_segment_dn_candidates',
        'native_line_path_evidence','crossview_equipment_branch_inventory','pipe_annotation_attributes','native_paired_caption_geometry','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__) for n in names})

def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);target=output/'continuous-source-vertical-DN.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementations(),output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'continuous-source-vertical-DN.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementations() or sha(m['path'])!=m['sha256'] or sha(target)!=receipt['output_sha256']:raise ValueError('source code or evidence changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('independent continuous-source native replay differs')
    return fresh

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(produce(a.manifest,a.output)['counts'],flush=True)
