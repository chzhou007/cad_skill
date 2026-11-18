"""Compose existing capped-caption, marker-port and native branch owners.

Correspondence is a source-bounded drawing context. It assigns neither a
remote device nor the other system's port, DN, or omitted physical length.
"""
import argparse,collections,copy,hashlib,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from batch_discover_capped_annotations import verify_output as verify_plan_caps
from native_capped_marker_port_context import verify_output as verify_axis_caps
from source_capped_branch_roles import apply as apply_plan_roles
from source_readability import read_source
from crossview_equipment_branch_inventory import index_graph,native_tee
from ordered_anchor_branch_paths import outward,branch_snapshot
from legacy_named_provider_inventory import current_plan_reader,require
from current_plan_crossover_path_reapplication import audit as plan_coverage
from batch_native_path_coverage import collect as axis_coverage
from native_drawing_marker_ports import collect as marker_ports

MODE='native_capped_branch_anchored_crossview_reapplication_v1'

def main_support(provider,graphs,plan_anchor,axis_anchor,plan_edge,axis_edge,floor,system):
    rows={r['edge_id']:r for r in provider['records']}
    require(provider['ordinary_junction_mappings'][str(floor)].get(plan_anchor)==axis_anchor,'independent ordinary T identity required')
    require(not rows[axis_edge]['has_existing_correspondence'],'existing branch provider must be preserved')
    stars={v:index_graph(g)[2][n]for v,g,n in [('plan',graphs['plan'],plan_anchor),('iso',graphs['iso'],axis_anchor)]}
    require(all(len(es)==3 and {e['system']for e in es}=={system}for es in stars.values()),'complete same-system T stars required')
    blocked={v:{e['edge_id']for e in es}-{plan_edge if v=='plan'else axis_edge}for v,es in stars.items()}
    require(all(len(es)==2 for es in blocked.values()),'branch must be a direct third arm')
    support=[];used=set()
    for ae in sorted(blocked['iso']):
        hits=[o for o in rows[ae]['correspondence_observations']if o.get('domain')=='ordinary_local_graph'and o.get('floor')==floor
              and o.get('grouped_axis_edges')==[ae]and len(o.get('plan_edges',[]))==1 and o['plan_edges'][0]in blocked['plan']]
        require(rows[ae]['has_existing_correspondence']and len(hits)==1,'two independently adopted ordinary main arms required')
        require(hits[0]['plan_edges'][0]not in used,'main arm correspondences collapse')
        used.add(hits[0]['plan_edges'][0]);support.append(copy.deepcopy(hits[0]))
    require(used==blocked['plan'],'complete independent main correspondence required')
    return dict(blocked={v:sorted(es)for v,es in blocked.items()},main_correspondence_evidence=support)

def candidates(provider,graphs,plan_inventories,axis_caps):
    pn,pe,pa=index_graph(graphs['plan']);an,ae,aa=index_graph(graphs['iso']);out=[];pending=[]
    for cap in plan_inventories:
        try:
            node=pn[cap['node_id']];edge=pe[cap['edge_id']];system=cap['system'];floor=node['floor']
            require(node.get('system')==edge['system']==system and len(pa[node['node_id']])==1,'native cap must be a unique same-system plan leaf')
            require(node['node_id']in [edge['start_node_id'],edge['end_node_id']],'caption targets another edge')
            anchor=edge['end_node_id']if edge['start_node_id']==node['node_id']else edge['start_node_id']
            require(anchor in pn and pn[anchor].get('floor')==floor,'plan cap must have a same-floor T anchor')
            hits=[]
            for group in axis_caps:
                if group['qualifier_text']!=cap['qualifier']['text']or group['declared_quantity']!=cap['caption']['declared_group_quantity']:continue
                for port in group['members']:
                    if port['system']!=system or port['floor']!=floor:continue
                    e=ae[port['edge_id']];target=e['end_node_id']if e['start_node_id']==port['node_id']else e['start_node_id']
                    if provider['ordinary_junction_mappings'][str(floor)].get(anchor)!=target:continue
                    support=main_support(provider,graphs,anchor,target,edge['edge_id'],e['edge_id'],floor,system)
                    hits.append(dict(plan_cap=copy.deepcopy(cap),axis_cap=copy.deepcopy(group),axis_cap_port=copy.deepcopy(port),floor=floor,system=system,
                        plan_anchor=anchor,axis_anchor=target,plan_edge_id=edge['edge_id'],axis_edge_id=e['edge_id'],**support))
            require(len(hits)==1,'native caption quantity, system and independent T do not select one separate axis port')
            row=hits[0];row['mapping_id']='CAP-BRANCH-'+hashlib.sha256(encode(dict(plan=row['plan_edge_id'],axis=row['axis_edge_id'],floor=floor,system=system,anchors=[anchor,row['axis_anchor']]))).hexdigest()[:16];out.append(row)
        except(ValueError,KeyError)as exc:pending.append(dict(plan_node=cap.get('node_id'),plan_edge=cap.get('edge_id'),reason=str(exc)))
    require(len({r['plan_edge_id']for r in out})==len({r['axis_edge_id']for r in out})==len(out),'competing capped branch correspondence')
    return out,pending

