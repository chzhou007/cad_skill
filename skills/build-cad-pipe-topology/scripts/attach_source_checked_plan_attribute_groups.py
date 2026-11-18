"""Compose disjoint source-checked mapping groups on one immutable axis parent."""
import argparse,copy,json,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from match_source_checked_crossview_paths import verify_output as verify_mapping
from attach_crossview_plan_attributes import verify_output as verify_parent
from attach_source_checked_plan_attributes import attach,native_local_diameters,metric_context
from native_plan_projection_lengths import unit_evidence
from source_checked_plan_path_coverage import audit as audit_paths
from source_readability import read_source

MODE='batch_source_checked_mapping_groups'

def combine(mappings):
    if len(mappings)<2:raise ValueError('multiple mapping groups required')
    base=mappings[0];records=[];claimed={v:set() for v in ('plan','iso')};ids=set()
    for index,mapping in enumerate(mappings,1):
        if any(mapping.get(k)!=base.get(k) for k in ('plan_graph_sha256','iso_graph_sha256','source_sha256','floor')):raise ValueError('mapping groups use different local drawings or floors')
        if mapping.get('human_accepted') is not False or mapping.get('expert_confirmation_claimed') is not False:raise ValueError('technical groups cannot claim expert acceptance')
        for r in mapping['records']:
            if r['mapping_id'] in ids:raise ValueError('duplicate mapping ID within group')
            ids.add(r['mapping_id']);row=copy.deepcopy(r);row['mapping_id']=f'G{index:02d}-'+r['mapping_id']
            row.update(source_group_index=index,source_group_mapping_id=r['mapping_id'])
            for view in claimed:
                eids=r[view+'_edges']
                if len(eids)!=len(set(eids)) or claimed[view].intersection(eids):raise ValueError('mapping groups overlap '+view)
                claimed[view].update(eids)
            records.append(row)
        ids.clear()
    return dict(base,records=records)

def compute(paths,policy):
    for key in ('groups_manifest','parent_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('batch source attribute input changed '+key)
    specs=load(paths['groups_manifest'])['groups'];runs=[Path(s['mapping_run']).resolve() for s in specs]
    if len(runs)!=len(set(runs)):raise ValueError('duplicate mapping run')
    mappings=[];receipts=[]
    for run,spec in zip(runs,specs):
        if sha(run/'mapping.json')!=spec['mapping_sha256'] or sha(run/'source-mapping-receipt.json')!=spec['receipt_sha256']:raise ValueError('mapping group dependency changed')
        mappings.append(verify_mapping(run));receipts.append(load(run/'source-mapping-receipt.json'))
    mapping=combine(mappings);parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['parent_graph']['sha256']!=mapping['iso_graph_sha256'] or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('batch parent has different local axis or inventory')
    inputs=receipts[0]['inputs'];plan=load(inputs['plan_graph']['path']);doc,preflight=read_source(inputs['plan_source']['path'])
    ids=[eid for r in mapping['records'] for eid in r['plan_edges']]
    coverage=audit_paths(doc,plan,dict(source_sha256=mapping['source_sha256']['plan'],graph_sha256=mapping['plan_graph_sha256'],edges=ids),mapping['source_sha256']['plan'],mapping['plan_graph_sha256'])
    units,allow_detail=metric_context(doc,policy,plan,mapping);diameters={r['mapping_id']:native_local_diameters(doc,plan,r,coverage) for r in mapping['records']}
    sources=dict(plan=mapping['source_sha256']['plan'],isometric=mapping['source_sha256']['iso'],plan_graph=mapping['plan_graph_sha256'],local_iso_graph=mapping['iso_graph_sha256'])
    graph,records=attach(load(paths['parent_graph']),mapping,plan,coverage,units,diameters,sources,sha(paths['groups_manifest']),allow_detail=allow_detail)
    diameter_proof=None
    if policy.get('diameter_evidence_sha256') or paths.get('diameter_evidence'):
        for key in ('diameter_evidence','diameter_receipt'):
            if key not in paths or sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('missing/stale plan DN evidence '+key)
        from plan_pipe_diameter_scopes import verify_output as verify_diameters
        from fuse_plan_DN_scopes import apply as fuse_DN
        directory=Path(paths['diameter_evidence']).resolve().parent
        if Path(paths['diameter_evidence']).resolve()!=directory/'plan-DN-scopes.json' or Path(paths['diameter_receipt']).resolve()!=directory/'plan-DN-scope-receipt.json':raise ValueError('DN scope paths outside canonical stage')
        evidence=verify_diameters(directory)
        if evidence['graph_sha256']!=mapping['plan_graph_sha256'] or evidence['source_sha256']!=mapping['source_sha256']['plan'] or evidence['local_graph_mutated'] is not False or evidence['human_accepted'] is not False:raise ValueError('plan DN scope belongs to different source topology')
        graph,diameter_proof=fuse_DN(graph,mapping,plan,evidence,sha(paths['diameter_evidence']),policy.get('isometric_horizontal_directions_degrees',[]))
    provenance=[dict(group_id=f'G{i:02d}',mapping_run=str(run),mapping_sha256=spec['mapping_sha256'],receipt_sha256=spec['receipt_sha256']) for i,(run,spec) in enumerate(zip(runs,specs),1)]
    graph['sourceCheckedCrossViewAttributeFusion']['mapping_groups']=provenance
    audit=dict(records=records,source_preflight=preflight,metric_evidence=units,mapping_groups=provenance,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])))
    if diameter_proof is not None:audit['plan_DN_scope_fusion']=diameter_proof
    return graph,audit

def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('confirmed_detail_projection.py','attach_source_checked_plan_attribute_groups.py','attach_source_checked_plan_attributes.py','match_source_checked_crossview_paths.py','native_plan_projection_lengths.py','native_path_coverage_audit.py','source_checked_plan_path_coverage.py','source_reviewed_circle_branch_evidence.py','plan_pipe_diameter_scopes.py','native_line_f_diameter_evidence.py','fuse_plan_DN_scopes.py')}

def verify_output(directory):
    directory=Path(directory);audit=load(directory/'source-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('batch source attribute implementation differs')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('batch source attribute dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit[k]!=v for k,v in proof.items()):raise ValueError('batch source attribute replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('batch canonical component inventory changed')
    return audit

def main():
    parser=argparse.ArgumentParser()
    for key in ('groups-manifest','parent-graph','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--diameter-run',type=Path)
    args=parser.parse_args();paths={k:getattr(args,k) for k in ('groups_manifest','parent_graph','devices','policy')}
    if args.diameter_run:paths.update(diameter_evidence=args.diameter_run/'plan-DN-scopes.json',diameter_receipt=args.diameter_run/'plan-DN-scope-receipt.json')
    if args.output.exists():raise FileExistsError(args.output)
    graph,audit=compute(paths,load(args.policy));args.output.mkdir(parents=True)
    (args.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(args.devices,args.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(args.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (args.output/'source-attribute-fusion-audit.json').write_bytes(encode(audit));print(json.dumps(dict(groups=len(audit['mapping_groups']),mapped_paths=len(audit['records']),axis_projection_edges=sum(bool(e.get('cross_view_attributes')) for e in graph['edges']),human_accepted=False)))

if __name__=='__main__':main()
