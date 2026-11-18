"""Apply explicit, graph-pinned human equipment-interface confirmations."""
import argparse, collections, copy, hashlib, json, math, shutil, subprocess, sys
from pathlib import Path
from edge_endpoint_semantics import reconcile
from source_readability import read_source
from source_terminal_pair_inventory import scan

def apply(graph, policy, inventory, source_hash, graph_hash):
    if policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash or graph.get('metadata',{}).get('source_sha256') != source_hash: raise ValueError('source or graph identity mismatch')
    if inventory.get('source_sha256') != source_hash or inventory.get('graph_sha256') != graph_hash: raise ValueError('inventory identity mismatch')
    confirmation=policy.get('confirmation',{})
    if confirmation.get('confirmed_by') != 'user' or not confirmation.get('question') or not confirmation.get('answer'): raise ValueError('explicit user confirmation required')
    rows=policy.get('connections')
    if not isinstance(rows,list) or not rows: raise ValueError('no confirmed connections')
    out=copy.deepcopy(graph); nodes={n['node_id']:n for n in out['nodes']}; edges={e['edge_id']:e for e in out['edges']}
    if len(nodes)!=len(out['nodes']) or len(edges)!=len(out['edges']): raise ValueError('duplicate IDs')
    counts=collections.Counter(n for e in out['edges'] for n in (e.get('start_node_id'),e.get('end_node_id')) if n)
    selected=set(); selected_edges=set(); device_system=set(); mappings=[]
    for row in rows:
        nid=row['interface_id']; eid=row['edge_id']; did=row['equipment_id']; system=row['system']
        if nid in selected or eid in selected_edges or (did,system) in device_system: raise ValueError('duplicate interface, edge or equipment system')
        n=nodes.get(nid); e=edges.get(eid); device=nodes.get(did)
        if not n or n.get('node_type')!='virtual_equipment' or n.get('subtype')!='out_of_plane_interface' or n.get('system')!=system or n.get('source_handle')!=row['interface_handle'] or counts[nid]!=1: raise ValueError('interface identity or degree mismatch')
        if not device or device.get('node_type')!='equipment' or device.get('source_handle')!=row['equipment_handle'] or device.get('floor')!=n.get('floor'): raise ValueError('equipment identity mismatch')
        if not e or e.get('system')!=system or (e.get('start_node_id')==nid)+(e.get('end_node_id')==nid)!=1: raise ValueError('edge ownership or system mismatch')
        if any(x.get('node_id')==nid for x in out.get('sourceTerminalGlyphs',[])): raise ValueError('source glyph requires explicit migration')
        side='start' if e['start_node_id']==nid else 'end'
        port=e.get(side+'_port_id'); ports=n.get('ports',[])
        if len(ports)!=1 or ports[0].get('port_id')!=port or ports[0].get('system')!=system: raise ValueError('interface port mismatch')
        point=e.get('path',[])[0 if side=='start' else -1]
        if math.dist(point,(n['x'],n['y']))>.05: raise ValueError('source path does not reach original interface')
        if not any(x.get('node_id')==did and x.get('source_handle')==row['equipment_handle'] for x in inventory.get('equipment',[])): raise ValueError('equipment absent from source inventory')
        original=copy.deepcopy(n)
        e[side+'_node_id']=did; e.pop(side+'_port_id',None)
        e['confirmed_equipment_interface']={'original_interface':original,'interface_side':side,'confirmation':copy.deepcopy(confirmation),'source_sha256':source_hash,'input_graph_sha256':graph_hash,'physical_port_verified':False,'interface_to_equipment_length_known':False,'scope':'Logical equipment ownership; pipe path stops at source interface.'}
        e['drawing_path_length']=e.get('path_length');e['path_length_complete']=False;e['physical_length_status']='unknown_interface_to_equipment_length';e['path_length_scope']='source_drawn_pipe_only'
        selected.add(nid);selected_edges.add(eid);device_system.add((did,system));mappings.append({'retired_node_id':nid,'equipment_id':did,'edge_id':eid,'system':system,'source_handles':n['source_handles']})
    for did in {r['equipment_id'] for r in rows}:
        systems={r['system'] for r in rows if r['equipment_id']==did}
        if systems!={'supply','return'}: raise ValueError('confirmed equipment must have separate supply and return bindings')
        nodes[did]['connection_status']='confirmed_interfaces_physical_ports_unresolved'
        nodes[did]['confirmed_interface_ids']=[r['interface_id'] for r in rows if r['equipment_id']==did]
    out['nodes']=[n for n in out['nodes'] if n['node_id'] not in selected]
    out['virtual_equipment_ports']=[p for p in out.get('virtual_equipment_ports',[]) if p.get('virtual_equipment_id') not in selected]
    out,changes=reconcile(out)
    out['confirmedEquipmentInterfaceRepair']={'source_sha256':source_hash,'input_graph_sha256':graph_hash,'confirmation':confirmation,'mappings':mappings,'supply_return_independent':True,'physical_ports_verified':False,'physical_lengths_complete':False,'review_status':'unreviewed_after_semantic_change'}
    if graph.get('confirmedEquipmentInterfaceRepair'):
        out['confirmedEquipmentInterfaceRepair']['previous_repair']=copy.deepcopy(graph['confirmedEquipmentInterfaceRepair'])
    out['preHilComparison']={'status':'pending','previous_comparison':copy.deepcopy(graph.get('preHilComparison')),'reason':'equipment endpoint semantics changed; source comparison and graph-bound reviews must be repeated'}
    out['metadata'].update(hil_ready=False,graph_complete=False,review_status='unreviewed_after_semantic_change',equipment_interface_status='user_confirmed_selected_interfaces_only')
    return out, {'mappings':mappings,'endpoint_type_changes':changes,'human_review':'unreviewed_after_semantic_change','hil_ready':False}

