"""Requalify existing outer T roles after an independently proved bend merge."""
import math
from confirm_crossview_paths import load,sha,encode
from legacy_named_provider_inventory import require,current_plan_reader
from crossview_equipment_branch_inventory import native_tee
from source_readability import read_source

def same_roles(before,after,aliases):
    require(len(before['junctions'])==len(after['junctions'])==1,'one existing junction required')
    a,b=before['junctions'][0],after['junctions'][0]
    require(a['node_id']==b['node_id']and a['system']==b['system']and math.dist(a['position'],b['position'])<=.05,'existing junction identity changed')
    old={aliases.get(r['edge_id'],r['edge_id']):r for r in a['source_rays']};new={r['edge_id']:r for r in b['source_rays']}
    require(len(old)==len(new)==3 and old.keys()==new.keys(),'existing three-arm roles lost during two-arm normalization')
    for eid,x in old.items():
        y=new[eid];require(x.get('source_line_handle')and x['source_line_handle']==y.get('source_line_handle'),'existing T ray changed native LINE')
        u,v=x['direction'],y['direction'];nu,nv=math.hypot(*u),math.hypot(*v)
        require(nu>0 and nv>0 and all(math.isfinite(z)for z in u+v)and math.dist([z/nu for z in u],[z/nv for z in v])<=1e-8,'existing T ray direction changed')
    return dict(node_id=a['node_id'],same_system=True,original_and_current_rays_equal_after_explicit_edge_aliases=True,physical_Ts_added=0)

def junction(doc,graph,nid,source_hash,graph_hash,config):
    waves=[r for r in graph.get('sourceWaveMainCohort',{}).get('records',[])if r['tee_id']==nid]
    if waves:
        require(len(waves)==1,'affected wave junction owner is ambiguous')
        from rebuild_wave_cohort_crossview_batch import wave_branch
        row=waves[0];return wave_branch(doc,graph,row['equipment_id'],row['system'],source_hash,graph_hash)['junction_evidence']
    return current_plan_reader(config,source_hash,graph_hash)(doc,graph,nid,source_hash,graph_hash)

def replay(proof,outputs):
    inputs=proof['inputs'];config=load(inputs['current_T_source_config']['path']);records=[]
    for f,floor in proof['floors'].items():
        aliases=floor['proof']['edge_aliases']
        if not aliases:continue
        ss,gs=inputs['plan_source_'+f],inputs['plan_graph_'+f]
        require(sha(ss['path'])==ss['sha256']and sha(gs['path'])==gs['sha256'],'affected junction source parent changed')
        old=load(gs['path']);new=outputs[f][0];old_edges={e['edge_id']:e for e in old['edges']};new_nodes={n['node_id']:n for n in new['nodes']};old_nodes={n['node_id']:n for n in old['nodes']}
        import hashlib
        gh=hashlib.sha256(encode(new)).hexdigest();require(gh==floor['reading_graph_sha256'],'affected junction uses another reconstructed graph')
        doc,preflight=read_source(ss['path']);affected=sorted({old_edges[eid][side]for eid in aliases for side in('start_node_id','end_node_id')}&new_nodes.keys())
        for nid in affected:
            require(old_nodes[nid]==new_nodes[nid],'two-arm merge changed an existing outer T node')
            before=junction(doc,old,nid,ss['sha256'],gs['sha256'],config);after=junction(doc,new,nid,ss['sha256'],gh,config)
            records.append(dict(floor=int(f),**same_roles(before,after,aliases),before=before,after=after,edge_aliases=aliases))
        require(sha(ss['path'])==ss['sha256'],'affected junction native source changed during reading')
    return dict(status='existing_affected_Ts_native_roles_requalified',records=records,count=len(records),physical_Ts_added=0,human_accepted=False)
