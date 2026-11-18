"""Apply existing non-node boundary/outward/path rules to all adopted main Ts."""
import argparse,collections,copy,hashlib,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from reapply_capped_branch_correspondence import main_support
from crossview_equipment_branch_inventory import index_graph,native_tee
from ordered_anchor_branch_paths import outward,retained_boundary_geometry,branch_snapshot
from legacy_named_provider_inventory import current_plan_reader,require
from current_plan_crossover_path_reapplication import audit as plan_coverage
from batch_native_path_coverage import collect as axis_coverage
from native_drawing_marker_ports import collect as marker_ports
from source_readability import read_source

MODE='native_complete_nonnode_boundary_branch_reapplication_v1'

def discover(provider,plan,axis,floor):
    pn,pe,pa=index_graph(plan);an,ae,aa=index_graph(axis);owners={r['edge_id']:r for r in provider['records']};boundaries={b['boundary_id']:b for b in plan.get('boundary_anchors',[])}
    require(len(boundaries)==len(plan.get('boundary_anchors',[])),'duplicate source boundary identity')
    owners_by_boundary=collections.Counter(e.get(side+'_boundary_id')for e in plan['edges']for side in ('start','end')if e.get(side+'_boundary_id')is not None)
    require(set(owners_by_boundary)<=set(boundaries)and all(n==1 for n in owners_by_boundary.values()),'source boundary has missing or competing edge owners')
    records=[];pending=[];existing=[];seen=set()
    for edge in plan['edges']:
        for side in ('start','end'):
            bid=edge.get(side+'_boundary_id')
            if bid is None:continue
            base=dict(floor=floor,system=edge['system'],plan_edge_id=edge['edge_id'],boundary_id=bid)
            try:
                require(edge.get(side+'_node_id')is None and bid in boundaries,'explicit non-node source boundary required')
                require(bid not in seen,'source boundary has competing edge owners');seen.add(bid)
                anchor=edge.get(('end'if side=='start'else'start')+'_node_id');target=provider['ordinary_junction_mappings'][str(floor)].get(anchor)
                require(anchor in pn and target in an,'boundary has no independently mapped ordinary T')
                off=[e for e in aa[target]if not owners[e['edge_id']]['has_existing_correspondence']]
                if not off:existing.append(base);continue
                require(len(off)==1,'one unclaimed axis branch required')
                a=off[0];support=main_support(provider,dict(plan=plan,iso=axis),anchor,target,edge['edge_id'],a['edge_id'],floor,edge['system'])
                b=boundaries[bid]
                require(b.get('kind')=='expert_non_node_source_boundary'and b.get('source_marker_kind')=='two_bar'and bool(b.get('expert_issue')),'existing retained two-bar boundary owner has another family')
                require(b.get('system')==edge['system']and b.get('source_pipe_handle')in edge['source_handles'],'boundary and source pipe belong to different systems')
                r=dict(base,axis_edge_id=a['edge_id'],plan_anchor=anchor,axis_anchor=target,plan_boundary=copy.deepcopy(b),**support)
                r['mapping_id']='BOUNDARY-BRANCH-'+hashlib.sha256(encode(dict(floor=floor,system=edge['system'],plan=edge['edge_id'],axis=a['edge_id'],anchors=[anchor,target],boundary=bid))).hexdigest()[:16];records.append(r)
            except(ValueError,KeyError)as exc:pending.append(dict(base,reason=str(exc)))
    require(len({r['axis_edge_id']for r in records})==len({r['plan_edge_id']for r in records})==len(records),'competing boundary branch correspondence')
    return records,pending,existing

def qualify(row,graphs,docs,hashes,reader):
    plan_edges=index_graph(graphs['plan'])[1];boundary=retained_boundary_geometry(docs['plan'],row['plan_boundary'],plan_edges[row['plan_edge_id']])
    routes={v:outward(graphs[v],row['plan_anchor'if v=='plan'else'axis_anchor'],set(row['blocked'][v]),row['system'],row['floor'])for v in graphs}
    require(routes['plan']['terminal_kind']=='source_boundary'and routes['plan']['terminal_id']==row['boundary_id']and routes['iso']['terminal_kind']=='drawing_marker_interface','native boundary branch terminates in another source family')
    require(routes['plan']['edges']==[row['plan_edge_id']]and routes['iso']['edges']==[row['axis_edge_id']],'boundary correspondence cannot skip intermediate edges')
    marker=marker_ports(docs['iso'],graphs['iso'],routes['iso']['terminal_id'],hashes['iso']['source'],hashes['iso']['graph']);ports=[p for p in marker['records']if p['edge_id']==row['axis_edge_id']and p['system']==row['system']]
    require(len(ports)==1,'one independent same-system axis drawing port required');checks={}
    for v in graphs:
        eid=row['plan_edge_id'if v=='plan'else'axis_edge_id'];anchor=row['plan_anchor'if v=='plan'else'axis_anchor'];h=hashes[v]
        path=plan_coverage(docs[v],graphs[v],eid,anchor,h['source'],h['graph'],reader)if v=='plan'else axis_coverage(docs[v],graphs[v],[eid],h['source'],h['graph'])
        for item in path['edges']:
            for seg in item['segments']:
                if v=='iso'and seg['index']==ports[0]['display_segment_index']:continue
                require(seg['status']=='single_source_line_covers','native boundary branch coverage is not unique')
        checks[v]=dict(native_T=(reader if v=='plan'else native_tee)(docs[v],graphs[v],anchor,h['source'],h['graph']),native_path=path,snapshot=branch_snapshot(graphs[v],[eid]))
    return dict(row,routes=routes,native_checks=checks,retained_source_boundary_geometry=boundary,axis_drawing_port=ports[0],
        scope='native_anchored_non_node_boundary_drawing_context_only',boundary_role_preserved=True,source_boundary_promoted_to_node=False,
        other_system_port_assigned=False,remote_equipment_identity_assigned=False,whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,vertical_values_assigned=0,human_accepted=False)

