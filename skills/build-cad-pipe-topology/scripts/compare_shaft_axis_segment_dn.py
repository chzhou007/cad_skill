"""Compare candidate shaft chains and local DN evidence, without mapping pipes."""
import argparse,hashlib,json
from pathlib import Path

def compare(chains,dn,bulk,axis_hash,ambiguous_handles=()):
 if (chains.get('status')!='shaft_axis_candidate_inventory_not_mapping' or chains.get('input_sha256',{}).get('axis_graph')!=axis_hash or chains.get('mapping_ready') is not False or chains.get('human_accepted') is not False or chains.get('hil_ready') is not False or dn.get('status')!='segment_candidates_not_accepted' or dn.get('graph_sha256')!=axis_hash or bulk.get('graph_sha256')!=axis_hash or bulk.get('source_sha256')!=dn.get('source_sha256')):raise ValueError('stale or promoted input')
 bulk_by={x['text_handle']:x for x in bulk['records']}
 if len(bulk_by)!=len(bulk['records']):raise ValueError('duplicate bulk text handle')
 records=[]
 for row in chains['records']:
  if row.get('mapping_ready') is not False or row.get('system') not in ('supply','return'):raise ValueError('invalid chain status')
  for chain in row['axis_chain_candidates']:
   edge_ids=[chain['axis_1_to_2_edge'],chain['axis_2_to_3_edge']];selected=[]
   for x in dn['observations']:
    if x['edge_id'] not in edge_ids:continue
    h=x['source_text']['handle'];seen=bulk_by.get(h)
    if not seen or seen.get('status')!='unique_source_line_and_graph_segment_candidate' or seen.get('system')!=row['system'] or x['edge_id'] not in [e['edge_id'] for e in seen['edge_candidates']]:raise ValueError('DN evidence lacks matching bulk screen')
    selected.append({'edge_id':x['edge_id'],'segment_index':x['segment_index'],'source_line_handle':x['source_line_handle'],'source_text_handle':h,'nominal_mm_candidate':x['nominal_mm_candidate'],'status':'local_source_candidate_not_accepted'})
   records.append({'system':row['system'],'plan_floor_nodes':row['plan_floor_nodes'],'axis_edge_ids':edge_ids,'segment_dn_candidates':selected,'mapping_ready':False,'physical_diameter_selected':False})
 unresolved=[]
 if len(set(ambiguous_handles))!=len(ambiguous_handles):raise ValueError('duplicate ambiguous text')
 for h in ambiguous_handles:
  x=bulk_by.get(h)
  if not x or x.get('status')!='ambiguous_source_lines':raise ValueError('ambiguous text changed')
  unresolved.append({'text_handle':h,'text':x['text'],'status':x['status']})
 return {'status':'local_dn_comparison_not_shaft_mapping','records':records,'unresolved_texts':unresolved,'graph_mutated':False,'mapping_ready':False,'human_accepted':False,'hil_ready':False,'limitations':['Local DN candidates are not whole-edge diameters or confirmed reducer locations.','Same-system values do not establish shaft membership or cross-view correspondence.','Only supplied candidate chains and explicitly selected ambiguous texts are included.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('chains','dn','bulk','axis-graph','output'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--ambiguous-handle',action='append',default=[]);a=p.parse_args();h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));r=compare(load(a.chains),load(a.dn),load(a.bulk),h(a.axis_graph),a.ambiguous_handle);r.update(input_sha256={k:h(getattr(a,k)) for k in ('chains','dn','bulk','axis_graph')},script_sha256=h(Path(__file__)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'status':r['status'],'chains':len(r['records'])}))
if __name__=='__main__':main()
