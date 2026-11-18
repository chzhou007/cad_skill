"""Batch inherited named-riser and external-interface source readers.

Names on different native targets retain separate roles. Observed circle/port
DN is not a horizontal pipe DN, and a shared marker creates no connection.
"""
import argparse,copy,hashlib,json,math,re
from pathlib import Path
from native_named_riser_evidence import collect as named_collect,underlines,xyz,at,label
from native_external_pipe_destination import collect as external_plan_collect
from native_external_port_destination import collect as external_axis_collect
from native_dn_text_position import supported
from native_line_path_evidence import LAYERS
from source_readability import read_source
from confirm_crossview_paths import load,sha,encode

MODE='complete_native_named_pipe_interface_batch_v1'

def discover(doc,graph,sh,gh,family,text_layers,leader_layers,external_templates=()):
    if family not in ('plan','axis')or graph.get('metadata',{}).get('source_sha256')!=sh or not text_layers or not leader_layers:raise ValueError('explicit current source/graph family and text/leader layers required')
    text_layers=set(text_layers);leader_layers=set(leader_layers);lines=list(doc.modelspace().query('LINE'));nodes=graph['nodes']
    texts=[t for t in doc.modelspace().query('TEXT MTEXT')if re.search(r'CHW[SR]\s*\d',t.plain_text(),re.I)]
    by_text={t.dxf.handle:t for t in texts};claimed={};groups=[];provider_issues=[]
    for index,template in enumerate(external_templates):
        origin=template['policy'];kind=template['kind']
        if kind not in ('plan_frontiers','axis_ports')or (kind=='plan_frontiers')!=(family=='plan')or origin['source_sha256']!=sh:raise ValueError('external template family or original native source differs')
        handles=[m['text_handle']for m in origin['members']]
        if len(set(handles))!=len(handles)or not set(handles)<=set(by_text)or set(handles)&set(claimed):raise ValueError('external text ownership repeated or missing from complete source inventory')
        policy=copy.deepcopy(origin);policy.update(source_sha256=sh,graph_sha256=gh)
        try:
            collector=external_plan_collect if kind=='plan_frontiers'else external_axis_collect
            evidence=collector(doc,graph,policy,sh,gh)
        except(ValueError,KeyError,TypeError)as exc:
            issue=dict(provider_index=index,kind=kind,reason='external_native_provider_rejected',detail=str(exc),text_handles=handles);provider_issues.append(issue)
            for handle in handles:claimed[handle]=dict(status='pending',text_handle=handle,raw_text=by_text[handle].plain_text(),reason=issue['reason'],detail=issue['detail'])
            continue
        groups.append(dict(kind=kind,derived_current_policy=policy,evidence=evidence))
        rows={r['native_name_evidence']['text_handle']if kind=='plan_frontiers'else r['native_name']['text_handle']:r for r in evidence['records']}
        if set(rows)!=set(handles):raise ValueError('external native source membership differs')
        for handle in handles:
            row=rows[handle];claimed[handle]=dict(status='source_witnessed',text_handle=handle,raw_text=by_text[handle].plain_text(),identifier=row['identifier'],system=row['system'],
                role='external_plan_frontier'if kind=='plan_frontiers'else'external_axis_port',node_id=row['node_id'],floor=row['floor'],
                observed_named_DN_mm=row.get('local_nominal_mm_observed',row.get('nominal_mm_observed')),native_evidence=row)
    selections=[];pending=[]
    for text in texts:
        handle=text.dxf.handle;raw=text.plain_text()
        if handle in claimed:continue
        try:
            parsed=label(raw)
            if not supported(text)or text.dxf.layer not in text_layers:raise ValueError('unsupported_native_text_or_layer')
            underline=underlines(doc,text,leader_layers)
            if len(underline)!=1:raise ValueError('ambiguous_or_missing_native_underline')
            joins=[]
            for line in lines:
                if line is underline[0]or line.dxf.layer not in leader_layers:continue
                for point in xyz(underline[0]):
                    for i,p in enumerate(xyz(line)):
                        if math.dist(point,p)<=.05:joins.append((line,1-i))
            if len(joins)!=1:raise ValueError('ambiguous_or_missing_native_leader')
            leader,other=joins[0];tip=xyz(leader)[other];targets=[]
            if family=='plan':
                for node in nodes:
                    if node.get('subtype')!='out_of_plane_riser'or node.get('system')!=parsed['system']:continue
                    circle=doc.entitydb.get(node.get('source_handle',''))
                    if circle and circle.dxftype()=='CIRCLE'and math.dist(tip,list(circle.dxf.center))<=.05:targets.append(dict(kind='plan_riser_circle',node_id=node['node_id'],circle_handle=circle.dxf.handle))
            else:
                hits=[line for line in lines if line.dxf.layer in LAYERS.values()and at(tip,line)]
                if len(hits)==1:targets=[dict(kind='axis_source_line',line_handle=hits[0].dxf.handle)]
                elif len(hits)in(2,3):targets=[dict(kind='axis_source_corner'if len(hits)==2 else'axis_source_junction',line_handles=[line.dxf.handle for line in hits])]
            if len(targets)!=1:raise ValueError('no_unique_target_in_current_declared_graph_scope')
            spec=dict(text_handle=handle,expected_text=raw,underline_handle=underline[0].dxf.handle,leader_handle=leader.dxf.handle,target=targets[0])
            policy=dict(source_sha256=sh,graph_sha256=gh,text_layers=sorted(text_layers),leader_layers=sorted(leader_layers),selections=[spec])
            native=named_collect(doc,graph,policy,sh,gh)['records'][0];selections.append(spec)
            claimed[handle]=dict(status='source_witnessed',text_handle=handle,raw_text=raw,identifier=native['identifier'],system=native['system'],role=native['target_kind'],
                node_id=native['target'].get('node_id'),floor=native['target'].get('floor'),observed_named_DN_mm=native['nominal_mm_observed'],native_evidence=native)
        except(ValueError,KeyError,TypeError)as exc:pending.append(dict(status='pending',text_handle=handle,raw_text=raw,reason='named_native_source_not_qualified',detail=str(exc)))
    for row in pending:claimed[row['text_handle']]=row
    if set(claimed)!=set(by_text):raise ValueError('complete named-text outcome partition differs')
    policy=dict(source_sha256=sh,graph_sha256=gh,text_layers=sorted(text_layers),leader_layers=sorted(leader_layers),selections=selections)
    named=named_collect(doc,graph,policy,sh,gh)if selections else None
    records=[claimed[h]for h in sorted(claimed)]
    return dict(mode=MODE,family=family,source_sha256=sh,graph_sha256=gh,records=records,named_source_policy=policy,named_source_evidence=named,external_source_groups=groups,provider_issues=provider_issues,
        counts=dict(source_labels=len(texts),source_witnessed=sum(r['status']=='source_witnessed'for r in records),pending=sum(r['status']=='pending'for r in records)),
        topology_owner_stage_reexecuted=False,graph_mutated=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,crossview_mappings_assigned=0,human_accepted=False)

