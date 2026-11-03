"""Compose immutable task graphs. Proposed links never count as proven physical pipe."""
import argparse, copy, csv, hashlib, json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(config):
    nodes=[]; edges=[]; sources=[]; ports={}; rows=[]
    for task in config['tasks']:
        tid=task['task_id']; p=Path(task['graph']); g=load(p)
        if sha(p)!=task['graph_sha256']: raise ValueError('Source graph changed: '+tid)
        nm={}
        for original in g['nodes']:
            n=copy.deepcopy(original); oid=n['node_id']; q=tid+'::'+oid
            n.update(node_id=q,source_task_id=tid,source_node_id=oid)
            n['source_ports']=copy.deepcopy(n.get('ports',[])); n.pop('ports',None)
            if original.get('node_type')=='virtual_equipment' and original.get('ports'):
                for pp in original['ports']:
                    pn=copy.deepcopy(n); pid=pp['port_id']; pn.update(node_id=tid+'::'+pid,source_port_id=pid,source_owner_node_id=oid,system=pp['system'],x=pp['x'],y=pp['y'])
                    nodes.append(pn); ports[tid+'::'+pid]=pn; nm[(oid,pid)]=pn['node_id']
            else:
                nodes.append(n); nm[(oid,None)]=q
        for original in g['edges']:
            e=copy.deepcopy(original); e.update(edge_id=tid+'::'+original['edge_id'],source_task_id=tid,source_edge_id=original['edge_id'])
            for side in ['start','end']:
                oid=original[side+'_node_id']; pid=original.get(side+'_port_id'); key=(oid,pid) if (oid,pid)in nm else(oid,None)
                if key not in nm:
                    matches=[v for(k,p),v in nm.items()if k==oid and next(n for n in nodes if n['node_id']==v).get('system')==e['system']]
                    if len(matches)!=1: raise ValueError('Ambiguous virtual port: '+str((tid,original['edge_id'],oid,pid)))
                    e[side+'_node_id']=matches[0]
                else:e[side+'_node_id']=nm[key]
            edges.append(e)
        with Path(task['devices']).open(encoding='utf-8-sig') as stream:
            device_rows=list(csv.DictReader(stream))
        for row in device_rows:
            r=dict(row);r.update(source_task_id=tid,source_edge_id=row.get('edge_id',''),edge_id=tid+'::'+row['edge_id'] if row.get('edge_id')else'',source_device_name=row.get('device_name',''),device_name=tid+'::'+row.get('device_name',''));rows.append(r)
        sources.append(dict(task_id=tid,graph_sha256=sha(p),devices_sha256=sha(task['devices']),graph=task['graph'],scope=task['scope']))
    used=set();links=[]
    for i,m in enumerate(config['links'],1):
        a=ports[m['from']];b=ports[m['to']]
        if a['system']!=b['system']:raise ValueError('Cross-system link rejected')
        if m['from']in used or m['to']in used:raise ValueError('Port used twice')
        used.update([m['from'],m['to']]);lid='LINK-'+str(i).zfill(2)
        links.append(dict(edge_id=lid,start_node_id=m['from'],end_node_id=m['to'],system=a['system'],edge_type='logical_cross_drawing_link',connection_mode='proposed_interface_mapping',verification_status='pending_exact_port_correspondence',evidence=m['evidence'],physical_length_verified=False,path_length=None,attribute_paths=[],source_handles=[],equipment_inventory=[],source_task_id='aggregate',source_edge_id=lid))
    ids={n['node_id']for n in nodes};assert len(ids)==len(nodes)
    assert all(e['start_node_id']in ids and e['end_node_id']in ids for e in edges+links)
    return dict(metadata=dict(project_id=config['project_id'],kind='derived_calculation_aggregate',review_inherited=False,solver_ready=False,default_include_proposed_links=False,source_graphs_immutable=True),nodes=nodes,edges=edges,proposed_links=links,sources=sources,reference_only=config.get('reference_only',[]),instances=rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=False);g=build(load(a.config))
    (out/'graph.json').write_text(json.dumps(g,ensure_ascii=False,indent=2),encoding='utf8')
    for key in ['nodes','edges','proposed_links','instances','sources']:
        (out/(key+'.json')).write_text(json.dumps(g[key],ensure_ascii=False,indent=2),encoding='utf8')
    (out/'validation.json').write_text(json.dumps(dict(nodes=len(g['nodes']),source_edges=len(g['edges']),proposed_links=len(g['proposed_links']),components=len(g['instances']),duplicate_terminal_networks=0,source_hashes_verified=True,supply_return_ports_separated=True,review_confirmation=None),indent=2),encoding='utf8')
if __name__=='__main__':main()
