"""Reuse the original direct segment reader on all native WCS pipe LINEs.

The reading document is private and reversible. Original text transforms,
F precedence, every graph-referenced pipe competitor and neutral layer-0
competitors remain checked. No repeated block-name template is learned here.
"""
import copy,hashlib,math
import ezdxf
from ezdxf.disassemble import recursive_decompose
from confirm_crossview_paths import encode
from native_repeated_branch_DN_layout import primitives,candidates
from native_paired_caption_geometry import leader_claims
from native_segment_dn_candidates_v2 import collect as direct_reader
from axis_local_DN_segment_domains import locate
from source_direct_dn_evidence import _projection
from native_line_path_evidence import LAYERS,_on
from native_dn_text_position import supported
from calibrated_direct_dn_evidence import profile
from pipe_annotation_attributes import source_texts,parse_dn_annotation

MODE='native_nested_direct_segment_DN_reapplication_v1'

def projection(doc,graph,source_hash):
    private=ezdxf.new('R2013');nested=primitives(doc,graph)
    items=nested+[dict(root_handle=None,child_handle=e.dxf.handle,XYZ=[list(e.dxf.start),list(e.dxf.end)],layer=e.dxf.layer)for e in doc.modelspace().query('LINE')if e.dxf.layer in LAYERS.values()]
    neutral=[]
    for root in sorted({e.get('source_insert_handle')for e in graph['edges']if e.get('source_insert_handle')}):
        entity=doc.entitydb.get(root)
        if entity is None or entity not in doc.modelspace():raise ValueError('original graph source root missing')
        if entity.dxftype()!='INSERT':continue
        for e in recursive_decompose([entity]):
            if e.dxftype()=='LINE'and e.dxf.layer=='0':
                if e.source_of_copy is None:raise ValueError('neutral nested source identity missing')
                neutral.append(dict(root_handle=root,child_handle=e.source_of_copy.dxf.handle,XYZ=[list(e.dxf.start),list(e.dxf.end)],layer='0'))
    edges=[];lines=[];links={};text_links={}
    for i,item in enumerate(items):
        line=private.modelspace().add_line(*item['XYZ'],dxfattribs={'layer':item['layer']});eid='native-pipe-'+str(i);a,b=[p[:2]for p in item['XYZ']];system=next(s for s,l in LAYERS.items()if l==item['layer']);links[eid]=dict(source_item=copy.deepcopy(item),private_LINE=line.dxf.handle)
        edges.append(dict(edge_id=eid,system=system,attribute_paths=[[a,b]],source_handles=[line.dxf.handle]))
        lines.append(dict(edge_id=eid,system=system,segments=[dict(segment_index=0,graph_start=a,graph_end=b,source_handle=line.dxf.handle)]))
    # Copy all annotation competitors, not just the selected target. The old
    # reader's F and transform checks execute on this private document as well.
    for e in doc.modelspace():
        if e.dxftype()not in('TEXT','MTEXT','LINE','LWPOLYLINE'):continue
        if e.dxftype()=='LINE'and e.dxf.layer in LAYERS.values():continue
        c=e.copy();private.modelspace().add_entity(c)
        if e.dxftype()in('TEXT','MTEXT'):text_links[e.dxf.handle]=c.dxf.handle
    pg=dict(metadata=dict(source_sha256=source_hash,scope='private_native_pipe_reading_projection'),edges=edges);gh=hashlib.sha256(encode(pg)).hexdigest()
    evidence=dict(status='geometry_evidence_unreviewed',source_sha256=source_hash,graph_sha256=gh,edges=lines);lh=hashlib.sha256(encode(evidence)).hexdigest()
    return private,pg,evidence,gh,lh,links,text_links,nested,neutral

def neutral_guard(text,item,neutral):
    angle=math.radians(text['rotation']);axis=[math.cos(angle),math.sin(angle)];q=_projection(text['position'],*([p[:2]for p in item['XYZ']]))
    if q is None:raise ValueError('selected native pipe projection missing')
    hits=[]
    for other in neutral:
        a,b=[p[:2]for p in other['XYZ']];v=[b[i]-a[i]for i in(0,1)];length=math.hypot(*v)
        if length<=.05 or abs(axis[0]*v[1]-axis[1]*v[0])/length>math.sin(math.radians(2)):continue
        foot=_projection(text['position'],a,b)
        if foot and 0<foot[0]<1 and foot[1]<=2*text['height']:hits.append(dict(source_item=copy.deepcopy(other),distance=foot[1]))
    if any(h['distance']-q[1]<=.5*text['height']for h in hits):raise ValueError('neutral layer0 source competes under original direct-reader margin')
    return dict(complete_neutral_population=len(neutral),eligible_neutral_competitors=hits,original_half_text_height_margin_preserved=True)