def qualify(row,graphs,docs,hashes,reader):
    inventory=dict(mode='native_capped_branch_annotation_witness_v1',source_sha256=hashes['plan']['source'],graph_sha256=hashes['plan']['graph'],records=[row['plan_cap']],graph_mutated=False,connections_added=0,physical_lengths_assigned=0)
    private,role=apply_plan_roles(graphs['plan'],inventory,hashes['plan']['graph'],hashlib.sha256(encode(inventory)).hexdigest())
    node=next(n for n in private['nodes']if n['node_id']==row['plan_cap']['node_id']);require(node['subtype']=='source_declared_capped_branch_interface','original source role owner did not qualify')
    node['subtype']='external_system_interface' # Private schema adapter for the unchanged outward reader only.
    routes={v:outward(private if v=='plan'else graphs[v],row[v+'_anchor'if v=='plan'else'axis_anchor'],set(row['blocked'][v]),row['system'],row['floor'])for v in graphs}
    require(routes['plan']['terminal_id']==row['plan_cap']['node_id']and routes['iso']['terminal_id']==row['axis_cap_port']['node_id'],'native branch terminates at another source scope')
    require(routes['plan']['edges']==[row['plan_edge_id']]and routes['iso']['edges']==[row['axis_edge_id']],'capped correspondence cannot skip intermediate edges')
    marker=marker_ports(docs['iso'],graphs['iso'],routes['iso']['terminal_id'],hashes['iso']['source'],hashes['iso']['graph'])
    ports=[p for p in marker['records']if p['edge_id']==row['axis_edge_id']and p['system']==row['system']]
    require(len(ports)==1 and ports[0]['port_id']==row['axis_cap_port']['port_id'],'independent native marker port differs')
    checks={}
    for v in graphs:
        edge=row['plan_edge_id'if v=='plan'else'axis_edge_id'];anchor=row['plan_anchor'if v=='plan'else'axis_anchor'];h=hashes[v]
        path=plan_coverage(docs[v],graphs[v],edge,anchor,h['source'],h['graph'],reader)if v=='plan'else axis_coverage(docs[v],graphs[v],[edge],h['source'],h['graph'])
        for item in path['edges']:
            for seg in item['segments']:
                if v=='iso'and seg['index']==ports[0]['display_segment_index']:continue
                require(seg['status']=='single_source_line_covers','capped branch native source coverage is not unique')
        checks[v]=dict(native_T=(reader if v=='plan'else native_tee)(docs[v],graphs[v],anchor,h['source'],h['graph']),native_path=path,snapshot=branch_snapshot(graphs[v],[edge]))
    return dict(row,routes=routes,native_checks=checks,original_source_cap_role=role,axis_drawing_port=ports[0],
        temporary_plan_role_projection=dict(node_id=node['node_id'],original_role='source_declared_capped_branch_interface',reader_role='external_system_interface',source_graph_mutated=False),
        scope='native_capped_third_arm_drawing_correspondence_only',other_system_port_assigned=False,remote_equipment_identity_assigned=False,
        whole_axis_DN_selected=False,whole_axis_physical_length_mm=None,vertical_values_assigned=0,human_accepted=False)