def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name))for name in(Path(__file__).name,'native_named_riser_evidence.py','native_external_pipe_destination.py','native_external_port_destination.py','native_dn_text_position.py','native_line_path_evidence.py','crossview_equipment_branch_inventory.py','source_readability.py')}

def compute(manifest,announce=lambda x:None):
    items=manifest['drawings'];ids=[d['id']for d in items]
    if len(set(ids))!=len(ids)or not items:raise ValueError('unique explicit source drawing scopes required')
    outputs={};inputs={}
    for item in items:
        for spec in(item['source'],item['graph'],*item.get('external_templates',[])):
            if sha(spec['path'])!=spec['sha256']:raise ValueError('native interface batch input changed')
            inputs[str(Path(spec['path']).resolve())]=spec['sha256']
        doc,preflight=read_source(item['source']['path']);templates=[dict(kind=s['kind'],policy=load(s['path']))for s in item.get('external_templates',[])]
        result=discover(doc,load(item['graph']['path']),item['source']['sha256'],item['graph']['sha256'],item['family'],item['text_layers'],item['leader_layers'],templates)
        result['source_preflight']=preflight;outputs[item['id']]=result;announce(item['id']+' '+str(result['counts']))
    if any(sha(p)!=h for p,h in inputs.items()):raise ValueError('native input changed during batch reading')
    counts={k:sum(d['counts'][k]for d in outputs.values())for k in('source_labels','source_witnessed','pending')}
    return dict(mode=MODE,drawings=outputs,counts=counts,inputs=inputs,implementation_sha256=implementation_hashes(),topology_owner_stage_reexecuted=False,graph_mutated=False,whole_edge_DN_assigned=0,physical_lengths_assigned=0,crossview_mappings_assigned=0,human_accepted=False)

def produce(manifest_path,output,announce=lambda x:None):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path),announce);output.mkdir(parents=True);target=output/'named-interface-batch.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),output_sha256=sha(target),implementation_sha256=implementation_hashes(),human_accepted=False)))
    return result
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');target=output/'named-interface-batch.json';manifest=receipt['manifest']
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(manifest['path'])!=manifest['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('native named-interface batch binding changed')
    fresh=compute(load(manifest['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('complete native named-interface batch does not replay exactly')
    return fresh
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification uses bound original inputs')
        result=verify_output(a.verify_output)
    else:
        if not(a.manifest and a.output):p.error('fixed batch manifest and new output required')
        result=produce(a.manifest,a.output,lambda s:print(s,flush=True))
    print(result['counts'],flush=True)
if __name__=='__main__':main()
