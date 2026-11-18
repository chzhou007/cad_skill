"""Compose checked named floor approaches over the complete axis parent.

Reuses the existing projection and DN fusion kernels. Existing floor-plan and
vertical segment attributes remain exact; no RIF radius or physical port is
invented. This stage does not publish or accept a drawing.
"""
import argparse,copy,shutil
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from named_riser_plan_attributes import MODE as SCOPE_MODE,verify_output as verify_scopes,implementation_hashes as scope_hashes
from attach_axis_riser_segment_attributes import verify_output as verify_parent,implementation_hashes as parent_hashes
from attach_source_checked_plan_attributes import attach,native_local_diameters
from match_source_checked_crossview_paths import selected_snapshot
from fuse_plan_DN_scopes import apply as fuse_DN
from source_readability import read_source

MODE='named_riser_floor_plan_attribute_extension_v1'
ROOT='sourceNamedRiserPlanAttributeFusion'
BASIS='native_named_riser_and_independent_equipment_service'


def append(parent,local,plan,mapping,scope,coverage,units,diameters,scope_hash,mapping_hash,parent_hash):
    if ROOT in parent:raise ValueError('named riser plan attributes already composed')
    if (scope.get('mode')!=SCOPE_MODE or scope.get('physical_values_fused') is not False
        or scope.get('local_graphs_mutated') is not False or scope.get('physical_ports_verified') is not False
        or scope.get('human_accepted') is not False or scope.get('installed_lengths_assigned')!=0
        or scope.get('mapping_sha256')!=mapping_hash):raise ValueError('unsupported named plan attribute scope')
    by={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(by)!=len(parent['edges']) or by.keys()!=raw.keys() or parent['nodes']!=local['nodes']:
        raise ValueError('named plan attachment local axis topology changed')
    mapped=copy.deepcopy(mapping);records=mapped['records'];scopes={r['mapping_id']:r for r in scope['records']}
    if len(scopes)!=len(scope['records']) or set(scopes)!={r['mapping_id'] for r in records}:
        raise ValueError('named attribute and mapping scopes differ')
    for record in records:
        row=scopes[record['mapping_id']]
        if (record['kind']!='named_riser_floor_approach' or len(record['iso_edges'])!=1
            or any(row[k]!=record[k] for k in ('plan_edges','iso_edges','system','floor','plan_riser_interface','iso_riser_junction'))
            or row.get('plan_glyph_radius_added_to_length') is not False or row.get('physical_port_verified') is not False
            or row.get('installed_whole_edge_length_mm') is not None or row.get('human_accepted') is not False):
            raise ValueError('named approach cannot claim a different route, radius or installed metric')
        eid=record['iso_edges'][0]
        if (by[eid]!=raw[eid] or 'cross_view_attributes' in by[eid]
            or by[eid]['attribute_paths']!=record['paths']['iso']['attribute_paths']):
            raise ValueError('selected axis approach changed or has an existing writer')
        record['iso_snapshot']=selected_snapshot(local,[eid])
    sources=dict(plan=scope['source_sha256'],isometric=mapping['source_sha256']['iso'],
                 plan_graph=scope['graph_sha256'],local_iso_graph=mapping['graph_sha256']['iso'])
    output,proof=attach(parent,mapped,plan,coverage,units,diameters,sources,mapping_hash)
    evidence=dict(records=[r['diameter'] for r in scope['records']],source_sha256=scope['source_sha256'],graph_sha256=scope['graph_sha256'])
    output,dn_proof=fuse_DN(output,mapped,plan,evidence,scope_hash)
    fusion=output.pop('sourceCheckedCrossViewAttributeFusion')
    if 'sourceCheckedCrossViewAttributeFusion' in parent:
        output['sourceCheckedCrossViewAttributeFusion']=copy.deepcopy(parent['sourceCheckedCrossViewAttributeFusion'])
    current={e['edge_id']:e for e in output['edges']};claimed=set()
    for record in records:
        row=scopes[record['mapping_id']];eid=record['iso_edges'][0];claimed.add(eid)
        attrs=current[eid]['cross_view_attributes']
        if (attrs['whole_edge_physical_length_mm'] is not None or attrs['diameter']['nominal_mm'] is not None
            or attrs['horizontal_projection']['value_mm']!=row['horizontal_projection']['value_mm']):
            raise ValueError('named approach attributes escaped their measured plan scope')
        attrs['mapping_basis']=BASIS
        attrs['named_riser_interface_context']=dict(identifier=record['identifier'],floor=record['floor'],
            plan_riser_interface=record['plan_riser_interface'],iso_riser_junction=record['iso_riser_junction'],
            equipment_anchor=record['equipment_id'],plan_equipment_main_T=record['plan_equipment_main_T'],
            iso_equipment_main_T=record['iso_equipment_main_T'],physical_port_verified=False,
            graphic_circle_radius_added_to_length=False,whole_installed_length_mm=None)
    for eid,edge in by.items():
        after=current[eid]
        if eid not in claimed and edge!=after:raise ValueError('prior unselected edge changed')
        if {k:v for k,v in edge.items() if k!='cross_view_attributes'}!={k:v for k,v in after.items() if k!='cross_view_attributes'}:
            raise ValueError('local geometry, vertical scope or components changed')
    fusion.update(status='source_checked_named_floor_plan_attributes_hil_pending',
        source_scope_sha256=scope_hash,mapping_sha256=mapping_hash,attribute_parent_graph_sha256=parent_hash,
        local_topology_prior_plan_and_vertical_attributes_preserved=True,human_accepted=False)
    output[ROOT]=fusion
    output.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_named_riser_plan_attribute_extension')
    return output,dict(records=proof,plan_DN_scope_fusion=dn_proof,added_axis_edges=sorted(claimed),
        prior_edges_and_vertical_attributes_preserved=True,physical_ports_verified=False,
        installed_lengths_assigned=0,whole_edge_DN_assigned=0,related_HIL_confirmation_inherited=False)


def compute(paths,policy):
    for key in ('parent_graph','attribute_scope','attribute_receipt','devices'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('named attribute attachment input changed '+key)
    folder=Path(paths['attribute_scope']).resolve().parent
    if Path(paths['attribute_scope']).resolve()!=folder/'named-riser-plan-attributes.json' or Path(paths['attribute_receipt']).resolve()!=folder/'named-riser-plan-attribute-receipt.json':
        raise ValueError('noncanonical named attribute scope')
    scope=verify_scopes(folder);receipt=load(paths['attribute_receipt'])
    parent=verify_parent(Path(paths['parent_graph']).parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):
        raise ValueError('named attachment parent or component inventory changed')
    inputs=receipt['inputs'];mapping=load(inputs['mapping']['path']);plan=load(inputs['graph']['path'])
    doc,_=read_source(inputs['source']['path']);local_path=Path(parent['native_local_graph']['path']);local=load(local_path)
    if sha(local_path)!=mapping['graph_sha256']['iso'] or sha(local_path)!=parent['native_local_graph']['sha256']:
        raise ValueError('named approach uses another local axis graph')
    observations={r['mapping_id']:native_local_diameters(doc,plan,r,scope['path_coverage']) for r in mapping['records']}
    graph,proof=append(load(paths['parent_graph']),local,plan,mapping,scope,scope['path_coverage'],scope['metric_evidence'],observations,
        sha(paths['attribute_scope']),sha(inputs['mapping']['path']),sha(paths['parent_graph']))
    return graph,dict(proof,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        native_local_graph=parent['native_local_graph'],verified_axis_segment_parent=parent,
        source_scope_sha256=sha(paths['attribute_scope']),mapping_sha256=sha(inputs['mapping']['path']))


def implementation_hashes():
    result=parent_hashes();result.update(scope_hashes())
    for name in ('attach_named_riser_plan_attributes.py','attach_source_checked_plan_attributes.py','fuse_plan_DN_scopes.py'):
        result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);audit=load(directory/'named-riser-plan-attribute-fusion-audit.json')
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('named attribute attachment implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('named attribute attachment dependency changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    if encode(graph)!=(directory/'graph_with_edges.json').read_bytes() or sha(directory/'graph_with_edges.json')!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):
        raise ValueError('named attribute attachment native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('named attribute attachment component CSV changed')
    return audit


def main():
    parser=argparse.ArgumentParser()
    for key in ('parent-graph','attribute-run','devices','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(parent_graph=a.parent_graph,attribute_scope=a.attribute_run/'named-riser-plan-attributes.json',
        attribute_receipt=a.attribute_run/'named-riser-plan-attribute-receipt.json',devices=a.devices,policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    graph,audit=compute(paths,load(a.policy));a.output.mkdir(parents=True)
    (a.output/'graph_with_edges.json').write_bytes(encode(graph));shutil.copyfile(a.devices,a.output/'edge_device_instances.csv')
    audit.update(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),
        output_graph_sha256=sha(a.output/'graph_with_edges.json'),human_accepted=False,hil_ready=False)
    (a.output/'named-riser-plan-attribute-fusion-audit.json').write_bytes(encode(audit))
    print(dict(added_named_approach_edges=len(audit['added_axis_edges']),physical_ports_verified=False,installed_lengths_assigned=0),flush=True)


if __name__=='__main__':main()
