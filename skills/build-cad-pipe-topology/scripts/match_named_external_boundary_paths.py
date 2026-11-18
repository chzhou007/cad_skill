"""Match named external feeds using destinations, separate ports and proven Ts."""
import argparse,copy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_external_pipe_destination import verify_output as verify_plan,implementation_hashes as plan_hashes
from native_external_port_destination import verify_output as verify_axis,implementation_hashes as axis_hashes
from native_inline_joint_path_coverage import verify_output as verify_inline,implementation_hashes as inline_hashes
from match_anchored_floor_main_network import verify_output as verify_main,implementation_hashes as main_hashes
from attach_confirmed_gap_joints import verify_output as verify_gaps
from native_path_coverage_audit import audit as audit_paths
from crossview_equipment_branch_inventory import index_graph

MODE='source_checked_named_external_boundary_paths_v1'


def match(graphs,main,plan,axis,inline,gap_graph,gap_audit,axis_coverage):
    hashes=dict(plan=main['plan_graph_sha256'],iso=main['iso_graph_sha256']);sources=main['source_sha256'];structure=main['evidence']['structure']
    if structure.get('unique_full_floor_T_network') is not True:raise ValueError('unique source-checked T network required')
    for evidence,view in ((plan,'plan'),(axis,'iso')):
        if (evidence['source_sha256']!=sources[view] or evidence['graph_sha256']!=hashes[view]
            or any(evidence.get(k) is not False for k in ('graph_mutated','human_accepted','hil_ready','common_marker_creates_pipe_connection'))
            or evidence.get('new_connections_added')!=0):raise ValueError('external source evidence differs')
    if (inline['source_sha256']!=sources['plan'] or inline['graph_sha256']!=hashes['plan'] or inline.get('graph_mutated') is not False
        or axis_coverage['source_sha256']!=sources['iso'] or axis_coverage['graph_sha256']!=hashes['iso']):raise ValueError('external source path proof differs')
    by_plan={r['identifier']:r for r in plan['records']};by_axis={r['identifier']:r for r in axis['records']}
    if (len(by_plan)<2 or len(by_plan)!=len(plan['records']) or len(by_axis)!=len(axis['records']) or by_plan.keys()!=by_axis.keys()
        or plan['destination']!=axis['destination']):raise ValueError('complete uniquely named external groups required')
    indices={v:index_graph(g) for v,g in graphs.items()};old={e['edge_id']:e for e in gap_graph['edges']}
    covered={r['edge_id']:r for r in axis_coverage['edges']};plan_inline={r['edge_id']:r for r in inline['records']};records=[];used=set()
    for name,p in sorted(by_plan.items()):
        a=by_axis[name];pn,pe,padj=indices['plan'];an,ae,aadj=indices['iso'];ep=pe[p['edge_id']];ea=ae[a['edge_id']]
        if (p['system']!=a['system'] or p['floor']!=a['floor'] or p['floor']!=main['floor']
            or ep['system']!=p['system'] or ea['system']!=p['system'] or p['edge_id'] not in plan_inline
            or len(padj[p['node_id']])!=1 or ep not in padj[p['node_id']] or a['port_id'] in used):raise ValueError('external system, floor or ownership differs')
        used.add(a['port_id']);pt=ep['end_node_id'] if ep['start_node_id']==p['node_id'] else ep['start_node_id'];at=ea['end_node_id'] if ea['start_node_id']==a['node_id'] else ea['start_node_id']
        if (pn[pt].get('node_type') not in ('tee','physical_junction') or an[at].get('node_type') not in ('tee','physical_junction')
            or len(padj[pt])!=3 or len(aadj[at])!=3 or {e['system'] for e in padj[pt]}!={p['system']} or {e['system'] for e in aadj[at]}!={p['system']}
            or structure['node_mapping'].get(pt)!=at
            or pn[pt]['floor']!=p['floor'] or an[at]['floor']!=p['floor']):raise ValueError('named external route disagrees with independently matched main T')
        if old.get(ea['edge_id'])!=ea or not ea.get('source_confirmed_gap_joints'):raise ValueError('confirmed original axis gap route changed')
        paths=ea['attribute_paths'];coverage=covered[ea['edge_id']]
        if len(paths)!=1 or len(coverage['segments'])!=len(paths[0])-1:raise ValueError('axis external path coverage incomplete')
        display=0 if ea['start_node_id']==a['node_id'] else len(paths[0])-2
        expected=[a['display_only_centre_span'][0],a['display_only_centre_span'][1]]
        if display!=0:expected.reverse()
        if paths[0][display:display+2]!=expected:raise ValueError('axis marker display span moved')
        gaps={r['gap_segment_index']:r for r in ea['source_confirmed_gap_joints']};audit_rows={r['edge_id']:r for r in gap_audit['records']}
        if (len(gaps)!=1 or ea['edge_id'] not in audit_rows or any(r!=audit_rows[ea['edge_id']] for r in gaps.values())
            or display in gaps):raise ValueError('native reviewed inline joint identity differs')
        for segment in coverage['segments']:
            index=segment['index']
            if index==display:
                if segment['status']!='no_witness_in_scoped_search':raise ValueError('display span unexpectedly owns a native pipe')
            elif index in gaps:
                joint=gaps[index]
                if (segment['status']!='no_witness_in_scoped_search' or paths[0][index:index+2]!=joint['gap_endpoints']
                    or joint.get('status')!='user_confirmed_inline_joint_logical_continuity' or joint.get('physical_length')!='unknown'
                    or joint.get('parameter_status')!='unknown_not_zero'):raise ValueError('unqualified inline source gap')
            elif segment['status']!='single_source_line_covers':raise ValueError('unexplained native external route gap')
        records.append(dict(mapping_id='EXTERNAL-F'+str(p['floor'])+'-'+name,kind='named_external_port_to_matched_main_T',floor=p['floor'],system=p['system'],identifier=name,
            destination=plan['destination'],plan_edges=[ep['edge_id']],iso_edges=[ea['edge_id']],plan_boundary_node=p['node_id'],axis_boundary_node=a['node_id'],axis_port_id=a['port_id'],
            plan_main_T=pt,axis_main_T=at,axis_display_only_segment_index=display,native_plan_destination=copy.deepcopy(p),native_axis_destination=copy.deepcopy(a),
            native_plan_inline_path=copy.deepcopy(plan_inline[ep['edge_id']]),native_axis_path_coverage=copy.deepcopy(coverage),native_axis_confirmed_gap=copy.deepcopy(list(gaps.values())),
            external_ports_connected_to_each_other=False,physical_external_connection_verified=False,physical_port_verified=False,physical_length_mm=None,whole_edge_DN_assigned=False,human_accepted=False))
    return dict(mode=MODE,status='source_checked_named_external_paths_attributes_and_semantic_adoption_pending',floor=main['floor'],records=records,
        graph_sha256=hashes,source_sha256=sources,local_graphs_mutated=False,new_connections_added=0,physical_values_assigned=0,human_accepted=False,hil_ready=False)


