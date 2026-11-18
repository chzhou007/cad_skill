"""Extend a complete axis parent with four source-checked direct-main scopes."""
import argparse
import copy
import math
import re
import shutil
import sys
from pathlib import Path

_runtime=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_runtime) not in sys.path:sys.path.insert(0,str(_runtime))

from confirm_crossview_paths import encode,load,sha
from known_junction_main_plan_attributes import verify_output as verify_attributes,check_result as check_attributes,MODE as ATTRIBUTE_MODE
from adopt_current_floor_plan_scopes import verify_output as verify_parent
from attach_anchored_floor_main_attributes import horizontal_domain
from match_source_checked_crossview_paths import selected_snapshot
from native_replay_session import verify_once

MODE='known_junction_main_plan_attribute_fusion_v1'
ROOT='sourceKnownJunctionMainAttributes'
FIELD='anchored_floor_main_attributes'
AUDIT='known-junction-main-fusion-audit.json'
ATTRIBUTE_FIELDS={'cross_view_attributes','anchored_floor_main_attributes','external_feed_plan_attributes',
    'network_named_lower_plan_attributes','plan_segment_attributes','axis_riser_attributes',
    'current_plan_scope_evidence','current_floor_plan_scope_evidence'}


def restore(graph,stage,parent):
    if (graph.get(ROOT)!=stage or stage.get('mode')!=MODE or stage.get('prior_topology_components_and_all_attributes_preserved') is not True
        or stage.get('human_accepted') is not False or stage.get('related_HIL_confirmation_inherited') is not False
        or stage.get('new_connections_added')!=0 or graph.get('metadata',{}).get('hil_ready') is not False):
        raise ValueError('Direct-main fusion stage or parent preservation differs')
    records={r['axis_edge']:r for r in stage['records']}
    if len(records)!=len(stage['records']) or len(records)!=stage['added_main_attributes']:
        raise ValueError('Direct-main root repeats or loses an attribute writer')
    result=copy.deepcopy(graph);result.pop(ROOT);result['metadata']=copy.deepcopy(parent.get('metadata',{}))
    found=set()
    for edge in result['edges']:
        if edge['edge_id'] in records:
            if edge.get(FIELD)!=records[edge['edge_id']]:raise ValueError('Direct-main root and edge attribute differ')
            edge.pop(FIELD);found.add(edge['edge_id'])
    if found!=set(records) or result!=parent:raise ValueError('Fusion changed prior nodes, edges, components, attributes or evidence')
    return result