def prepare_direct_dn_recheck(prior, updated, policy_bytes, source_hash, old_hash, new_hash):
    """Permit a fresh source rescan only if all existing edge geometry is unchanged."""
    policy=json.loads(policy_bytes)
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=old_hash: raise ValueError('direct DN policy source or graph mismatch')
    if not isinstance(policy.get('text_layers'),list) or not policy['text_layers'] or any(not isinstance(x,str) or not x for x in policy['text_layers']): raise ValueError('invalid DN text layers')
    old={e['edge_id']:e for e in prior['edges']};new={e['edge_id']:e for e in updated['edges']}
    if len(old)!=len(prior['edges']) or len(new)!=len(updated['edges']) or old.keys()!=new.keys(): raise ValueError('edge set changed')
    immutable=('system','path','path_points','attribute_paths','source_handles','source_insert_handle','start_floor','end_floor')
    if any(any(a.get(k)!=new[i].get(k) for k in immutable) for i,a in old.items()): raise ValueError('edge source geometry or system changed')
    selections=policy.get('selections')
    if not isinstance(selections,list) or not selections or any(r.get('edge_id') not in new for r in selections): raise ValueError('invalid direct DN selections')
    result=copy.deepcopy(policy);result['graph_sha256']=new_hash
    result['rechecked_from_policy_sha256']=hashlib.sha256(policy_bytes).hexdigest();result['prior_graph_sha256']=old_hash
    return result

def main():
    p=argparse.ArgumentParser()
    for k in ('source','graph','devices','policy','inventory-policy','output'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--direct-dn-policy',type=Path)
    a=p.parse_args()
    if a.output.exists(): raise ValueError('refusing to overwrite output')
    source,proof=read_source(a.source); gb=a.graph.read_bytes();pb=a.policy.read_bytes();ib=a.inventory_policy.read_bytes(); sha=lambda b:hashlib.sha256(b).hexdigest()
    graph=json.loads(gb);policy=json.loads(pb);inventory=scan(source,graph,json.loads(ib),proof['source_sha256'],sha(gb))
    result,audit=apply(graph,policy,inventory,proof['source_sha256'],sha(gb))
    a.output.mkdir(parents=True)
    dest=a.output/'graph_with_confirmed_interfaces.json';dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
    if a.direct_dn_policy:
        old_policy=a.direct_dn_policy.read_bytes();new_hash=sha(dest.read_bytes())
        dn_policy=prepare_direct_dn_recheck(graph,result,old_policy,proof['source_sha256'],sha(gb),new_hash)
        dn_policy_path=a.output/'direct_dn_recheck_policy.json';dn_policy_path.write_text(json.dumps(dn_policy,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        dn_output=a.output/'source-direct-dn-candidates.json';risk_output=a.output/'source-dn-annotation-risks.json'
        subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).with_name('source_direct_dn_evidence.py')),'--source',str(a.source),'--graph',str(dest),'--policy',str(dn_policy_path),'--output',str(dn_output)],check=True)
        cmd=[sys.executable,'-X','utf8',str(Path(__file__).with_name('source_dn_annotation_risks.py')),'--source',str(a.source),'--graph',str(dest),'--output',str(risk_output)]
        for layer in dn_policy['text_layers']:cmd.extend(['--text-layer',layer])
        subprocess.run(cmd,check=True)
        audit['direct_dn_recheck']={'status':'source_candidate_not_accepted','policy_sha256':sha(dn_policy_path.read_bytes()),'candidates_sha256':sha(dn_output.read_bytes()),'risk_report_sha256':sha(risk_output.read_bytes()),'graph_sha256':new_hash}
    audit.update(input_graph_sha256=sha(gb),output_graph_sha256=sha(dest.read_bytes()),source_sha256=proof['source_sha256'],policy_sha256=sha(pb),inventory_policy_sha256=sha(ib),component_table_sha256=sha(a.devices.read_bytes()),source_preflight=proof)
    (a.output/'confirmed-interface-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'connections':len(audit['mappings']),'output_sha256':audit['output_graph_sha256'],'hil_ready':False}))
if __name__=='__main__':main()
