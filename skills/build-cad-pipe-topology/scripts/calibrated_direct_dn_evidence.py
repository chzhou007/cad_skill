"""Bind ambiguous scalar DN text using independently checked native controls.

Learn the annotation side for one exact native text profile. Never presume a
global above/left convention, use target labels as controls, or assign a
whole-edge diameter. F leaders and unparsed/conflicting annotations stay out.
"""
import argparse,json,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from source_direct_dn_evidence import collect as strict_collect,_projection,LAYERS
from native_dn_text_position import supported
from pipe_annotation_attributes import source_texts,direct_diameters,parse_dn_annotation,recognize_f_leaders


def profile(doc,entity):
    style=doc.styles.get(entity.dxf.style)
    return dict(style=entity.dxf.style,font=style.dxf.get('font',''),bigfont=style.dxf.get('bigfont',''),height=entity.dxf.height,
        width=entity.dxf.get('width',1.),layer=entity.dxf.layer,oblique=entity.dxf.get('oblique',0),text_generation_flag=entity.dxf.get('text_generation_flag',0))


def collect(doc,graph,policy,source_hash,graph_hash):
    if (policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash
        or graph.get('metadata',{}).get('source_sha256')!=source_hash):raise ValueError('calibrated DN source/graph differs')
    controls=policy.get('controls',[]);targets=policy.get('selections',[]);all_specs=controls+targets
    if len(controls)<4 or not targets or len({r['text_handle'] for r in all_specs})!=len(all_specs):raise ValueError('independent controls and disjoint target texts required')
    texts=source_texts(doc,'plan',source_hash);bytext={t['handle']:t for t in texts};edges={e['edge_id']:e for e in graph['edges']};layers=set(policy.get('text_layers',[]))
    if len(edges)!=len(graph['edges']) or not layers:raise ValueError('invalid calibrated DN graph/layers')
    frames=recognize_f_leaders(doc,texts,[],graph['edges'],layers);F={t['handle'] for frame in frames for t in frame['texts']}
    if any(r['text_handle'] in F for r in all_specs):raise ValueError('F leader text requires its ordered leader feature')
    control_rows=[]
    for spec in controls:
        proof=strict_collect(doc,graph,dict(source_sha256=source_hash,graph_sha256=graph_hash,text_layers=sorted(layers),selections=[spec]),source_hash,graph_hash)
        row=proof['observations'][0];native=doc.entitydb[spec['text_handle']];angle=math.radians(native.dxf.rotation)
        normal=[-math.sin(angle),math.cos(angle)];signed=sum((row['source_text']['position'][i]-row['graph_projection'][i])*normal[i] for i in (0,1))
        if abs(signed)<=.05:raise ValueError('control annotation side is unresolved')
        control_rows.append(dict(spec=spec,profile=profile(doc,native),side=1 if signed>0 else -1,signed_text_normal_distance=signed,axis=[math.cos(angle),math.sin(angle)],native_evidence=row))
    assigned,pending=direct_diameters(texts,graph['edges'],set(),layers);selected_texts={r['text_handle'] for r in targets};selected_edges={r['edge_id'] for r in targets}
    for row in pending:
        if selected_edges.intersection(row['candidate_edge_ids']) and row['text']['handle'] not in selected_texts:raise ValueError('another unresolved DN annotation overlaps calibrated target')
    unparsed=[dict(t,text='DN1') for t in texts if t['layer'] in layers and 'DN' in t['text'].upper() and parse_dn_annotation(t['text']) is None]
    a,p=direct_diameters(unparsed,graph['edges'],set(),layers)
    if any(selected_edges.intersection(r['candidate_edge_ids']) for r in a+p):raise ValueError('unparsed DN overlaps calibrated target')
    observations=[]
    for spec in targets:
        native=doc.entitydb.get(spec['text_handle']);text=bytext.get(spec['text_handle']);edge=edges.get(spec['edge_id'])
        if (native is None or not supported(native) or not text or text['layer'] not in layers or text['text']!=spec['expected_text']
            or not edge or edge.get('system') not in LAYERS):raise ValueError('calibrated target text/edge/transform differs')
        label=parse_dn_annotation(text['text'])
        if not label:raise ValueError('calibrated target is not a scalar DN')
        matched=[r for r in control_rows if r['profile']==profile(doc,native)]
        if (len({r['spec']['source_line_handle'] for r in matched})<4 or {r['native_evidence']['system'] for r in matched}!={'supply','return'}
            or len({r['side'] for r in matched})!=1 or not any(abs(a['axis'][0]*b['axis'][1]-a['axis'][1]*b['axis'][0])>.5 for a in matched for b in matched)):
            raise ValueError('native text profile lacks independent two-service/two-direction side calibration')
        angle=math.radians(native.dxf.rotation);axis=[math.cos(angle),math.sin(angle)];normal=[-axis[1],axis[0]];side=matched[0]['side'];hits=[];rejected=[]
        for line in doc.modelspace().query('LINE'):
            if line.dxf.layer not in LAYERS.values():continue
            a,b=list(line.dxf.start)[:2],list(line.dxf.end)[:2];length=math.dist(a,b)
            if length<=.05 or abs(axis[0]*(b[1]-a[1])-axis[1]*(b[0]-a[0]))/length>math.sin(math.radians(2)):continue
            projection=_projection(text['position'],a,b)
            if not projection or not 0<projection[0]<1 or not .05<projection[1]<=2*text['height']:continue
            signed=sum((text['position'][i]-projection[2][i])*normal[i] for i in (0,1));item=dict(handle=line.dxf.handle,distance=projection[1],signed_text_normal_distance=signed,point=list(projection[2]),source_layer=line.dxf.layer)
            (hits if signed*side>.05 else rejected).append(item)
        if len(hits)!=1 or hits[0]['handle']!=spec['source_line_handle'] or hits[0]['source_layer']!=LAYERS[edge['system']] or spec['source_line_handle'] not in edge.get('source_handles',[]):raise ValueError('calibrated target native pipe is not unique or changed')
        point=hits[0]['point'];locations=[]
        for pi,path in enumerate(edge.get('attribute_paths',[])):
            for si,(a,b) in enumerate(zip(path,path[1:])):
                q=_projection(point,a,b)
                if q and 0<q[0]<1 and q[1]<=.05:locations.append(dict(path_index=pi,segment_index=si))
        if len(locations)!=1:raise ValueError('calibrated label has no unique current edge segment')
        if any(r['edge_id']==spec['edge_id'] and r['nominal_mm']!=label['nominal_mm'] for r in assigned):raise ValueError('conflicting direct DN requires subdivision')
        observations.append(dict(edge_id=spec['edge_id'],system=edge['system'],nominal_mm=label['nominal_mm'],parenthesized_source_value=label['parenthesized_source_value'],
            status='candidate_source_annotation',source_text=text,source_line_handle=spec['source_line_handle'],graph_projection=point,source_pipe_candidates=hits,
            calibration_controls=[r['spec']['text_handle'] for r in matched],calibrated_text_normal_side=side,rejected_wrong_side_native_pipes=rejected,
            local_scope_only=True,physical_length_from_parentheses=False,human_accepted=False))
    from plan_pipe_diameter_scopes import guard_leader_bridges
    guard_leader_bridges(doc,texts,[p for eid in selected_edges for p in edges[eid]['attribute_paths']])
    return dict(schema_version=1,source_sha256=source_hash,graph_sha256=graph_hash,status='source_calibrated_local_DN_candidates_not_edgewide',observations=observations,
        calibration=control_rows,graph_mutated=False,hil_ready=False,human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    doc,preflight=read_source(a.source);result=collect(doc,load(a.graph),load(a.policy),sha(a.source),sha(a.graph));a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes(encode(dict(result,source_preflight=preflight,policy_sha256=sha(a.policy),implementation_sha256=sha(__file__))));print(json.dumps(dict(observations=len(result['observations']),controls=len(result['calibration']),graph_mutated=False,human_accepted=False)))


if __name__=='__main__':main()