def compute(paths,policy):
    for data,receipt,data_name,receipt_name in (
        ('main_mapping','main_receipt','mapping.json','source-mapping-receipt.json'),
        ('plan_destinations','plan_destination_receipt','external-destinations.json','external-destination-receipt.json'),
        ('axis_destinations','axis_destination_receipt','external-port-destinations.json','external-port-destination-receipt.json'),
        ('plan_inline','plan_inline_receipt','inline-joint-coverage.json','inline-joint-coverage-receipt.json')):
        folder=Path(paths[data]).resolve().parent
        if Path(paths[data]).name!=data_name or Path(paths[receipt]).resolve()!=folder/receipt_name:raise ValueError('noncanonical external mapping source '+data)
    if Path(paths['gap_audit']).name!='confirmed-gap-joint-audit.json':raise ValueError('noncanonical original gap owner')
    for key in paths:
        if key!='policy' and sha(paths[key])!=policy[key+'_sha256']:raise ValueError('external mapping input changed '+key)
    main_folder=Path(paths['main_mapping']).parent;main=verify_main(main_folder);mr=load(paths['main_receipt'])
    plan=verify_plan(Path(paths['plan_destinations']).parent);axis=verify_axis(Path(paths['axis_destinations']).parent);inline=verify_inline(Path(paths['plan_inline']).parent)
    gap_folder=Path(paths['gap_audit']).parent;gap_audit=verify_gaps(gap_folder);gap_graph=load(gap_folder/'graph_with_edges.json')
    li=mr['local_inputs'];graphs={v:load(li[v+'_graph']['path']) for v in ('plan','iso')}
    if (main['plan_graph_sha256']!=sha(li['plan_graph']['path']) or main['iso_graph_sha256']!=sha(li['iso_graph']['path'])
        or gap_audit['inputs']['source']['sha256']!=main['source_sha256']['iso']):raise ValueError('external mapping graph or original gap source differs')
    source=Path(li['iso_source']['path']);doc,preflight=read_source(source)
    if sha(source)!=main['source_sha256']['iso']:raise ValueError('axis original source changed')
    coverage=audit_paths(doc,graphs['iso'],dict(source_sha256=sha(source),graph_sha256=main['iso_graph_sha256'],edges=[r['edge_id'] for r in axis['records']]),sha(source),main['iso_graph_sha256'])
    result=match(graphs,main,plan,axis,inline,gap_graph,gap_audit,coverage)
    result.update(main_mapping_sha256=sha(paths['main_mapping']),source_preflight=preflight)
    for key in paths:
        if key!='policy' and sha(paths[key])!=policy[key+'_sha256']:raise ValueError('external mapping input changed during replay '+key)
    return result


