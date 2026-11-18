"""Attach strictly witnessed segment dimensions to an eligible final plan graph."""
import argparse,hashlib,json,shutil
from pathlib import Path
from source_readability import read_source
from attach_source_segment_dimensions import collect,attach

def apply(doc,graph,policy,source_hash,graph_hash):
 if graph.get('sourceSegmentDimensions') or any(e.get('source_dimensioned_segments') for e in graph['edges']):raise ValueError('existing dimension evidence requires reconciliation')
 if any('diameter' in k.lower() for k in graph) or any(any('diameter' in k.lower() for k in e) for e in graph['edges']):raise ValueError('existing DN evidence requires explicit recheck before attachment')
 observations=collect(doc,graph,policy,source_hash,graph_hash)
 return attach(graph,observations,source_hash,graph_hash),observations

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','devices','policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 if a.output.exists():raise FileExistsError(a.output)
 doc,proof=read_source(a.source);g=json.loads(a.graph.read_text(encoding='utf8'));policy=json.loads(a.policy.read_text(encoding='utf8'));out,rows=apply(doc,g,policy,proof['source_sha256'],sha(a.graph));a.output.mkdir(parents=True);gp=a.output/'graph_with_source_segment_dimensions.json';gp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 audit={'status':'source_segment_dimensions_pending_review','source_sha256':proof['source_sha256'],'input_graph_sha256':sha(a.graph),'output_graph_sha256':sha(gp),'devices_sha256':sha(a.devices),'policy_sha256':sha(a.policy),'script_sha256':sha(Path(__file__)),'observations':rows,'whole_edge_length_assigned':False,'hil_ready':False,'source_preflight':proof};(a.output/'audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':audit['status'],'segments':len(rows),'graph_sha256':audit['output_graph_sha256']}))
if __name__=='__main__':main()
