"""Re-enter graph construction for source-reviewed rims before downstream attributes."""
import argparse,csv,hashlib,json
from pathlib import Path
from source_readability import read_source
from source_reviewed_circle_connections import load_review
from source_circle_rim_tee_screen import scan
from repair_confirmed_circle_junctions import apply,sha

def main():
 p=argparse.ArgumentParser()
 for key in ('source','graph','devices','policy','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args()
 if a.output.exists():raise ValueError('output already exists')
 policy=json.loads(a.policy.read_text(encoding='utf8'));doc,proof=read_source(a.source);source_hash=proof['source_sha256'];graph_hash=sha(a.graph)
 if policy.get('input_graph_sha256')!=graph_hash or policy.get('devices_sha256')!=sha(a.devices):raise ValueError('input graph or components stale')
 reviewed=load_review(policy,source_hash);g=json.loads(a.graph.read_text(encoding='utf8'))
 screen=scan(doc,g,{'source_sha256':source_hash,'graph_sha256':graph_hash,'circle_radius':policy['circle_radius'],'z_tolerance':.05},source_hash,graph_hash)
 screen_bytes=(json.dumps(screen,ensure_ascii=False,indent=2)+'\n').encode('utf8');screen_hash=hashlib.sha256(screen_bytes).hexdigest()
 with a.devices.open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
 selection=dict(policy,screen_sha256=screen_hash,circle_handles=sorted(reviewed))
 out,rows,audit=apply(doc,g,rows,screen,selection,source_hash,graph_hash,screen_hash,source_review_policy=policy)
 a.output.mkdir(parents=True)
 target=a.output/'graph_with_source_reviewed_circles.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (a.output/'input-circle-screen.json').write_bytes(screen_bytes)
 with (a.output/'assigned_edge_device_instances.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 audit.update(source_sha256=source_hash,input_graph_sha256=graph_hash,output_graph_sha256=sha(target),policy_sha256=sha(a.policy),screen_sha256=screen_hash,script_sha256=sha(__file__),source_preflight=proof,review_kind='technical_native_source_comparison',human_accepted=False)
 (a.output/'source-reviewed-circle-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'connections':len(audit['records']),'graph_sha256':sha(target),'human_accepted':False}))
if __name__=='__main__':main()