def append(parent,local,mapping,attributes,hashes,angles):
    if ROOT in parent:raise ValueError('Direct-main attributes already composed')
    if any(not isinstance(v,str) or not re.fullmatch('[0-9a-f]{64}',v) for v in hashes.values()):raise ValueError('Invalid fusion evidence hash')
    if attributes.get('mode')!=ATTRIBUTE_MODE:raise ValueError('Native direct-main attribute owner required')
    check_attributes(attributes)
    if (attributes['mapping_sha256']!=hashes['mapping'] or attributes['graph_sha256']!=mapping['plan_graph_sha256']
        or attributes['source_sha256']!=mapping['source_sha256']['plan']):raise ValueError('Direct-main source version differs')
    old={e['edge_id']:e for e in parent['edges']};raw={e['edge_id']:e for e in local['edges']}
    if len(old)!=len(parent['edges']) or len(raw)!=len(local['edges']) or old.keys()!=raw.keys():raise ValueError('Complete parent/local edge set differs')
    if {n['node_id'] for n in parent['nodes']}!={n['node_id'] for n in local['nodes']}:raise ValueError('Complete parent/local node identities differ')
    for eid,e in old.items():
        if {k:v for k,v in e.items() if k not in ATTRIBUTE_FIELDS}!=raw[eid]:raise ValueError('Complete parent pipe geometry or component inventory differs')
    records={r['mapping_id']:r for r in mapping['records']};values={r['mapping_id']:r for r in attributes['records']}
    if len(records)!=len(mapping['records']) or len(values)!=len(attributes['records']) or records.keys()!=values.keys():raise ValueError('Mapping and attribute scope incomplete or repeated')
    result=copy.deepcopy(parent);target={e['edge_id']:e for e in result['edges']};rows=[];claimed=set()
    for mid,record in records.items():
        value=values[mid]
        if any(value[k]!=record[k] for k in ('floor','system','plan_edges','iso_edges')) or len(record['iso_edges'])!=1 or len(record['plan_edges'])!=1:
            raise ValueError('Direct-main attribute correspondence differs')
        eid=record['iso_edges'][0]
        if eid in claimed or ATTRIBUTE_FIELDS.intersection(old[eid]):raise ValueError('New direct-main writer overlaps existing attributes or evidence')
        claimed.add(eid)
        if selected_snapshot(parent,[eid])!=record['iso_snapshot'] or selected_snapshot(local,[eid])!=record['iso_snapshot']:
            raise ValueError('Selected direct-main native axis snapshot changed')
        points=horizontal_domain(local,record,angles);metric=value['horizontal_projection'];dn=value['diameter'];mm=metric['value_mm']
        pieces=metric['pieces'];keys=[(p['plan_edge'],p['path_index'],p['segment_index']) for p in pieces]
        if (isinstance(mm,bool) or not isinstance(mm,(int,float)) or not math.isfinite(mm) or mm<=0 or not pieces
            or len(keys)!=len(set(keys)) or abs(sum(p['length_mm'] for p in pieces)-mm)>.0001):raise ValueError('Native plan metric pieces differ or repeat')
        partial=metric['status']=='native_plan_pipe_XY_inline_interiors_unknown'
        if partial and (metric.get('joint_graphic_spans_added') is not False or metric.get('inline_joint_interior_length_mm') is not None):
            raise ValueError('Inline marker interior cannot become pipe length')
        item=dict(mapping_id=mid,floor=record['floor'],system=record['system'],axis_edge=eid,plan_edges=record['plan_edges'],iso_edges=record['iso_edges'],
            status='source_checked_known_junction_main_attributes_human_pending',scope='native_same_floor_T_to_T_main',scope_paths=copy.deepcopy([points]),
            nominal_mm=dn['nominal_mm'],diameter_evidence=copy.deepcopy(dn),horizontal_projection=copy.deepcopy(metric),inline_interiors_unknown=partial,
            complete_horizontal_centerline_route_mm=None if partial else mm,pipe_net_cut_length_mm=None,installed_whole_edge_length_mm=None,
            physical_ports_verified=False,human_accepted=False,related_HIL_confirmation_inherited=False,
            source_sha256=copy.deepcopy(mapping['source_sha256']),local_graph_sha256=dict(plan=mapping['plan_graph_sha256'],iso=mapping['iso_graph_sha256']),
            mapping_sha256=hashes['mapping'],attribute_scope_sha256=hashes['attributes'],parent_graph_sha256=hashes['parent'])
        target[eid][FIELD]=item;rows.append(copy.deepcopy(item))
    stage=dict(mode=MODE,status='source_checked_known_junction_mains_complete_parent_hil_pending',floor=mapping['floor'],records=rows,
        parent_graph_sha256=hashes['parent'],added_main_attributes=len(rows),known_DN_scopes=sum(r['nominal_mm'] is not None for r in rows),
        inline_interiors_unknown=sum(r['inline_interiors_unknown'] for r in rows),prior_topology_components_and_all_attributes_preserved=True,
        new_connections_added=0,related_HIL_confirmation_inherited=False,human_accepted=False)
    result[ROOT]=stage;result.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_known_junction_main_attributes')
    restore(result,stage,parent)
    return result,stage


