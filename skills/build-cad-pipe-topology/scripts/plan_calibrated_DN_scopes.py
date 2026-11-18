"""Use proved native text-side seeds with the established T-scope algorithm."""
import argparse,json
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from calibrated_ownership_scope_composition import verify_ownership_output
from plan_pipe_diameter_scopes import catalog,group_evidence
from calibrated_direct_dn_evidence import collect as calibrated_collect
from source_direct_dn_evidence import collect as strict_collect
from source_checked_plan_path_coverage import audit as audit_paths

MODE='calibrated_plan_DN_scopes'


def verify_topology_parent(path,graph):
    path=Path(path)
    if 'sourceSideviewEquipmentOwnership' in graph or any('source_sideview_equipment_interface' in e for e in graph.get('edges',[])):
        from reconstruct_sideview_equipment_ownership import verify_output
        audit=verify_output(path.parent)
    else:
        audit=verify_ownership_output(path.parent)
    if audit['output_graph_sha256']!=sha(path):raise ValueError('calibrated plan ownership differs')
    return audit


def compute(paths,policy):
    for key in ('source','graph','calibration_policy'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('calibrated plan DN input changed '+key)
    graph=load(paths['graph']);verify_topology_parent(paths['graph'],graph)
    source_hash=sha(paths['source']);graph_hash=sha(paths['graph']);doc,preflight=read_source(paths['source']);calibration=load(paths['calibration_policy'])
    bindings=calibrated_collect(doc,graph,calibration,source_hash,graph_hash)
    allowed={r['text_handle']:r for r in calibration['selections']}
    def direct(doc,current,selection,sh,gh):
        selected=selection['selections']
        if all(s['text_handle'] in allowed for s in selected):
            if any(s!=allowed[s['text_handle']] for s in selected):raise ValueError('calibrated seed differs from explicit native binding')
            return calibrated_collect(doc,current,dict(calibration,selections=selected),sh,gh)
        if any(s['text_handle'] in allowed for s in selected):raise ValueError('mixed direct and calibrated seed call must be separated')
        return strict_collect(doc,current,selection,sh,gh)
    groups=policy.get('groups',[]);ids=[eid for g in groups for eid in g['main_edges']+[b['edge_id'] for b in g['branches']]]
    if not groups or len(ids)!=len(set(ids)) or not policy.get('expert_T_inheritance_rule'):raise ValueError('explicit non-overlapping T/DN scope required')
    texts,annotation_inventory=catalog(doc,graph,ids,source_hash,graph_hash)
    component_labels=None;component_strokes=()
    if policy.get('qualified_component_DN'):
        from qualified_inline_DN_evidence import collect as component_collect
        component_labels=component_collect(doc,graph,policy['qualified_component_DN'],source_hash,graph_hash)
        consumed=set(component_labels['consumed_DN_text_handles']);texts=[t for t in texts if t['handle'] not in consumed];component_strokes=component_labels['consumed_leader_handles']
        annotation_inventory['qualified_component_DN']=component_labels
    results=[group_evidence(doc,graph,g,texts,source_hash,graph_hash,set(annotation_inventory['F_text_handles']),direct_collector=direct,path_auditor=audit_paths,verified_nonpipe_annotation_strokes=component_strokes) for g in groups]
    return dict(status='source_checked_plan_DN_scopes_human_pending',source_sha256=source_hash,graph_sha256=graph_hash,source_preflight=preflight,
        source_annotation_inventory=annotation_inventory,groups=results,records=[r for g in results for r in g['records']],calibrated_direct_binding=bindings,
        local_graph_mutated=False,scope='native_floor_plan_drawn_pipe_paths_only_not_unshown_drops_or_equipment_connectors',expert_rule=policy['expert_T_inheritance_rule'],human_accepted=False)


def implementation_hashes():
    from plan_pipe_diameter_scopes import implementation_hashes as inherited
    result=inherited()
    for name in ('qualified_inline_DN_evidence.py','plan_calibrated_DN_scopes.py','calibrated_direct_dn_evidence.py','source_checked_plan_path_coverage.py','source_reviewed_circle_branch_evidence.py','reconstruct_sideview_equipment_ownership.py','native_sideview_equipment_branch_evidence.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'plan-DN-scope-receipt.json')
    if receipt.get('mode')!=MODE or receipt.get('implementation_sha256')!=implementation_hashes():raise ValueError('calibrated plan DN implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('calibrated plan DN dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'plan-DN-scopes.json').read_bytes() or sha(directory/'plan-DN-scopes.json')!=receipt['output_sha256']:raise ValueError('calibrated plan DN source replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','calibration-policy','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={k:getattr(a,k) for k in ('source','graph','calibration_policy','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'plan-DN-scopes.json').write_bytes(encode(result))
    receipt=dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'plan-DN-scopes.json'),human_accepted=False)
    (a.output/'plan-DN-scope-receipt.json').write_bytes(encode(receipt));print(json.dumps(dict(source_plan_edges=len(result['records']),known_plan_DN=sum(r['nominal_mm'] is not None for r in result['records']),human_accepted=False)))


if __name__=='__main__':main()
