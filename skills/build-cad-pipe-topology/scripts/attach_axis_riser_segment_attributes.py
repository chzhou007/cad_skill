"""Add checked axis DN segment domains without overwriting floor-plan values.

The full parent and native riser scope are independently replayed. No local
topology, mixed-edge diameter, physical length or HIL acceptance is changed.
"""
import argparse,copy,math,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from compose_refined_paired_plan_attributes import verify_output as verify_parent,implementation_hashes as parent_hashes
from native_axis_riser_DN_scopes import verify_output as verify_scopes,implementation_hashes as scope_hashes,MODE as SCOPE_MODE

MODE='axis_riser_segment_attribute_extension_v1'
ROOT='sourceAxisRiserSegmentAttributes'


def append(parent,local,scope,scope_hash,parent_hash):
    if ROOT in parent or any('axis_riser_attributes' in e for e in parent['edges']):raise ValueError('axis riser segment attributes already present')
    if (scope.get('mode')!=SCOPE_MODE or scope.get('status')!='source_checked_axis_through_riser_segment_DN_human_pending'
        or any(scope.get(k) is not False for k in ('local_graph_mutated','physical_values_fused','floor_interface_correspondence_confirmed','human_accepted'))
        or scope.get('installed_lengths_assigned')!=0 or scope.get('whole_edge_DN_assigned')!=0):raise ValueError('unsupported source riser scope state')
    by={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']};nodes={n['node_id']:n for n in parent['nodes']}
    if len(by)!=len(parent['edges']) or len(raw)!=len(local['edges']) or len(nodes)!=len(parent['nodes']):raise ValueError('duplicate segment parent identity')
    if parent['nodes']!=local['nodes'] or by.keys()!=raw.keys() or parent['metadata'].get('source_sha256')!=scope['source_sha256']:raise ValueError('riser local topology differs from attribute parent')
    selected=scope['records'];seen=set();output=copy.deepcopy(parent);target={e['edge_id']:e for e in output['edges']};records=[]
    for row in selected:
        eid=row['edge_id'];si=row['segment_index'];edge=by.get(eid);key=(eid,si)
        if (key in seen or not edge or not isinstance(si,int) or isinstance(si,bool) or edge['system']!=row['system']
            or row.get('scope')!='native_axis_through_riser_drawn_vertical_segment_only' or row.get('whole_local_edge_DN_assigned') is not False
            or row.get('physical_length_mm') is not None or row.get('human_accepted') is not False):raise ValueError('invalid or repeated riser segment scope')
        seen.add(key)
        if {k:v for k,v in edge.items() if k!='cross_view_attributes'}!=raw[eid]:raise ValueError('selected riser local edge changed before attachment')
        paths=edge.get('attribute_paths',[])
        if len(paths)!=1 or not 0<=si<len(paths[0])-1 or row['scope_paths']!=[paths[0][si:si+2]]:raise ValueError('riser scope endpoints do not match exact current segment')
        nominal=row['nominal_mm']
        if isinstance(nominal,bool) or not isinstance(nominal,(int,float)) or not math.isfinite(nominal) or nominal<=0:raise ValueError('riser nominal DN must be positive and known')
        if row['status'] not in ('direct_axis_segment_DN','T_inherited_axis_segment_DN'):raise ValueError('unresolved segment DN cannot be attached as checked')
        if not row.get('lineage') or any(c.get('nominal_mm')!=nominal or not c.get('evidence') or any(not e.get('evidence_id','').startswith('source:')
            or not e.get('edge_path') or e['edge_path'][-1]!=row['projection_edge_id'] for e in c['evidence']) for c in row['lineage']):raise ValueError('riser DN lineage does not reach declared segment')
        spans=[s for c in scope['through_contracts'] if c['system']==edge['system'] for s in c['segments'] if s['edge_id']==eid and s['segment_index']==si]
        if len(spans)!=1 or spans[0]['source_line_handle']!=row['source_line_handle'] or spans[0]['scope_points']!=row['scope_paths'][0]:raise ValueError('riser native through contract differs')
        if spans[0]['floor_pair']!=sorted(nodes[edge[k]]['floor'] for k in ('start_node_id','end_node_id')):raise ValueError('riser floor span differs from local endpoints')
        item=dict(edge_id=eid,path_index=0,segment_index=si,system=edge['system'],scope_points=copy.deepcopy(row['scope_paths'][0]),
            floor_pair=spans[0]['floor_pair'],nominal_mm=nominal,status=row['status'],lineage=copy.deepcopy(row['lineage']),
            source_line_handle=row['source_line_handle'],source_scope_sha256=scope_hash,source_sha256=scope['source_sha256'],
            local_graph_sha256=scope['graph_sha256'],attribute_parent_graph_sha256=parent_hash,
            scope='native_axis_vertical_segment_DN_only',horizontal_values_source='floor_plan_correspondence',
            whole_edge_nominal_mm=None,physical_length_mm=None,whole_edge_physical_length_mm=None,human_accepted=False)
        target[eid].setdefault('axis_riser_attributes',[]).append(item);records.append(item)
    if not records:raise ValueError('empty riser attribute scope')
    output[ROOT]=dict(status='source_checked_axis_segment_DN_hil_pending',records=records,source_scope_sha256=scope_hash,
        source_sha256=scope['source_sha256'],local_graph_sha256=scope['graph_sha256'],attribute_parent_graph_sha256=parent_hash,
        local_topology_and_all_plan_attributes_preserved=True,whole_edge_DN_assigned=0,installed_lengths_assigned=0,human_accepted=False)
    output['metadata'].update(graph_complete=False,hil_ready=False,review_status='unreviewed_after_axis_segment_DN_attribute_extension')
    return output,dict(added_segment_attributes=len(records),affected_axis_edges=sorted({r['edge_id'] for r in records}),
        all_prior_plan_attributes_preserved=True,local_topology_and_components_preserved=True,
        whole_edge_DN_assigned=0,installed_lengths_assigned=0,related_prior_HIL_confirmation_inherited=False)


def compute(paths,policy):
    for key in ('parent_graph','riser_scope','riser_receipt','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('axis riser attachment input changed '+key)
    directory=Path(paths['riser_scope']).resolve().parent
    if Path(paths['riser_scope']).resolve()!=directory/'axis-riser-DN-scopes.json' or Path(paths['riser_receipt']).resolve()!=directory/'axis-riser-DN-scope-receipt.json':raise ValueError('noncanonical native riser scope input')
    scope=verify_scopes(directory)
    parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):raise ValueError('verified parent or canonical component inventory differs')
    sr=load(paths['riser_receipt']);segment_receipt=load(sr['inputs']['segment_receipt']['path']);localpath=Path(segment_receipt['inputs']['graph']['path'])
    if sha(localpath)!=scope['graph_sha256']:raise ValueError('native riser local graph changed')
    graph,proof=append(load(paths['parent_graph']),load(localpath),scope,sha(paths['riser_scope']),sha(paths['parent_graph']))
    base=Path(parent['parent_graph']['path']);base_audit=base.parent/'source-attribute-fusion-audit.json'
    ba=load(base_audit)
    if ba['output_graph_sha256']!=sha(base) or ba['parent_graph']!=parent['common_parent_graph']:raise ValueError('freshly replayed parent ancestry differs')
    return graph,dict(proof,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        native_local_graph=dict(path=str(localpath.resolve()),sha256=sha(localpath)),source_sha256=scope['source_sha256'],
        source_scope_sha256=sha(paths['riser_scope']),verified_parent_composition=parent,
        verified_parent_base_attribute_audit=dict(path=str(base_audit.resolve()),sha256=sha(base_audit)),records=graph[ROOT]['records'])


def viewer_ancestry(audit,graph_hash):
    """Reuse only the exact parent audit just reproduced by this verifier."""
    parent=audit['verified_parent_composition'];binding=audit['verified_parent_base_attribute_audit'];path=Path(binding['path'])
    if sha(path)!=binding['sha256']:raise ValueError('verified parent attribute context changed')
    result=copy.deepcopy(load(path));base=Path(parent['parent_graph']['path'])
    if result['output_graph_sha256']!=sha(base) or result['parent_graph']!=parent['common_parent_graph']:raise ValueError('axis segment parent ancestry differs')
    result['records']+=parent['records'];result['plan_DN_scope_fusion']+=parent['plan_DN_scope_fusion']
    result.update(output_graph_sha256=graph_hash,refined_paired_attribute_composition_audit=parent,refined_base_attribute_audit_path=str(path),
        axis_riser_segment_attribute_audit=audit,axis_riser_refined_parent_graph_path=audit['parent_graph']['path'],human_accepted=False,hil_ready=False)
    ancestor=Path(result['parent_graph']['path'])
    if sha(ancestor)!=result['parent_graph']['sha256']:raise ValueError('axis segment common ancestor changed')
    return ancestor,result


def implementation_hashes():
    hashes=parent_hashes();hashes.update(scope_hashes());hashes['attach_axis_riser_segment_attributes.py']=sha(__file__);return hashes


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'axis-riser-attribute-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('axis riser attribute implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('axis riser attribute dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):raise ValueError('axis riser attachment native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('axis riser attribute components changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-graph','riser-run','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_graph=a.parent_graph,riser_scope=a.riser_run/'axis-riser-DN-scopes.json',riser_receipt=a.riser_run/'axis-riser-DN-scope-receipt.json',devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'axis-riser-attribute-audit.json').write_bytes(encode(audit));print(dict(segments=audit['added_segment_attributes'],whole_edge_DN_assigned=0,installed_lengths_assigned=0),flush=True)


if __name__=='__main__':main()
