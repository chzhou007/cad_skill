"""Resolve native name targets to source-checked through-riser columns.

A leader may land directly on the column LINE or on an inherited vent display
leg. Both paths require fresh source geometry; neither creates a cross-view
mapping, a horizontal DN, a physical port or a measured length.
"""
import argparse, copy, dataclasses, math
from pathlib import Path
from confirm_crossview_paths import load, sha, encode
from source_readability import read_source
from batch_native_named_interfaces import verify_output as verify_names
from match_named_riser_floor_paths import vent_normalization
from native_axis_riser_DN_scopes import project
from native_path_coverage_audit import audit
from native_line_path_evidence import collect as collect_lines, _on, LAYERS
from crossview_equipment_branch_inventory import index_graph

MODE='native_named_axis_column_context_v1'

def resolve(doc, graph, contracts, names, removed, sh, gh):
    if names['family']!='axis' or names['source_sha256']!=sh or names['graph_sha256']!=gh:
        raise ValueError('current native axis names and graph required')
    _,edges,_=index_graph(graph); records=[]; ignored=[]
    for row in names['records']:
        if row.get('status')!='source_witnessed':
            records.append(dict(text_handle=row['text_handle'],status='pending',reason='native source label is not qualified',native_source_outcome=copy.deepcopy(row),crossview_mapping_confirmed=False,whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False));continue
        if not row.get('role','').startswith('axis_source_'):
            ignored.append(dict(text_handle=row['text_handle'],role=row.get('role'),reason='not_a_qualified_local_axis_pipe_name'));continue
        base=dict(text_handle=row['text_handle'],identifier=row['identifier'],system=row['system'],native_name=copy.deepcopy(row['native_evidence']))
        try:
            native=row['native_evidence']; tip=native['leader']['target_point']; system=row['system']; hits=[]
            # Exact native LINE identity is an alternative to a display leg,
            # not a synthetic zero-length display leg or nearest-pipe snap.
            if row['role']=='axis_source_line':
                handle=native['target']['source_line_handle']; line=doc.entitydb.get(handle)
                if line is None or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[system] or not _on(tip[:2],list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05):
                    raise ValueError('native direct target LINE or service differs')
                hits=[(c,'exact_native_target_LINE_is_checked_through_column',None)for c in contracts
                    if c['system']==system and c['through_source_LINE']==handle]
            if not hits:
                legs=[r for r in removed if r.system==system and _on(tip[:2],list(r.vent_port),list(r.junction),.05)]
                if len(legs)!=1:raise ValueError('no unique native direct column LINE or inherited display leg')
                leg=legs[0]
                for contract in contracts:
                    if contract['system']!=system:continue
                    upper=[s for s in contract['segments']if s['side']=='upper']
                    if len(upper)!=1:raise ValueError('checked upper column segment is ambiguous')
                    edge=edges[upper[0]['edge_id']]
                    if sum(math.dist(p,list(leg.junction))<=.05 for path in edge['attribute_paths']for p in path[1:-1])==1:
                        line=doc.entitydb.get(contract['through_source_LINE'])
                        if line is None or line.dxftype()!='LINE' or line.dxf.layer!=LAYERS[system] or not _on(list(leg.junction),list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05):
                            raise ValueError('display-leg junction lacks original column LINE')
                        hits.append((contract,'inherited_native_display_leg_and_checked_through_column',dataclasses.asdict(leg)))
            if len(hits)!=1:raise ValueError('native target selects multiple or no checked columns')
            contract,basis,leg=hits[0]
            if contract['corridor_id']!=row['identifier']:raise ValueError('native name conflicts with independently selected column identity')
            records.append(dict(base,status='source_checked_native_column_context',basis=basis,middle_T=contract['middle_T'],
                through_source_LINE=contract['through_source_LINE'],native_through_contract=copy.deepcopy(contract),inherited_display_leg=leg,
                graph_mutated=False,crossview_mapping_confirmed=False,whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
        except(ValueError,KeyError,TypeError)as exc:
            records.append(dict(base,status='pending',reason=str(exc),crossview_mapping_confirmed=False,whole_edge_DN_assigned=False,physical_length_mm=None,human_accepted=False))
    # Competing names for one column must not produce two accepted identities.
    accepted=[r for r in records if r['status']=='source_checked_native_column_context']
    for row in accepted:
        if sum(r['middle_T']==row['middle_T']or r['identifier']==row['identifier']for r in accepted)!=1:
            row.update(status='pending',reason='competing native column identities')
    return dict(records=records,ignored_roles=ignored,counts=dict(local_axis_names=len(records),source_checked=sum(r['status']=='source_checked_native_column_context'for r in records),pending=sum(r['status']=='pending'for r in records),other_roles=len(ignored)),
        graph_mutated=False,crossview_mappings_assigned=0,whole_edge_DN_assigned=0,physical_lengths_assigned=0,human_accepted=False)

def implementation_hashes():
    from batch_native_named_interfaces import implementation_hashes as names
    from match_named_riser_floor_paths import implementation_hashes as risers
    result=names();result.update(risers())
    for name in (Path(__file__).name,'native_path_coverage_audit.py','native_line_path_evidence.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result

def compute(manifest):
    for spec in manifest.values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('native column input changed')
    batch=verify_names(Path(manifest['named_batch']['path']).parent); names=batch['drawings'][manifest['axis']['drawing_id']]
    axis=manifest['axis'];graph=load(axis['path']);source=manifest['source'];doc,preflight=read_source(source['path']);sh=source['sha256'];gh=axis['sha256']
    if graph.get('metadata',{}).get('source_sha256')!=sh:raise ValueError('axis graph source differs')
    policy=load(manifest['column_policy']['path']);corridors=policy['corridors'];selected=[c[k]['edge_id']for c in corridors for k in ('lower','upper')]
    cover=audit(doc,graph,dict(source_sha256=sh,graph_sha256=gh,edges=selected),sh,gh);choices=[]
    for edge in cover['edges']:
        if any(s['status']!='single_source_line_covers'or s['witnesses'][0]['scope']!='modelspace'for s in edge['segments']):
            raise ValueError('current column paths lack unique native modelspace LINE coverage')
        choices.append(dict(edge_id=edge['edge_id'],line_handles=[s['witnesses'][0]['source_handle']for s in edge['segments']]))
    evidence=collect_lines(doc,graph,dict(source_sha256=sh,graph_sha256=gh,selections=choices),sh,gh)
    _,_,_,contracts,_,_=project(doc,graph,evidence,corridors,sh,gh)
    result=resolve(doc,graph,contracts,names,vent_normalization(doc),sh,gh)
    result.update(mode=MODE,source_sha256=sh,graph_sha256=gh,source_preflight=preflight,native_current_column_path_evidence=evidence,
        topology_owner_stage_reexecuted=False,source_geometry_replayed=True)
    if any(sha(spec['path'])!=spec['sha256']for spec in manifest.values()):raise ValueError('input changed during column replay')
    return result

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'named-axis-columns.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'named-axis-columns.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('named column dependencies changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('native named column replay differs')
    return fresh

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification uses exact original inputs')
        result=verify_output(a.verify_output)
    else:
        if not(a.manifest and a.output):p.error('manifest and new output required')
        result=produce(a.manifest,a.output)
    print(result['counts'],flush=True)
if __name__=='__main__':main()
