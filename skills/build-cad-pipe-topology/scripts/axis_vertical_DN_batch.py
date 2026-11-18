"""Batch inherited modelspace/nested readers on native vertical segment domains.

Only original witnessed segment identities receive a local annotation value.
The repeated-layout reader still requires four independent source instances;
targets do not train themselves. Physical lengths and whole-edge DN stay unknown.
"""
import argparse,collections,concurrent.futures,copy,hashlib,importlib,math,sys
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from axis_attribute_source_routing import verify_output as verify_routing
from source_readability import read_source
from pipe_annotation_attributes import source_texts,parse_dn_annotation,direct_diameters,recognize_f_leaders
from native_paired_caption_geometry import collect as paired_captions
from native_segment_dn_candidates_v2 import collect as direct_reader
from native_repeated_branch_DN_layout import collect as repeated_reader
from axis_local_DN_segment_domains import locate
MODE='native_axis_vertical_segment_DN_batch_v1'

def projection(graph,route):
    raw={e['edge_id']:e for e in graph['edges']};private=dict(metadata=copy.deepcopy(graph['metadata']),nodes=[],edges=[]);index={};witness=[]
    for scope in route['records']:
        pid=f"AXIS-DN-SEG:{scope['edge_id']}:{scope['path_index']}:{scope['segment_index']}";index[pid]=scope;original=raw[scope['edge_id']]
        edge=dict(edge_id=pid,start_node_id=pid+':A',end_node_id=pid+':B',system=scope['system'],source_insert_handle=original.get('source_insert_handle'),
            connection_mode=original.get('connection_mode'),attribute_paths=[copy.deepcopy(scope['scope_points'])],read_only_attribute_projection=True)
        private['edges'].append(edge)
        for label,point in zip(('A','B'),scope['scope_points']):private['nodes'].append(dict(node_id=pid+':'+label,node_type='read_only_attribute_cut_not_physical_node',x=point[0],y=point[1]))
        witness.append(dict(edge_id=pid,system=scope['system'],segments=[dict(segment_index=0,graph_start=scope['scope_points'][0],graph_end=scope['scope_points'][1],
            source_handle=scope['native_witnesses'][0]['source_handle']if scope['native_source_status']=='single_source_line_covers'else None)]))
    ph=hashlib.sha256(encode(private)).hexdigest();evidence=dict(status='geometry_evidence_unreviewed',source_sha256=route['inputs']['source']['sha256'],graph_sha256=ph,edges=witness)
    return private,index,evidence,ph

def recursive_qualification(handles,reader):
    pieces=[]
    def split(selected):
        if not selected:return
        try:pieces.append(dict(status='passed',handles=selected,result=reader(selected)))
        except ValueError as exc:
            if len(selected)==1:pieces.append(dict(status='pending',handles=selected,reason=str(exc)))
            else:mid=len(selected)//2;split(selected[:mid]);split(selected[mid:])
    split(handles);return pieces

def initialize(source,graph,expected_source,expected_graph):
    global _DOC,_GRAPH,_SH,_GH
    if sha(source)!=expected_source or sha(graph)!=expected_graph:raise ValueError('native worker inputs changed')
    _DOC,_=read_source(Path(source));_GRAPH=load(graph);_SH=expected_source;_GH=expected_graph

def repeated_job(handles):
    def reader(selected):
        proof=repeated_reader(_DOC,_GRAPH,selected,_SH,_GH);return dict(ownership=proof,domains=locate(_GRAPH,proof,_SH,_GH))
    return recursive_qualification(handles,reader)