def compute(manifest):
    inputs=manifest['inputs']
    def checked():require(all(sha(v['path'])==v['sha256']for v in inputs.values()),'capped correspondence input changed')
    checked();discovery=verify_plan_caps(Path(inputs['plan_discovery']['path']).parent);axis_caps=verify_axis_caps(Path(inputs['axis_caps']['path']).parent)
    provider=load(inputs['provider']['path']);axis=load(inputs['axis_graph']['path']);config=load(inputs['current_T_source_config']['path']);records=[];pending=[]
    require(axis_caps['source_sha256']==inputs['axis_source']['sha256']and axis_caps['graph_sha256']==inputs['axis_graph']['sha256'],'axis capped marker proof has another source scope')
    require(provider['inputs']['axis_graph']==inputs['axis_graph'],'provider axis namespace differs')
    views={r['id']:r['inputs']for r in discovery['inputs']};axis_doc,axis_preflight=read_source(inputs['axis_source']['path']);preflight=dict(iso=axis_preflight)
    for floor,view in sorted(discovery['views'].items()):
        if floor=='axis'or not view['selections']:continue
        require(provider['inputs']['plan_graph_'+floor]==views[floor]['graph']and provider['inputs']['plan_source_'+floor]==views[floor]['source'],'current provider and native cap plan differ')
        graph=load(views[floor]['graph']['path']);doc,preflight[floor]=read_source(views[floor]['source']['path']);graphs=dict(plan=graph,iso=axis)
        hashes=dict(plan=dict(source=views[floor]['source']['sha256'],graph=views[floor]['graph']['sha256']),iso=dict(source=inputs['axis_source']['sha256'],graph=inputs['axis_graph']['sha256']))
        reader=current_plan_reader(config,hashes['plan']['source'],hashes['plan']['graph']);proposed,held=candidates(provider,graphs,view['source_inventory']['records'],axis_caps['records']);pending.extend(held)
        for row in proposed:
            try:records.append(qualify(row,graphs,dict(plan=doc,iso=axis_doc),hashes,reader))
            except ValueError as exc:pending.append(dict(mapping_id=row['mapping_id'],axis_edge_id=row['axis_edge_id'],reason=str(exc)))
    checked()
    return dict(mode=MODE,inputs=copy.deepcopy(inputs),records=records,pending=pending,source_preflight=preflight,
        all_native_cap_discovery_views_replayed=True,all_separate_axis_cap_ports_replayed=True,original_T_outward_role_path_and_marker_owners_reused=True,
        counts=dict(new_drawing_correspondences=len(records),pending=len(pending)),graph_mutated=False,old_providers_replaced=False,
        other_system_ports_assigned=0,remote_equipment_identities_assigned=0,physical_lengths_assigned=0,whole_axis_DN_assigned=0,vertical_values_assigned=0,human_accepted=False,whole_goal_complete=False)

def implementations():
    names=('batch_discover_capped_annotations','discover_native_capped_annotations','native_capped_branch_annotations','native_capped_marker_port_context','source_capped_branch_roles','ordered_anchor_branch_paths','current_plan_crossover_path_reapplication','native_drawing_marker_ports','crossview_equipment_branch_inventory','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest,output):
    output=Path(output);require(not output.exists(),'fresh capped correspondence output required');code=implementations();result=compute(load(manifest));require(code==implementations(),'native capped correspondence implementation changed')
    output.mkdir(parents=True);target=output/'capped-branch-correspondence.json';target.write_bytes(encode(result));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(target))))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');require(receipt['mode']==MODE and receipt['implementation_sha256']==implementations()and sha(receipt['manifest']['path'])==receipt['manifest']['sha256']and sha(output/'capped-branch-correspondence.json')==receipt['output_sha256'],'capped correspondence receipt changed')
    fresh=compute(load(receipt['manifest']['path']));require(encode(fresh)==(output/'capped-branch-correspondence.json').read_bytes(),'native capped correspondence independent replay differs');return fresh

def main():
    p=argparse.ArgumentParser()
    for n in ['manifest','output','verify-output']:p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):r=verify_output(a.verify_output)if a.verify_output else produce(a.manifest,a.output)
    print(dict(mode=MODE,counts=r['counts']),flush=True)
if __name__=='__main__':main()
