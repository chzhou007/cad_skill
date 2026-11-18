"""Compose independently replayed floor scopes on one unchanged axis parent.

This does not infer correspondence or copy an old graph onto a new topology.
Every child must be re-created on the identical parent and component version.
"""
import argparse,copy,json,re,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode

MODE='composed_source_checked_plan_scopes'


def compose(parent,scopes,manifest_hash):
    if len(scopes)<2 or not re.fullmatch('[0-9a-f]{64}',manifest_hash):raise ValueError('multiple explicit verified plan scopes required')
    if parent.get('sourceCheckedCrossViewAttributeFusion'):raise ValueError('compose from the common confirmed-attribute parent')
    out=copy.deepcopy(parent);base={e['edge_id']:e for e in parent['edges']};dest={e['edge_id']:e for e in out['edges']}
    if len(base)!=len(parent['edges']):raise ValueError('duplicate axis edge identity')
    claimed=set();scope_ids=set();records=[];dn=[];scope_proofs=[]
    for item in scopes:
        scope_id=item['scope_id'];child=item['graph'];audit=item['audit']
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_-]*',scope_id) or scope_id in scope_ids:raise ValueError('duplicate or invalid source scope identity')
        scope_ids.add(scope_id);root=child.get('sourceCheckedCrossViewAttributeFusion',{})
        if root.get('human_accepted') is not False or root.get('expert_confirmation_claimed') is not False or child.get('metadata',{}).get('hil_ready') is not False:raise ValueError('technical scope cannot inherit human acceptance')
        edges={e['edge_id']:e for e in child['edges']}
        if child['nodes']!=parent['nodes'] or edges.keys()!=base.keys() or len(edges)!=len(child['edges']):raise ValueError('plan scopes use different axis nodes/edges')
        for key in set(parent)|set(child):
            if key not in ('metadata','sourceCheckedCrossViewAttributeFusion','edges') and child.get(key)!=parent.get(key):raise ValueError('source scope changed common local evidence '+key)
        rows=root.get('records',[])
        if rows!=audit.get('records') or len({r['mapping_id'] for r in rows})!=len(rows):raise ValueError('source scope record/audit mismatch')
        owners={}
        for row in rows:
            for eid in row['iso_edges']:
                if eid in owners:raise ValueError('source scope repeats an axis owner')
                owners[eid]=row
        changed=[]
        for eid,edge in edges.items():
            before=base[eid]
            if edge==before:continue
            if eid not in owners or eid in claimed or 'cross_view_attributes' in before:raise ValueError('source scopes overlap or change an unrecorded edge')
            original={k:v for k,v in edge.items() if k!='cross_view_attributes'}
            if original!=before:raise ValueError('source scope changed local geometry/component ownership')
            attr=edge.get('cross_view_attributes',{});row=owners[eid]
            if (attr.get('mapping_basis')!='native_source_and_main_branch_order' or attr.get('mapping_id')!=row['mapping_id']
                or attr.get('plan_edges')!=row['plan_edges'] or attr.get('iso_edges')!=row['iso_edges'] or attr.get('system')!=before.get('system')
                or attr.get('human_accepted') is not False or attr.get('physical_ports_verified') is not False):raise ValueError('source scope attribute/record binding differs')
            dest[eid]['cross_view_attributes']=copy.deepcopy(attr)
            dest[eid]['cross_view_attributes'].update(mapping_id=scope_id+'-'+row['mapping_id'],source_scope_id=scope_id,source_scope_mapping_id=row['mapping_id'])
            changed.append(eid);claimed.add(eid)
        if set(changed)!=set(owners):raise ValueError('source scope records do not exactly cover its new attributes')
        records.extend([dict(copy.deepcopy(r),mapping_id=scope_id+'-'+r['mapping_id'],source_scope_id=scope_id,source_scope_mapping_id=r['mapping_id']) for r in rows])
        dn.extend([dict(copy.deepcopy(r),mapping_id=scope_id+'-'+r['mapping_id'],source_scope_id=scope_id,source_scope_mapping_id=r['mapping_id']) for r in audit.get('plan_DN_scope_fusion',[])])
        scope_proofs.append(dict(scope_id=scope_id,attribute_run=item['attribute_run'],attribute_graph_sha256=item['attribute_graph_sha256'],attribute_receipt_sha256=item['attribute_receipt_sha256'],axis_edges=changed,
            original_root=copy.deepcopy(root),source_preflight=copy.deepcopy(audit.get('source_preflight')),human_accepted=False))
    out['sourceCheckedCrossViewAttributeFusion']=dict(status='source_checked_multifloor_plan_attributes_hil_pending',mapping_sha256=manifest_hash,records=records,
        plan_scopes=scope_proofs,prior_attributes_preserved=True,expert_confirmation_claimed=False,physical_ports_verified=False,human_accepted=False,
        whole_main_centerline_route_edges=[r['iso_edge'] for r in dn if r['whole_main_DN_and_centerline_route']])
    out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_multifloor_plan_scope_composition')
    proof=dict(records=records,plan_scopes=scope_proofs)
    if dn:proof['plan_DN_scope_fusion']=dn
    return out,proof


