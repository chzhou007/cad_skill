"""Inventory potential DN-annotation conflicts without assigning diameters.

Reads modelspace text only. Geometric proximity is a review lead, not evidence
that a specific edge changes size or that an annotation belongs to that edge.
"""
import argparse,collections,hashlib,json,re
from pathlib import Path
from pipe_annotation_attributes import source_texts,parse_dn_annotation,direct_diameters
from source_readability import read_source

def scan(texts,edges,layers):
 if not layers:raise ValueError('explicit annotation layers required')
 selected=[t for t in texts if t['layer'] in layers and re.search(r'DN',t['text'],re.I)]
 if len({t['id'] for t in selected})!=len(selected):raise ValueError('duplicate text ids')
 probes=[dict(t,text='DN1') for t in selected]
 assigned,pending=direct_diameters(probes,edges,set(),layers)
 originals={t['id']:t for t in selected};groups=collections.defaultdict(list);rows=[]
 for probe in assigned+pending:
  src=originals[probe['text']['id']];parsed=parse_dn_annotation(src['text'])
  row={'source_text':src,'syntax':'single_dn' if parsed else 'other_dn_text','parsed_single_dn':parsed,'geometric_candidate_edge_ids':probe['candidate_edge_ids'],'unique_geometric_edge_id':probe.get('edge_id'),'status':'unverified_spatial_lead'}
  rows.append(row)
  for edge in probe['candidate_edge_ids']:groups[edge].append({'text_handle':src['handle'],'text':src['text'],'syntax':row['syntax']})
 risks=[{'edge_id':edge,'nearby_texts':items,'status':'mixed_dn_syntax_review_required'} for edge,items in sorted(groups.items()) if any(i['syntax']=='single_dn' for i in items) and any(i['syntax']=='other_dn_text' for i in items)]
 return {'status':'screening_only','observations':rows,'mixed_syntax_edges':risks,'limitations':['Modelspace TEXT/MTEXT on explicitly selected layers only; nested blocks and proxy entities are excluded.','Geometry uses text insertion, orientation and height; proximity does not establish annotation, direction, system or edge-wide applicability.','Composite and system-qualified text is not interpreted; this report neither splits edges nor infers or assigns diameter.'],'graph_mutated':False,'hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for name in ('source','graph','output'):p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--text-layer',required=True,action='append');a=p.parse_args()
 doc,proof=read_source(a.source);raw=a.graph.read_bytes();graph=json.loads(raw)
 if graph.get('metadata',{}).get('source_sha256')!=proof['source_sha256']:raise ValueError('source hash mismatch')
 report=scan(source_texts(doc,a.source.stem,proof['source_sha256']),graph['edges'],set(a.text_layer))
 report.update(source_sha256=proof['source_sha256'],graph_sha256=hashlib.sha256(raw).hexdigest(),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_preflight=proof,text_layers=sorted(set(a.text_layer)))
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'observations':len(report['observations']),'mixed_syntax_edges':len(report['mixed_syntax_edges']),'status':report['status']}))
if __name__=='__main__':main()