def compute(paths,policy):
    for key,path in paths.items():
        if key!='policy' and sha(path)!=policy.get(key+'_sha256'):raise ValueError('Fusion dependency changed: '+key)
    folder=Path(paths['attributes']).resolve().parent;parent_folder=Path(paths['parent_graph']).resolve().parent
    if Path(paths['attribute_receipt']).resolve()!=folder/'known-main-attribute-receipt.json' or Path(paths['attributes']).name!='attributes.json':
        raise ValueError('Canonical direct-main attribute source required')
    # A bounded replay session can reuse only native results obtained in this
    # process after validating their complete observed input/code read closure.
    # Outside a session verify_once performs the full verifier call.
    attributes=verify_once(folder,verify_attributes);parent=verify_once(parent_folder,verify_parent)
    if parent['output_graph_sha256']!=sha(paths['parent_graph']) or parent['inputs']['devices']['sha256']!=sha(paths['devices']):
        raise ValueError('Complete current parent or component inventory differs')
    receipt=load(paths['attribute_receipt']);mp=Path(receipt['inputs']['mapping']['path']);mapping=load(mp)
    if sha(mp)!=attributes['mapping_sha256']:raise ValueError('Native attribute mapping changed')
    local=load(receipt['inputs']['mapping_receipt']['path'])['local_inputs'];ip=local['iso_graph']
    if sha(ip['path'])!=mapping['iso_graph_sha256'] or parent['native_local_graph']['sha256']!=ip['sha256']:
        raise ValueError('Complete parent uses another native axis graph')
    graph,stage=append(load(paths['parent_graph']),load(ip['path']),mapping,attributes,
        dict(parent=sha(paths['parent_graph']),mapping=sha(mp),attributes=sha(paths['attributes'])),policy['isometric_horizontal_directions_degrees'])
    for key,path in paths.items():
        if key!='policy' and sha(path)!=policy[key+'_sha256']:raise ValueError('Fusion input changed during native replay')
    return graph,dict(stage=stage,parent_graph=dict(path=str(Path(paths['parent_graph']).resolve()),sha256=sha(paths['parent_graph'])),
        verified_complete_parent=parent,native_local_graph=parent['native_local_graph'],mapping_path=str(mp),attribute_scope_path=str(Path(paths['attributes']).resolve()))


def implementation_hashes():
    from known_junction_main_plan_attributes import implementation_hashes as attribute_hashes
    from adopt_current_floor_plan_scopes import implementation_hashes as parent_hashes
    import native_direct_verification_runtime
    values=parent_hashes();values.update(attribute_hashes());values[Path(__file__).name]=sha(__file__)
    values['native_replay_session.py']=sha(Path(native_direct_verification_runtime.__file__).with_name('native_replay_session.py'))
    return values


def verify_output(directory):
    directory=Path(directory);audit=load(directory/AUDIT)
    if audit.get('mode')!=MODE or audit['implementation_sha256']!=implementation_hashes():raise ValueError('Fusion implementation changed')
    for item in audit['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Fusion input changed')
    paths={k:v['path'] for k,v in audit['inputs'].items()};graph,proof=compute(paths,load(paths['policy']))
    out=directory/'graph_with_edges.json'
    if encode(graph)!=out.read_bytes() or sha(out)!=audit['output_graph_sha256'] or any(audit.get(k)!=v for k,v in proof.items()):
        raise ValueError('Fusion independent native replay differs')
    if (directory/'edge_device_instances.csv').read_bytes()!=Path(paths['devices']).read_bytes():raise ValueError('Canonical components changed during fusion')
    return audit


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--policy',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();policy=load(a.policy);paths={k:Path(v['path']) for k,v in policy['inputs'].items()};paths['policy']=a.policy
    if a.output.exists():raise FileExistsError(a.output)
    graph,proof=compute(paths,policy);a.output.mkdir(parents=True);out=a.output/'graph_with_edges.json';out.write_bytes(encode(graph))
    shutil.copyfile(paths['devices'],a.output/'edge_device_instances.csv')
    shutil.copyfile(Path(paths['parent_graph']).parent/'source-comparison-gate.json',a.output/'source-comparison-gate.json')
    (a.output/AUDIT).write_bytes(encode(dict(proof,mode=MODE,
        inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),
        output_graph_sha256=sha(out),human_accepted=False,hil_ready=False)))
    print(dict(added_main_attributes=proof['stage']['added_main_attributes'],complete_parent_preserved=True,human_accepted=False),flush=True)


if __name__=='__main__':main()