def consolidate(route,observations,blocked):
    grouped=collections.defaultdict(list);records=[];pending=[]
    for observation in observations:grouped[(observation['edge_id'],observation['path_index'],observation['segment_index'])].append(observation)
    for scope in route['records']:
        if scope['direction_class']!='vertical':continue
        key=(scope['edge_id'],scope['path_index'],scope['segment_index']);items=grouped.get(key,[])
        reason='native_source_LINE_not_yet_witnessed'if scope['native_source_status']!='single_source_line_covers'else blocked.get(key)
        values={r['nominal_mm']for r in items}
        if not reason and any(isinstance(v,bool)or not isinstance(v,(int,float))or not math.isfinite(v)or v<=0 for v in values):reason='invalid_native_DN_value'
        if not reason and len(values)>1:reason='multiple_native_DN_values_need_transition_extent'
        if not reason and not values:reason='no_qualified_axis_annotation_on_this_vertical_segment'
        if reason:pending.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],reason=reason,observations=items));continue
        record=dict(edge_id=key[0],path_index=key[1],segment_index=key[2],system=scope['system'],floor_start=scope['floor_start'],floor_end=scope['floor_end'],scope_points=copy.deepcopy(scope['scope_points']),
            nominal_mm=next(iter(values)),status='native_axis_vertical_annotation_segment_DN',observations=copy.deepcopy(items),native_witnesses=scope['native_witnesses'],
            source='axis_11_native_annotation_even_same_floor',whole_edge_DN_assigned=False,physical_length_mm=None,whole_edge_physical_length_mm=None,human_accepted=False)
        records.append(record)
    return records,pending