def implementation_hashes():
    result=main_hashes();result.update(plan_hashes());result.update(axis_hashes());result.update(inline_hashes())
    for name in (Path(__file__).name,'attach_confirmed_gap_joints.py','screen_missing_gap_joints.py','repair_exploded_joint_ownership.py'):result[name]=sha(Path(__file__).with_name(name))
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'named-external-path-mapping-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('external mapping implementation changed')
    for row in receipt['inputs'].values():
        if sha(row['path'])!=row['sha256']:raise ValueError('external mapping dependency changed')
    result=compute({k:r['path'] for k,r in receipt['inputs'].items()},load(receipt['inputs']['policy']['path']))
    if encode(result)!=(directory/'mapping.json').read_bytes() or sha(directory/'mapping.json')!=receipt['output_sha256']:raise ValueError('external mapping native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('main-run','plan-destination-run','axis-destination-run','plan-inline-run','gap-run','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths=dict(main_mapping=a.main_run/'mapping.json',main_receipt=a.main_run/'source-mapping-receipt.json',
        plan_destinations=a.plan_destination_run/'external-destinations.json',plan_destination_receipt=a.plan_destination_run/'external-destination-receipt.json',
        axis_destinations=a.axis_destination_run/'external-port-destinations.json',axis_destination_receipt=a.axis_destination_run/'external-port-destination-receipt.json',
        plan_inline=a.plan_inline_run/'inline-joint-coverage.json',plan_inline_receipt=a.plan_inline_run/'inline-joint-coverage-receipt.json',gap_audit=a.gap_run/'confirmed-gap-joint-audit.json',policy=a.policy)
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);target=a.output/'mapping.json';target.write_bytes(encode(result))
    (a.output/'named-external-path-mapping-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(Path(v).resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False,hil_ready=False)))
    print(dict(external_paths=len(result['records']),new_connections_added=0,physical_values_assigned=0),flush=True)

if __name__=='__main__':main()
