"""Source-calibrated ownership v2: compose prior length scopes, never erase them.

The original native glyph/body/calibration algorithm remains independently
versioned. This entry changes attribute composition, not its matching rule.
"""
import argparse,copy,json,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
import calibrated_equipment_interface_ownership as native

MODE='calibrated_ownership_preserve_source_scopes_v2'
SCOPE_FIELDS=('path_length_scope','physical_length_status','physical_length','drawing_path_length','path_length_complete')


def entry_for_policy(policy):
    if 'preserve_prior_source_scopes' not in policy:return 'calibrated_equipment_interface_ownership.py'
    if policy['preserve_prior_source_scopes'] is not True:raise ValueError('source-scope preservation policy must be true when declared')
    return 'calibrated_ownership_scope_composition.py'


def compose(graph,evidence,model,policy,source_hash,graph_hash):
    out,records,changes=native.apply(graph,evidence,model,policy,source_hash,graph_hash)
    original={e['edge_id']:e for e in graph['edges']};edges={e['edge_id']:e for e in out['edges']};proof=[]
    for record in records:
        eid=record['edge_id'];before=original[eid];edge=edges[eid]
        if before.get('cross_view_attributes') is not None:raise ValueError('local ownership must precede cross-view fusion')
        if before.get('equipment_connector_length_mm') is not None:raise ValueError('existing measured equipment connector requires reconciliation')
        prior={k:copy.deepcopy(before[k]) for k in SCOPE_FIELDS if k in before}
        for key in ('path_length_scope','drawing_path_length'):
            if key in prior:edge[key]=copy.deepcopy(prior[key])
        # A previous unknown status stays explicit. A previous complete pipe
        # scope cannot certify the newly introduced unshown equipment link.
        status=prior.get('physical_length_status')
        if isinstance(status,str) and any(t in status.lower() for t in ('unknown','pending','unverified')):edge['physical_length_status']=status
        edge['path_length_complete']=False
        edge['physical_length']='unknown'
        edge['equipment_connector_length_mm']=None;edge['equipment_connector_length_status']='unshown_interface_to_equipment_unknown'
        lineage=copy.deepcopy(before.get('length_scope_evidence',[]))
        if not isinstance(lineage,list):raise ValueError('unsupported previous length scope lineage')
        lineage.extend([dict(kind='inherited_local_edge_length_scope',source_graph_sha256=graph_hash,edge_id=eid,properties=copy.deepcopy(prior)),
            dict(kind='source_calibrated_logical_ownership_connector',source_graph_sha256=graph_hash,edge_id=eid,equipment_id=record['equipment_id'],physical_length_mm=None,physical_port_verified=False)])
        edge['length_scope_evidence']=lineage
        record['prior_edge_length_scope']=copy.deepcopy(prior)
        record['length_scope_composition']=MODE
        # reconcile() deep-copies edges before the historical root is attached.
        # Keep the root and per-edge evidence identical after augmentation.
        edge['source_layout_equipment_interface']=record
        proof.append(dict(edge_id=eid,prior=prior,current={k:copy.deepcopy(edge.get(k)) for k in SCOPE_FIELDS},new_equipment_connector_length_mm=None))
    root=out['sourceLayoutEquipmentOwnership']
    root.update(scope_composition_mode=MODE,prior_edge_scopes_preserved=True,scope_composition=proof)
    return out,records,changes


def compute(paths,policy):
    if policy.get('preserve_prior_source_scopes') is not True:raise ValueError('explicit source-scope composition policy required')
    graph,model,evidence,proof=native.compute(paths,policy)
    out,records,changes=compose(graph,evidence,model,policy,sha(paths['source']),sha(paths['graph']))
    return out,records,changes,dict(calibration=model,evidence=evidence,**proof)


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('calibrated_ownership_scope_composition.py','calibrated_equipment_interface_ownership.py','edge_endpoint_semantics.py','native_equipment_body.py','source_terminal_pair_inventory.py','cad_ceiling_native_rules.py','source_readability.py')}


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'calibrated-equipment-ownership-audit.json')
    if audit.get('mode')!=MODE or audit.get('implementation_sha256')!=implementation_hashes():raise ValueError('stale source-scope ownership implementation')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('source-scope ownership input changed')
    paths={k:v['path'] for k,v in audit['inputs'].items() if k!='policy'}
    graph,records,changes,proof=compute(paths,load(audit['inputs']['policy']['path']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or audit['records']!=records or audit['endpoint_type_changes']!=changes:raise ValueError('source-scope ownership native replay differs')
    if any(audit.get(k)!=proof[k] for k in ('source_preflight','control_preflight')):raise ValueError('source-scope ownership preflight changed')
    if (directory/'assigned_edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('source-scope ownership component inventory changed')
    return audit


def verify_ownership_output(directory):
    """Dispatch receipts, retaining the immutable earlier algorithm for history."""
    receipt=Path(directory)/'calibrated-equipment-ownership-audit.json'
    mode=load(receipt).get('mode') if receipt.is_file() else None
    if mode==MODE:return verify_output(directory)
    if mode is not None:raise ValueError('unsupported source-layout ownership receipt mode')
    return native.verify_output(directory)


def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','devices','control-source','control-graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths={k:getattr(a,k) for k in ('source','graph','devices','control_source','control_graph')}
    if a.output.exists():raise FileExistsError(a.output)
    graph,records,changes,proof=compute(paths,load(a.policy));a.output.mkdir(parents=True)
    (a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
    (a.output/'source-screen.json').write_bytes(encode(proof));paths['policy']=a.policy
    audit=dict(mode=MODE,source_preflight=proof['source_preflight'],control_preflight=proof['control_preflight'],records=records,endpoint_type_changes=changes,
        parent_graph=dict(path=str(a.graph.resolve()),sha256=sha(a.graph)),inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},
        implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'calibrated-equipment-ownership-audit.json').write_bytes(encode(audit))
    print(json.dumps(dict(equipment=len({r['equipment_id'] for r in records}),logical_service_links=len(records),prior_edge_scopes_preserved=True,human_accepted=False)))


if __name__=='__main__':main()