def collect(doc,graph,route,source_path,graph_path,workers=12):
    if route['inputs']['source']['sha256']!=sha(source_path)or route['inputs']['graph']['sha256']!=sha(graph_path)or graph['metadata']['source_sha256']!=sha(source_path):raise ValueError('vertical batch source/routing graph differs')
    if not 1<=workers<=22:raise ValueError('vertical batch workers must be1..22')
    private,index,lines,ph=projection(graph,route);texts=source_texts(doc,'axis',sha(source_path));layers={t['layer']for t in texts}
    if any('\ufffd'in t['text']for t in texts):raise ValueError('unreadable native axis annotation')
    F={t['handle']for f in recognize_f_leaders(doc,texts,[],graph['edges'],layers)for t in f['texts']}|set(paired_captions(doc)['F_owned_texts'])
    assigned,ambiguous=direct_diameters(texts,private['edges'],F,layers);blocked={}
    def key(scope):return(scope['edge_id'],scope['path_index'],scope['segment_index'])
    for row in ambiguous:
        for pid in row['candidate_edge_ids']:
            if index[pid]['direction_class']=='vertical':blocked[key(index[pid])]='ambiguous_native_text_projection_requires_ownership_rule'
    # Preserve unresolved compound/qualified text as a scope barrier.
    probes=[dict(t,text='DN1')for t in texts if 'DN'in t['text'].upper()and parse_dn_annotation(t['text'])is None]
    pa,pp=direct_diameters(probes,private['edges'],set(),layers)
    for row in pa+pp:
        for pid in([row['edge_id']]if row['status']=='assigned'else row['candidate_edge_ids']):
            if index[pid]['direction_class']=='vertical':blocked[key(index[pid])]='unparsed_or_qualified_native_DN_needs_its_original_reader'
    direct=[];nested=collections.defaultdict(list);selection_index={}
    for row in assigned:
        scope=index[row['edge_id']]
        if scope['direction_class']!='vertical'or scope['native_source_status']!='single_source_line_covers':continue
        h=row['text']['handle'];spec=dict(text_handle=h,edge_id=row['edge_id'],segment_index=0,expected_text=row['text']['text']);selection_index[h]=dict(spec=spec,scope=scope)
        witness=scope['native_witnesses'][0]
        if witness['scope']=='modelspace':direct.append(h)
        elif witness['scope']=='decomposed_selected_insert':nested[witness['source_handle']].append(h)
        else:blocked[key(scope)]='unsupported_native_vertical_witness_scope'
    sh,gh=sha(source_path),sha(graph_path);lh=hashlib.sha256(encode(lines)).hexdigest()
    def direct_work(handles):
        policy=dict(source_sha256=sh,graph_sha256=ph,line_evidence_sha256=lh,text_layers=sorted(layers),selections=[selection_index[h]['spec']for h in handles])
        return direct_reader(doc,private,lines,policy,sh,ph,lh)
    direct_pieces=recursive_qualification(direct,direct_work);observations=[]
    for piece in direct_pieces:
        if piece['status']!='passed':
            for h in piece['handles']:blocked[key(selection_index[h]['scope'])]=piece['reason']
            continue
        for r in piece['result']['observations']:
            scope=selection_index[r['source_text']['handle']]['scope'];observations.append(dict(edge_id=scope['edge_id'],path_index=scope['path_index'],segment_index=scope['segment_index'],
                nominal_mm=r['nominal_mm_candidate'],reader='inherited_modelspace_segment_DN_reader',source_text=r['source_text'],native_evidence=r))
    groups=[[]for _ in range(min(workers,max(1,len(nested)//4)))]
    for i,(_,handles)in enumerate(sorted(nested.items())):groups[i%len(groups)].extend(handles)
    results=[]
    if nested:
        with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers,len(groups)),initializer=initialize,initargs=(str(source_path),str(graph_path),sh,gh))as pool:
            futures={pool.submit(repeated_job,group):i for i,group in enumerate(groups)}
            for future in concurrent.futures.as_completed(futures):results.append(dict(batch=futures[future],pieces=future.result()))
    results.sort(key=lambda r:r['batch'])
    for batch in results:
        for piece in batch['pieces']:
            if piece['status']!='passed':
                for h in piece['handles']:blocked[key(selection_index[h]['scope'])]=piece['reason']
                continue
            domains={r['text_handle']:r for r in piece['result']['domains']['records']}
            for r in piece['result']['ownership']['records']:
                h=r['source_text']['handle'];scope=selection_index[h]['scope'];d=domains[h]
                if (d['edge_id'],d['segment']['path_index'],d['segment']['segment_index'])!=key(scope)or d['segment']['scope_points']!=scope['scope_points']or r['source_chain'][0]!=scope['native_witnesses'][0]['source_handle']:raise ValueError('nested ownership differs from exact native routing domain')
                observations.append(dict(edge_id=d['edge_id'],path_index=d['segment']['path_index'],segment_index=d['segment']['segment_index'],nominal_mm=r['nominal_mm_candidate'],
                    reader='inherited_repeated_native_branch_layout_and_segment_domain',source_text=r['source_text'],native_evidence=r))
    records,pending=consolidate(route,observations,blocked)
    return dict(mode=MODE,records=records,pending=pending,counts=dict(vertical_segments=sum(r['direction_class']=='vertical'for r in route['records']),
        direct_candidate_texts=len(direct),nested_candidate_texts=sum(map(len,nested.values())),qualified_vertical_segments=len(records),same_floor_qualified=sum(r['floor_start']==r['floor_end']for r in records),
        interfloor_qualified=sum(r['floor_start']!=r['floor_end']for r in records),pending_vertical_segments=len(pending)),
        direct_native_qualification=direct_pieces,repeated_native_qualification=results,reading_projection_sha256=ph,F_owned_texts=sorted(F),
        source_sha256=sh,graph_sha256=gh,graph_mutated=False,horizontal_plan_attributes_changed=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False)

def compute(manifest):
    paths={k:Path(r['path'])for k,r in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=r['sha256']for k,r in manifest['inputs'].items()):raise ValueError('vertical batch input changed')
    checked();route=verify_routing(paths['routing'].parent);doc,preflight=read_source(paths['source']);result=collect(doc,load(paths['graph']),route,paths['source'],paths['graph'],manifest.get('workers',12));checked()
    result.update(source_preflight=preflight,source_bindings={k:dict(path=str(p.resolve()),sha256=sha(p))for k,p in paths.items()});return result

def implementation_hashes():
    names=('axis_vertical_DN_batch','axis_attribute_source_routing','native_repeated_branch_DN_layout','axis_local_DN_segment_domains','native_segment_dn_candidates_v2','native_segment_dn_candidates','native_dn_text_position','native_paired_caption_geometry','native_paired_end_labels','native_line_f_diameter_evidence','native_line_path_evidence','source_direct_dn_evidence','pipe_annotation_attributes','source_dn_bulk_screen','calibrated_direct_dn_evidence','source_readability')
    return {n:sha(importlib.import_module(n).__file__)for n in names}
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest));output.mkdir(parents=True);target=output/'vertical-DN.json';target.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)));return result
def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'vertical-DN.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']:raise ValueError('vertical batch implementation or artifact changed')
    result=compute(load(m['path']))
    if encode(result)!=target.read_bytes():raise ValueError('independent native vertical DN batch differs')
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'))
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:result=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and new output required')
            result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