def compute(manifest):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'non-node branch input changed')
    checked();provider=load(inputs['provider']['path']);axis=load(inputs['axis_graph']['path']);config=load(inputs['current_T_source_config']['path'])
    require(provider['inputs']['axis_graph']==inputs['axis_graph']and provider['inputs']['axis_source']==inputs['axis_source'],'current axis source namespace differs')
    # Strict Chinese extraction for every participating view precedes experiments.
    docs={};graphs={};preflight={}
    docs['iso'],preflight['iso']=read_source(inputs['axis_source']['path']);require(axis['metadata']['source_sha256']==inputs['axis_source']['sha256'],'axis graph/source binding differs')
    for f in ('1','2','3'):
        for k in ('plan_source_'+f,'plan_graph_'+f):require(provider['inputs'][k]==inputs[k],'current plan source namespace differs')
        docs[f],preflight[f]=read_source(inputs['plan_source_'+f]['path']);graphs[f]=load(inputs['plan_graph_'+f]['path']);require(graphs[f]['metadata']['source_sha256']==inputs['plan_source_'+f]['sha256'],'plan graph/source binding differs')
    records=[];pending=[];existing=[];screened=0
    for f,plan in graphs.items():
        proposed,held,prior=discover(provider,plan,axis,int(f));pending.extend(held);existing.extend(prior);screened+=len(proposed)+len(held)+len(prior)
        hashes=dict(plan=dict(source=inputs['plan_source_'+f]['sha256'],graph=inputs['plan_graph_'+f]['sha256']),iso=dict(source=inputs['axis_source']['sha256'],graph=inputs['axis_graph']['sha256']))
        reader=current_plan_reader(config,hashes['plan']['source'],hashes['plan']['graph'])
        for row in proposed:
            try:records.append(qualify(row,dict(plan=plan,iso=axis),dict(plan=docs[f],iso=docs['iso']),hashes,reader))
            except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],axis_edge_id=row['axis_edge_id'],plan_edge_id=row['plan_edge_id'],reason=str(exc)))
    checked()
    return dict(mode=MODE,inputs=copy.deepcopy(inputs),records=records,pending=pending,existing_boundary_contexts=existing,source_preflight=preflight,
        all_current_plan_boundary_edges_screened=True,original_boundary_outward_T_path_and_marker_owners_reused=True,
        counts=dict(screened_boundaries=screened,existing_contexts=len(existing),new_drawing_correspondences=len(records),pending=len(pending)),
        graph_mutated=False,old_providers_replaced=False,source_boundaries_promoted_to_nodes=0,other_system_ports_assigned=0,remote_equipment_identities_assigned=0,physical_lengths_assigned=0,whole_axis_DN_assigned=0,vertical_values_assigned=0,human_accepted=False,whole_goal_complete=False)

def implementations():
    names=('reapply_capped_branch_correspondence','ordered_anchor_branch_paths','legacy_named_provider_inventory','crossview_equipment_branch_inventory','current_plan_crossover_path_reapplication','native_drawing_marker_ports','batch_native_path_coverage','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh non-node branch output required');code=implementations();result=compute(load(manifest));require(code==implementations(),'non-node branch implementation changed')
    output.mkdir(parents=True);target=output/'nonnode-boundary-branches.json';target.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');require(r['mode']==MODE and r['implementation_sha256']==implementations()and sha(r['manifest']['path'])==r['manifest']['sha256']and sha(output/'nonnode-boundary-branches.json')==r['output_sha256'],'non-node branch receipt changed')
    fresh=compute(load(r['manifest']['path']));require(encode(fresh)==(output/'nonnode-boundary-branches.json').read_bytes(),'non-node branch independent native replay differs');return fresh

def main():
    p=argparse.ArgumentParser()
    for n in ('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(dict(mode=MODE,counts=r['counts']),flush=True)
if __name__=='__main__':main()
