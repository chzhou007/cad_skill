"""Attach source-backed unpaired wave marks to edges without asserting a route."""
import argparse,copy,hashlib,json,math,shutil
from pathlib import Path
from source_readability import read_source
from wave_omission_candidates import screen

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def attach(doc,graph,policy):
 g=copy.deepcopy(graph)
 if g.get('unpairedWaveEvidence'):raise ValueError('unpaired wave stage already present')
 result=screen(doc,g,block_name=policy['block_name'],expected_fingerprint=policy['block_fingerprint'],max_gap=policy['max_gap'],contact_tolerance=policy['contact_tolerance'])
 rows={r['node_id']:r for r in result['wave_endpoints']}; paired={p[x] for p in result['candidate_pairs'] for x in ('a','b')}
 nodes={n['node_id']:n for n in g['nodes']};edges={e['edge_id']:e for e in g['edges']};selected=policy['endpoints'];ids=[x['node_id'] for x in selected]
 if not ids or len(ids)!=len(set(ids)) or any(n in paired or n not in rows for n in ids):raise ValueError('scope contains paired, ambiguous or missing endpoint')
 evidence=[]
 for spec in selected:
  row=rows[spec['node_id']];n=nodes[row['node_id']];e=edges[row['edge_id']]
  if row['wave_handle']!=spec['wave_handle'] or e.get('source_wave_terminal'):raise ValueError('wave handle mismatch or existing evidence')
  hits=[];layer=policy['source_layer_by_system'][n['system']]
  for h in n.get('source_handles',[]):
   source=doc.entitydb.get(h)
   if source is not None and source.dxftype()=='LINE' and source.dxf.layer==layer and h in e.get('source_handles',[]):
    if min(math.dist((p.x,p.y),row['xy']) for p in (source.dxf.start,source.dxf.end))<=policy['contact_tolerance']:hits.append(h)
  if len(hits)!=1:raise ValueError('source pipe contact missing or ambiguous')
  item={'source_wave_handle':row['wave_handle'],'source_block_name':policy['block_name'],
        'source_pipe_handle':hits[0],'source_endpoint':row['xy'],'endpoint_node_id':row['node_id'],
        'source_sha256':policy['source_sha256'],'destination':'unknown',
        'paired_continuation':'not_established','physical_length':'unknown','human_instance_reviewed':False}
  e['source_wave_terminal']=item;evidence.append({'edge_id':e['edge_id'],**item})
 g['unpairedWaveEvidence']={'source_sha256':policy['source_sha256'],'input_graph_sha256':policy['graph_sha256'],
  'changes':evidence,'scope':'edge source mark only; endpoint and remote destination unresolved','hil_ready':False}
 g.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False)
 return g,evidence

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();policy=json.loads(a.policy.read_text(encoding='utf8'))
 for key,path in [('source_sha256',a.source),('graph_sha256',a.graph),('devices_sha256',a.devices)]:
  if sha(path)!=policy[key]:raise ValueError(key+' mismatch')
 doc,_=read_source(a.source);g,evidence=attach(doc,json.loads(a.graph.read_text(encoding='utf8')),policy)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);out=a.output/'graph_with_wave_evidence.json';out.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 (a.output/'audit.json').write_text(json.dumps({'source_sha256':policy['source_sha256'],'input_graph_sha256':policy['graph_sha256'],'output_graph_sha256':sha(out),'changes':evidence,'graph_connectivity_changed':False,'human_acceptance':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'edge_marks':len(evidence),'graph_connectivity_changed':False,'hil_ready':False}))
if __name__=='__main__':main()
