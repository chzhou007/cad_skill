"""Audit exact native two-bar joints inside selected equipment instances.

This records source geometry and existing component attribution only. It does
not change topology or equate a drawn symbol's span with physical length.
"""
import argparse, csv, hashlib, json, math
from collections import Counter
from pathlib import Path
from native_line_path_evidence import LAYERS, _on
from source_readability import read_source


def fingerprint(block):
 rows=[]
 for e in block:
  if e.dxftype()=='LINE': rows.append(['LINE',list(e.dxf.start),list(e.dxf.end)])
  elif e.dxftype()=='ARC': rows.append(['ARC',list(e.dxf.center),e.dxf.radius,e.dxf.start_angle,e.dxf.end_angle])
  else: raise ValueError('unsupported joint block entity')
 return hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode('utf8')).hexdigest()


def collect(doc,graph,inventory,circle,policy,hashes,tol=.05):
 for key in ('source_sha256','graph_sha256','inventory_sha256','circle_sha256'):
  if policy.get(key)!=hashes.get(key):raise ValueError('input hash mismatch: '+key)
 if circle.get('source_sha256')!=hashes['source_sha256'] or circle.get('graph_sha256')!=hashes['graph_sha256'] or circle.get('status')!='source_geometry_candidates_only':raise ValueError('stale circle evidence')
 if not 0<tol<=.05:raise ValueError('invalid tolerance')
 block=policy.get('joint_block');definition=doc.blocks.get(block)
 if definition is None or fingerprint(definition)!=policy.get('block_fingerprint_sha256'):raise ValueError('joint definition mismatch')
 if sorted(e.dxftype() for e in definition)!=['ARC']*4+['LINE']*2:raise ValueError('joint structure mismatch')
 edges={e['edge_id']:e for e in graph['edges']};sources={e['edge_id']:e for e in circle['edges']};selected=policy.get('edges',[])
 if len(edges)!=len(graph['edges']) or len(sources)!=len(circle['edges']) or not selected or len(selected)!=len(set(selected)):raise ValueError('invalid edges')
 output=[]
 for eid in selected:
  edge=edges.get(eid);screen=sources.get(eid)
  if not edge or not screen or edge.get('system') not in LAYERS or screen.get('system')!=edge['system'] or screen.get('source_insert_handle')!=edge.get('source_insert_handle'):raise ValueError('edge/source mismatch')
  root=doc.entitydb.get(edge['source_insert_handle'])
  if root is None or root.dxftype()!='INSERT' or root not in doc.modelspace():raise ValueError('invalid source instance')
  children=list(root.virtual_entities()); owner=doc.blocks[root.dxf.name].block_record_handle
  direct=[x for x in children if getattr(x,'source_of_copy',None) is not None and x.source_of_copy.dxf.owner==owner]
  lines=[x for x in direct if x.dxftype()=='LINE' and x.dxf.layer==LAYERS[edge['system']]]
  joints=[x for x in direct if x.dxftype()=='INSERT' and x.dxf.name==block]
  matches=[]
  for candidate in screen['candidates']:
   if len(candidate.get('circles',[]))!=1:continue
   inner=[x for x in lines if [root.dxf.handle,x.source_of_copy.dxf.handle]==candidate['source_chain']]
   if len(inner)!=1:continue
   c=candidate['circles'][0]
   if c.get('z_coincident') is not True or c.get('line_endpoint_index') not in (0,1):continue
   circle_end=c['line_endpoint_index'];ip=[list(inner[0].dxf.start),list(inner[0].dxf.end)];free=ip[1-circle_end]
   for joint in joints:
    glyph=list(joint.virtual_entities());bars=[x for x in glyph if x.dxftype()=='LINE']
    if len(glyph)!=6 or len(bars)!=2 or sum(x.dxftype()=='ARC' for x in glyph)!=4:continue
    centers=[list((x.dxf.start+x.dxf.end)/2) for x in bars]
    for ci in range(2):
     if math.dist(free,centers[ci])>tol:continue
     for outer in lines:
      if outer is inner[0]:continue
      op=[list(outer.dxf.start),list(outer.dxf.end)]
      touching=[k for k in range(2) if math.dist(op[k],centers[1-ci])<=tol]
      if len(touching)!=1:continue
      covered=any(_on(op[0][:2],a,b,tol) and _on(op[1][:2],a,b,tol) for path in edge.get('attribute_paths',[]) for a,b in zip(path,path[1:]))
      if not covered:continue
      point=joint.ocs().to_wcs(joint.dxf.insert)
      assigned=[row for row in inventory if row.get('edge_id')==eid and row.get('source_top_handle')==root.dxf.handle and row.get('source_block_name')==block and row.get('equipment_type')=='金属软接' and row.get('assignment_status')=='assigned' and math.dist((float(row['x']),float(row['y'])),(point.x,point.y))<=tol]
      if len(assigned)!=1:continue
      matches.append({'joint_chain':[root.dxf.handle,joint.source_of_copy.dxf.handle], 'inner_line_chain':candidate['source_chain'], 'circle_chain':c['source_chain'], 'outer_line_chain':[root.dxf.handle,outer.source_of_copy.dxf.handle], 'inner_contact':centers[ci], 'outer_contact':centers[1-ci], 'component_name':assigned[0]['device_name'], 'graphic_span':math.dist(*centers), 'physical_length':'unknown'})
  output.append({'edge_id':eid,'system':edge['system'],'device_label':edge.get('device_label'),'status':'unique_source_symbol_evidence' if len(matches)==1 else 'unresolved_no_unique_evidence','matches':matches})
 # Local uniqueness is insufficient if two selected edges claim the same
 # physical instance. Retain the evidence, but block a unique conclusion.
 identities=('joint_chain','inner_line_chain','circle_chain','outer_line_chain','component_name')
 counts={key:Counter(tuple(row['matches'][0][key]) if isinstance(row['matches'][0][key],list) else row['matches'][0][key] for row in output if len(row['matches'])==1) for key in identities}
 for row in output:
  if len(row['matches'])!=1:continue
  match=row['matches'][0]
  if any(counts[key][tuple(match[key]) if isinstance(match[key],list) else match[key]]>1 for key in identities):row['status']='unresolved_shared_source_identity'
 return {'status':'native_joint_geometry_unreviewed','source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],'inventory_sha256':hashes['inventory_sha256'],'circle_sha256':hashes['circle_sha256'],'edges':output,'graph_mutated':False,'hil_ready':False,'limitations':['A source symbol and component attribution do not establish physical port identity, cross-view correspondence, actual length or human acceptance.','Only selected direct-child equipment instances and one fingerprinted joint block are covered.']}


def main():
 p=argparse.ArgumentParser()
 for key in ('source','graph','inventory','circle','policy','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);sha=lambda b:hashlib.sha256(b).hexdigest();gb=a.graph.read_bytes();ib=a.inventory.read_bytes();cb=a.circle.read_bytes();pb=a.policy.read_bytes()
 with a.inventory.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
 r=collect(doc,json.loads(gb),rows,json.loads(cb),json.loads(pb),{'source_sha256':proof['source_sha256'],'graph_sha256':sha(gb),'inventory_sha256':sha(ib),'circle_sha256':sha(cb)})
 r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'edges':len(r['edges']),'unique':sum(x['status']=='unique_source_symbol_evidence' for x in r['edges'])}))
if __name__=='__main__':main()