def compute(paths,policy):
    from attach_source_checked_plan_attributes import verify_output as verify_child
    from attach_crossview_plan_attributes import verify_output as verify_parent
    for key in ('manifest','parent_graph','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('source scope composition input changed '+key)
    parent=Path(paths['parent_graph']).resolve();parent_audit=verify_parent(parent.parent)
    if parent_audit['output_graph_sha256']!=sha(parent) or parent_audit['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('source scope common parent/inventory differs')
    specs=load(paths['manifest'])['scopes'];scopes=[];runs=set()
    for spec in specs:
        run=Path(spec['attribute_run']).resolve()
        if run in runs:raise ValueError('duplicate attribute scope run')
        runs.add(run);gp=run/'graph_with_edges.json';ap=run/'source-attribute-fusion-audit.json'
        if sha(gp)!=spec['attribute_graph_sha256'] or sha(ap)!=spec['attribute_receipt_sha256']:raise ValueError('source attribute scope dependency changed')
        audit=verify_child(run)
        if audit.get('parent_graph')!=dict(path=str(parent),sha256=sha(parent)) or audit['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('source scopes were not built on identical current axis parent/components')
        scopes.append(dict(spec,graph=load(gp),audit=audit))
    graph,proof=compose(load(parent),scopes,sha(paths['manifest']))
    return graph,dict(proof,parent_graph=dict(path=str(parent),sha256=sha(parent)))


def implementation_hashes():
    return {name:sha(Path(__file__).with_name(name)) for name in ('compose_source_checked_plan_scopes.py','attach_source_checked_plan_attributes.py','attach_source_checked_plan_attribute_groups.py')}


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'source-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit.get('implementation_sha256')!=implementation_hashes():raise ValueError('source scope composition implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('source scope composition dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('source scope composition replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('source scope canonical component CSV changed')
    return audit


def verify_attribute_output(directory):
    receipt=Path(directory)/'source-attribute-fusion-audit.json'
    if receipt.is_file() and load(receipt).get('mode')==MODE:return verify_output(directory)
    from attach_source_checked_plan_attributes import verify_output as previous
    return previous(directory)


def main():
    p=argparse.ArgumentParser()
    for key in ('manifest','parent-graph','devices','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();paths={k:getattr(a,k) for k in ('manifest','parent_graph','devices','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True)
    (a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'source-attribute-fusion-audit.json').write_bytes(encode(audit));print(json.dumps(dict(plan_scopes=len(audit['plan_scopes']),technical_paths=len(audit['records']),axis_edges_with_plan_attributes=sum('cross_view_attributes' in e for e in graph['edges']),human_accepted=False)))


if __name__=='__main__':main()
