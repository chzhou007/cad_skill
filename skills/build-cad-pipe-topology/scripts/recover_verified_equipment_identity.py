"""Recover source equipment identity from a uniquely matchable candidate group.

This changes equipment inventory only. It does not infer a port or pipe edge.
"""
import argparse,copy,hashlib,json,math
from pathlib import Path
from source_readability import read_source
from native_equipment_body import body_straight_segments

def unique_matching(matrix):
 if not matrix or len(matrix)>12:raise ValueError('invalid candidate group size')
 labels=set().union(*[set(x) for x in matrix.values()])
 if len(labels)!=len(matrix) or any(not x for x in matrix.values()):raise ValueError('group is not balanced')
 results=[]
 def solve(remaining,used,chosen):
  if len(results)>1:return
  if not remaining:results.append(dict(chosen));return
  key=min(remaining,key=lambda k:len(set(matrix[k])-used))
  for label in sorted(set(matrix[key])-used):
   chosen[key]=label;solve(remaining-{key},used|{label},chosen);del chosen[key]
 solve(set(matrix),set(),{})
 if len(results)!=1:raise ValueError('candidate group is not uniquely matchable')
 return results[0]

def recover(doc,graph,bindings,policy,source_hash,graph_hash,bindings_hash,tol=.05):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or policy.get('bindings_sha256')!=bindings_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('source or input hash mismatch')
 by_handle={r['source_handle']:r for r in bindings};nodes={n['node_id']:n for n in graph['nodes']};group=policy['group'];handles=group['source_handles'];labels=group['label_handles']
 if len(by_handle)!=len(bindings) or len(nodes)!=len(graph['nodes']) or len(set(handles))!=len(handles) or len(set(labels.values()))!=len(labels):raise ValueError('duplicate input identity')
 text_entities={e.dxf.text:e for e in doc.modelspace().query('TEXT') if e.dxf.layer=='空调编号' and e.dxf.text.startswith('CRAH-')}
 all_text=[e for e in doc.modelspace().query('TEXT') if e.dxf.layer=='空调编号' and e.dxf.text.startswith('CRAH-')]
 if len(text_entities)!=len(all_text):raise ValueError('duplicate source equipment labels')
 for label,h in labels.items():
  t=text_entities.get(label)
  if not t or t.dxf.handle!=h or tuple(t.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.) or t.dxf.get('text_generation_flag',0)!=0:raise ValueError('source label mismatch or unsupported transform')
 matrix={};boxes={}
 for h in handles:
  r=by_handle.get(h);ins=doc.entitydb.get(h)
  if not r or not ins or ins.dxftype()!='INSERT' or ins not in doc.modelspace() or ins.dxf.layer!='空调' or ins.dxf.name!=r['source_block']:raise ValueError('source equipment mismatch')
  body,unsupported=body_straight_segments(ins)
  if not body or unsupported:raise ValueError('incomplete equipment geometry')
  box=[[min(p[i] for seg in body for p in seg) for i in (0,1)],[max(p[i] for seg in body for p in seg) for i in (0,1)]];old=r['bounds']
  if any(abs(box[j][i]-old[j][i])>tol for j in (0,1) for i in (0,1)):raise ValueError('source equipment bounds mismatch')
  inside=[name for name,t in text_entities.items() if box[0][0]-tol<=t.dxf.insert.x<=box[1][0]+tol and box[0][1]-tol<=t.dxf.insert.y<=box[1][1]+tol]
  hits=inside or [name for name,t in text_entities.items() if box[0][0]-600<=t.dxf.insert.x<=box[1][0]+600 and box[0][1]-600<=t.dxf.insert.y<=box[1][1]+600]
  if set(hits)!=set(r['label_candidates']) or not set(hits)<=set(labels):raise ValueError('source label candidate set changed')
  matrix[h]=hits;boxes[h]=box
 for r in bindings:
  if r['source_handle'] not in handles and set(r['label_candidates'])&set(labels):raise ValueError('candidate group overlaps outside equipment')
 mapping=unique_matching(matrix)
 if set(mapping.values())!=set(labels):raise ValueError('unexpected matching labels')
 for h,label in mapping.items():
  n=nodes.get(label)
  if n and (n.get('node_type')!='equipment' or n.get('source_handle')!=h):raise ValueError('existing equipment contradicts matching')
  if any(n.get('source_handle')==h and n['node_id']!=label for n in nodes.values()):raise ValueError('source equipment already claimed')
 missing=[(h,label) for h,label in mapping.items() if label not in nodes]
 if {label for h,label in missing}!=set(group['expected_recovered_labels']):raise ValueError('unexpected recovered equipment')
 out=copy.deepcopy(graph);new=[]
 for h,label in sorted(missing):
  b=boxes[h];r=by_handle[h];node={'node_id':label,'node_type':'equipment','subtype':'CRAH','floor':group['floor'],'label':label,'x':(b[0][0]+b[1][0])/2,'y':(b[0][1]+b[1][1])/2,'source_handle':h,'source_block':r['source_block'],'connection_status':'ports_unresolved','parameter_candidates':r['parameter_candidates'],'source_identity_evidence':{'rule':'unique_one_to_one_candidate_group','source_label_handle':labels[label],'source_equipment_handles':handles,'candidate_matrix':matrix,'source_sha256':source_hash,'ports_inferred':False}}
  out['nodes'].append(node);new.append(node)
 out.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False,review_status='unreviewed',equipment_identity_status='source_identity_recovered_ports_pending')
 out.setdefault('preHilComparison',{}).setdefault('families',[]).append({'id':'recovered-equipment-identity','status':'algorithm_pending','disposition':'Compare recovered source equipment and labels; ports remain unresolved.'});out['preHilComparison']['status']='pending'
 return out,{'status':'source_equipment_recovered_ports_unresolved','input_graph_sha256':graph_hash,'source_sha256':source_hash,'bindings_sha256':bindings_hash,'matching':mapping,'candidate_matrix':matrix,'recovered_nodes':[n['node_id'] for n in new],'added_edges':[],'human_review':'unreviewed','hil_ready':False}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','bindings','policy','output'):p.add_argument('--'+k,required=True,type=Path)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();bb=a.bindings.read_bytes();pb=a.policy.read_bytes();sha=lambda x:hashlib.sha256(x).hexdigest();out,audit=recover(doc,json.loads(gb),json.loads(bb),json.loads(pb),proof['source_sha256'],sha(gb),sha(bb));a.output.mkdir(parents=True,exist_ok=False);g=a.output/'graph_with_equipment_identity.json';g.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 resolved=json.loads(bb)
 for row in resolved:
  if row['source_handle'] in audit['matching']:
   row['resolved_label']=audit['matching'][row['source_handle']];row['association_status']='unique_one_to_one_source_candidate_group';row['connection_status']='ports_unresolved'
 resolved_file=a.output/'equipment_source_bindings_resolved.json';resolved_file.write_text(json.dumps(resolved,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 audit.update(output_graph_sha256=sha(g.read_bytes()),resolved_bindings_sha256=sha(resolved_file.read_bytes()),policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof);(a.output/'equipment_identity_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':audit['status'],'recovered':audit['recovered_nodes']},ensure_ascii=False))
if __name__=='__main__':main()