def collect(doc,graph,route,handles,source_hash,graph_hash):
    if not handles or len(set(handles))!=len(handles)or graph['metadata']['source_sha256']!=source_hash or route['inputs']['source']['sha256']!=source_hash or route['inputs']['graph']['sha256']!=graph_hash:raise ValueError('current unique native annotation/graph/route identities required')
    before=encode(graph),encode(route);private,pg,lines,ph,lh,links,text_links,nested,neutral=projection(doc,graph,source_hash)
    texts=source_texts(doc,'axis',source_hash);by={t['handle']:t for t in texts}
    if any('\ufffd'in t['text']for t in texts):raise ValueError('native Chinese unreadable')
    guardtexts=[dict(t,profile=profile(doc,doc.entitydb[t['handle']]))for t in texts if doc.entitydb[t['handle']].dxftype()=='TEXT'and supported(doc.entitydb[t['handle']])and parse_dn_annotation(t['text'])]
    F=leader_claims(doc,guardtexts);rows=[];held=[];scopes={(s['edge_id'],s['path_index'],s['segment_index']):s for s in route['records']}
    for h in handles:
        try:
            t=by.get(h);entity=doc.entitydb.get(h)
            if t is None or entity is None or not supported(entity)or entity.dxftype()!='TEXT'or not parse_dn_annotation(t['text']):raise ValueError('supported native scalar TEXT required')
            if h in F:raise ValueError('original F reader owns selected text')
            hits=candidates(doc,graph,t,nested)
            if not hits or hits[0]['root_handle']is None or not hits[0]['Z_coincident']or len(hits[0]['current_graph_owners'])!=1:raise ValueError('unique nested native Z and current graph owner required')
            hit=hits[0];bindings=[(eid,link)for eid,link in links.items()if link['source_item'].get('root_handle')==hit['root_handle']and link['source_item']['child_handle']==hit['child_handle']and link['source_item']['XYZ']==hit['XYZ']]
            if len(bindings)!=1:raise ValueError('native source primitive has competing private identities')
            eid,link=bindings[0];ng=neutral_guard(t,hit,neutral);th=text_links[h]
            proof=direct_reader(private,pg,lines,dict(source_sha256=source_hash,graph_sha256=ph,line_evidence_sha256=lh,text_layers=sorted({x['layer']for x in texts}),selections=[dict(text_handle=th,expected_text=t['text'],edge_id=eid,segment_index=0)]),source_hash,ph,lh)
            observation=proof['observations'][0]
            if observation['source_line_handle']!=link['private_LINE']or math.dist(observation['graph_projection'],hit['projection'])>.05:raise ValueError('original direct reader source projection differs')
            value=parse_dn_annotation(t['text'])['nominal_mm'];owner=dict(source_text=copy.deepcopy(t),nominal_mm_candidate=value,source_chain=[hit['root_handle'],hit['child_handle']],current_edge_id=hit['current_graph_owners'][0],native_binding=copy.deepcopy(hit),scope='native_nested_branch_annotation_only_not_whole_edge_DN',whole_edge_DN_assigned=False,human_accepted=False)
            domains=locate(graph,dict(records=[owner],source_sha256=source_hash,graph_sha256=graph_hash,graph_mutated=False,physical_values_fused=False,human_accepted=False),source_hash,graph_hash)
            if len(domains['records'])!=1:raise ValueError('unique exact graph segment required')
            domain=domains['records'][0];seg=domain['segment'];key=domain['edge_id'],seg['path_index'],seg['segment_index'];scope=scopes[key]
            if scope['direction_class']!='vertical'or scope['native_source_status']!='single_source_line_covers'or scope['scope_points']!=seg['scope_points']:raise ValueError('one original vertical routing witness required')
            if len(scope['native_witnesses'])!=1 or scope['native_witnesses'][0]['source_handle']!=hit['root_handle']or scope['native_witnesses'][0]['layer']!=hit['layer']:raise ValueError('original routing root/layer differs')
            rows.append(dict(edge_id=key[0],path_index=key[1],segment_index=key[2],scope_points=copy.deepcopy(scope['scope_points']),system=scope['system'],floor_start=scope['floor_start'],floor_end=scope['floor_end'],nominal_mm=value,observations=[dict(source_text=copy.deepcopy(t),nominal_mm=value,native_evidence=owner)],direct_reader_evidence=proof,original_native_owner=owner,neutral_competitor_evidence=ng,native_witnesses=copy.deepcopy(scope['native_witnesses']),source='axis11_original_direct_reader_on_complete_nested_WCS_projection',whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
        except ValueError as exc:held.append(dict(text_handle=h,reason=str(exc)))
    if len({(r['edge_id'],r['path_index'],r['segment_index'])for r in rows})!=len(rows):raise ValueError('competing direct values require transition scope')
    if before!=(encode(graph),encode(route)):raise ValueError('original graph/routing mutated')
    return dict(mode=MODE,records=rows,held=held,private_graph_sha256=ph,private_line_evidence_sha256=lh,native_projection_links=links,original_to_private_text_handles=text_links,complete_native_pipe_population=len(links),complete_neutral_population=len(neutral),F_owned_text_handles=sorted(F),original_direct_reader_and_margin_unchanged=True,repeated_layout_threshold_changed=False,graph_mutated=False,horizontal_values_assigned=0,physical_lengths_assigned=0,human_accepted=False)
