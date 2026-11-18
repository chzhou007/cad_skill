"""Exclude source-reviewed circle radii from existing logical branch paths.

No connections, identities, main segmentation or component assignments change.
Original calibrated ownership evidence stays bound to its immutable parent.
"""
import argparse,copy,json,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from source_reviewed_circle_connections import load_review,candidate
from expert_circle_source_lengths import correct_circle_branch_lengths
from native_line_path_evidence import LAYERS
from native_circle_rim_junction_evidence import collect

def snapshot(edge):
    return {k:copy.deepcopy(edge.get(k)) for k in ('start_node_id','end_node_id','system','attribute_paths')}

def apply(doc,graph,policy,source_hash):
    review=load_review(policy,source_hash);selected=policy.get('circle_handles',[])
    if not selected or len(set(selected))!=len(selected) or not set(selected)<=set(review):raise ValueError('invalid circle normalization scope')
    reverse={v:k for k,v in LAYERS.items()}
    segments=[dict(handle=l.dxf.handle,system=reverse[l.dxf.layer],a=(l.dxf.start.x,l.dxf.start.y),b=(l.dxf.end.x,l.dxf.end.y)) for l in doc.modelspace().query('LINE') if l.dxf.layer in reverse]
    out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};records=[]
    for handle in selected:
        row=review[handle];c=doc.entitydb.get(handle)
        if c is None or c.dxftype()!='CIRCLE':raise ValueError('normalization circle missing')
        main,(branch,_,rim)=candidate(doc,dict(handle=handle,system=reverse.get(c.dxf.layer),center=(c.dxf.center.x,c.dxf.center.y),radius=c.dxf.radius),segments,review,graph=out)
        chosen=[e for e in out['edges'] if branch['handle'] in e.get('source_handles',[]) and e.get('system')==row['system']]
        if len(chosen)!=1:raise ValueError('circle branch graph owner ambiguous')
        edge=chosen[0]
        if edge.get('source_circle_connection') or 'cross_view_attributes' in edge or edge.get('source_circle_path_normalization'):raise ValueError('circle path already normalized or attributes need invalidation first')
        tees=[nodes[nid] for nid in (edge.get('start_node_id'),edge.get('end_node_id')) if nid in nodes and nodes[nid].get('node_type') in ('tee','physical_junction')]
        if len(tees)!=1:raise ValueError('existing circle branch must have one T')
        node=tees[0];before=snapshot(edge)
        proof=dict(source_sha256=source_hash,review_kind='technical_native_source_comparison',review_manifest=policy['review_manifest'],review_sha256=policy['review_sha256'],pair_sha256=row['pair_sha256'],human_accepted=False)
        bridge=dict(system=row['system'],circle_handle=handle,main_handle=main['handle'],branch_handle=branch['handle'],semantic_endpoint=(c.dxf.center.x,c.dxf.center.y),original_endpoint=rim,source_comparison=proof)
        correction=correct_circle_branch_lengths(out['nodes'],out['edges'],[bridge])
        edge['drawing_path_length']=edge['path_length'];edge['physical_length']='unknown';edge['physical_length_status']='unknown_circle_connector_and_equipment_connection'
        after=snapshot(edge)
        record=dict(edge_id=edge['edge_id'],node_id=node['node_id'],circle_handle=handle,branch_handle=branch['handle'],input_snapshot=before,output_snapshot=after,
            correction=correction[0],source_sha256=source_hash,human_accepted=False,physical_connector_length=None)
        edge['source_circle_path_normalization']=copy.deepcopy(record);records.append(record)
        collect(doc,out,node['node_id'],source_hash,'read_only_current_normalized_projection')
    out['sourceCirclePathNormalization']=dict(status='native_circle_radius_excluded_local_topology_unchanged',source_sha256=source_hash,records=records,
        logical_connections_changed=False,component_assignments_changed=False,human_accepted=False)
    out['derivedEvidenceInvalidation']=dict(previous_invalidation=copy.deepcopy(graph.get('derivedEvidenceInvalidation')),
        reason='native circle drafting radius excluded from source path; selected local IDs and logical connectivity unchanged',
        recompute=['source_path_checks','crossview_mapping','diameter_scope','length_fusion','human_acceptance'],historical_annotations_preserved=True)
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_circle_source_path_normalization')
    return out,records

def implementation_hashes():
    return {n:sha(Path(__file__).with_name(n)) for n in ('normalize_plan_circle_paths.py','native_circle_rim_junction_evidence.py','source_reviewed_circle_connections.py','expert_circle_source_lengths.py','cad_ceiling_native_rules.py')}

def compute(paths,policy):
    for key in ('source','graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('circle normalization input changed '+key)
    from calibrated_equipment_interface_ownership import verify_output as verify_parent
    parent=verify_parent(Path(paths['graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('circle normalization ownership parent differs')
    doc,preflight=read_source(paths['source']);out,records=apply(doc,load(paths['graph']),policy,sha(paths['source']))
    return out,dict(records=records,source_preflight=preflight,parent_graph=dict(path=str(Path(paths['graph']).resolve()),sha256=sha(paths['graph'])))

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'circle-path-normalization-audit.json')
    if audit['implementation_sha256']!=implementation_hashes():raise ValueError('stale circle path normalization implementation')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('circle normalization dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};out,proof=compute(paths,load(paths['policy']))
    if encode(out)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or proof['records']!=audit['records']:raise ValueError('circle path replay differs')
    if (directory/'assigned_edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('circle normalization components changed')
    return audit

def main():
    p=argparse.ArgumentParser()
    for k in ('source','graph','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
    args=p.parse_args();paths={k:getattr(args,k) for k in ('source','graph','devices','policy')}
    if args.output.exists():raise FileExistsError(args.output)
    out,audit=compute(paths,load(args.policy));args.output.mkdir(parents=True)
    (args.output/'graph_with_edges.json').write_bytes(encode(out));shutil.copyfile(args.devices,args.output/'assigned_edge_device_instances.csv')
    audit.update(inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(args.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (args.output/'circle-path-normalization-audit.json').write_bytes(encode(audit));print(json.dumps(dict(normalized=len(audit['records']),logical_topology_changed=False,human_accepted=False)))

if __name__=='__main__':main()
