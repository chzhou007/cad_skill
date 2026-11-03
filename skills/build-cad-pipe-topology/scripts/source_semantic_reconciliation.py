"""Source-backed semantic enrichment; assembly candidates never create hydraulic links."""
import copy, hashlib, json
from pathlib import Path

VERSION='1.13.0'
def reconcile(graph, evidence):
    g=copy.deepcopy(graph);nodes={n['node_id']:n for n in g['nodes']}
    edges={e['edge_id']:e for e in g['edges']};bindings=[];groups=[]
    for n in nodes.values():
        if n.get('boundary_type')=='unresolved_source_terminal':
            n['resolution_state']='algorithm_pending'
            n['review_queue']='source_comparison'
    for item in evidence.get('interface_bindings',[]):
        a=item['annotation']
        if not a.get('handle') or not item.get('leader_handles'):raise ValueError('Missing native label/leader evidence')
        for hit in item['terminal_contacts']:
            n=nodes[hit['node_id']];p=hit['leader_endpoint']
            if ((n['x']-p[0])**2+(n['y']-p[1])**2)**.5>evidence.get('contact_tolerance',.5):raise ValueError('Leader does not contact node')
            text=a['text'];kind='plate_heat_exchanger_container' if '板换集装箱'in text else 'drain_interface' if '排水管'in text else 'makeup_water_interface' if '补水管'in text else 'source_named_interface'
            n.update(boundary_type='source_named_external_interface',subtype=kind,label=text,
                     resolution_state='destination_known_remote_port_pending',review_queue='identity_completion')
            n['interface_destination']={'text':text,'kind':kind,'remote_port_confirmed':False,'source_label_handle':a['handle'],'source_leader_handles':item['leader_handles']}
            for port in n.get('ports',[]):port['destination']=copy.deepcopy(n['interface_destination'])
            bindings.append(n['node_id'])
    for c in evidence.get('circle_groups',[]):
        if not c.get('pairs'):continue
        ids=sorted(set(c['center_nodes']+c['rim_nodes']))
        for nid in ids:
            if nid not in nodes:raise ValueError('Unknown assembly member')
        cross=any(not p['same_system']for p in c['pairs'])
        gid='SRC-CIRCLE-'+c['circle']['handle']
        groups.append({'assembly_id':gid,'kind':'source_symbol_candidate','physical_equipment':False,
                       'member_node_ids':ids,'source_handles':[c['circle']['handle']],
                       'geometry':c['circle'],'status':'cross_system_tangency_excluded'if cross else 'symbol_role_calibration_pending',
                       'hydraulic_merge_applied':False})
        for nid in ids:nodes[nid].setdefault('source_assembly_candidates',[]).append(gid)
    # Importer renames blocks. Only audited original->imported identities qualify;
    # a prefix or similar block name is insufficient proof.
    aliases={}
    for a in evidence.get('imported_blocks',[]):
        if not a.get('reference_handle')or not a.get('normalized_handle'):raise ValueError('Untraced imported block')
        aliases[a['actual_block_name']]=evidence['configured_imported_block']
    g['sourceAssemblies']=groups
    g.setdefault('metadata',{}).update(semantic_reconciliation_version=VERSION,
        stage_status='source_comparison_in_progress',hil_ready=False,
        hil_block_reason='Resolve repeated source symbol roles before expert HIL; see source-comparison.json')
    return g,{'version':VERSION,'known_destination_nodes':sorted(set(bindings)),
              'assembly_candidates':len(groups),'block_aliases':aliases,
              'hydraulic_connectivity_changed':False,'equipment_nodes_fabricated':0}

def resolve_profile_aliases(profile, audit):
    p=copy.deepcopy(profile)
    for imported,original in audit['block_aliases'].items():
        if original not in p['inline_types']:raise ValueError('Unknown original symbol identity')
        verified=original in audit.get('verified_engineering_roles',[])
        p['inline_types'][imported]=copy.deepcopy(p['inline_types'][original]) if verified else ['Native Source Symbol (role pending)','SRC']
        if verified and original in p.get('inline_bridge_blocks',[])and imported not in p['inline_bridge_blocks']:p['inline_bridge_blocks'].append(imported)
        if not verified:p.setdefault('unverified_import_symbol_roles',[]).append(imported)
    p['import_alias_provenance']=audit['block_aliases'];return p
