"""Inventory proxy objects and their owner chains without decoding payloads."""
import argparse,collections,hashlib,json
from pathlib import Path
from ezdxf.entities.dxfgfx import DXFGraphic

def trace(db,entity,limit=40):
 chain=[];seen={entity.dxf.handle};cur=entity
 for _ in range(limit):
  handle=cur.dxf.get('owner')
  if not handle or handle=='0':return chain,'owner_chain_ended'
  if handle in seen:return chain,'owner_cycle'
  seen.add(handle);parent=db.get(handle)
  if parent is None:return chain+[{'handle':handle,'type':'unresolved'}],'missing_owner'
  chain.append({'handle':handle,'type':parent.dxftype()})
  if isinstance(parent,DXFGraphic):return chain,'graphic_ancestor'
  if parent.dxftype()=='BLOCK_RECORD':return chain,'block_record_ancestor'
  cur=parent
 return chain,'depth_limit'

def inventory(doc,source_hash,context):
 if context.get('source_sha256')!=source_hash:raise ValueError('source identity mismatch')
 text=[x for x in context.get('records',[]) if '井' in x.get('source_text','')];rows=[];counts=collections.Counter()
 for e in doc.entitydb.values():
  if not e or e.dxftype()!='ACAD_PROXY_OBJECT':continue
  chain,status=trace(doc.entitydb,e);anc=chain[-1] if chain else {};handle=anc.get('handle');matches=[{'source_text':x['source_text'],'source_chain':x['source_chain']} for x in text if handle and handle in x.get('source_chain',[])]
  rows.append({'proxy_handle':e.dxf.handle,'owner_chain':chain,'status':status,'ancestor_handle':handle,'ancestor_type':anc.get('type'),'matching_shaft_text_chains':matches});counts[(status,anc.get('type'))]+=1
 entities=[{'handle':x.dxf.handle,'layer':x.dxf.layer} for x in doc.entitydb.values() if x and x.dxftype()=='ACAD_PROXY_ENTITY']
 return {'status':'proxy_owner_metadata_not_payload','source_sha256':source_hash,'proxy_objects':rows,'proxy_object_count':len(rows),'graphic_proxy_entities':entities,'graphic_proxy_entity_count':len(entities),'summary':[{'status':k[0],'ancestor_type':k[1],'count':v} for k,v in sorted(counts.items(),key=lambda x:str(x[0]))],'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Counts cover the complete loaded entity database; they are not counts of objects skipped by a particular renderer.','Owner-chain and matching handles are metadata only; proxy payload and semantic content are not decoded.','Block ancestry, duplicate references, XREFs, cached graphics and opaque data prevent conclusions about visual or semantic completeness.']}

def main():
 p=argparse.ArgumentParser()
 for name in ('source','context','output'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();import sys;sys.path.insert(0,str(Path.home()/'.codex/skills/build-cad-pipe-topology/scripts'));from source_readability import read_source
 doc,proof=read_source(a.source);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=inventory(doc,proof['source_sha256'],json.loads(a.context.read_text(encoding='utf8')));r.update(context_sha256=h(a.context),script_sha256=h(Path(__file__)),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'proxy_objects':r['proxy_object_count'],'proxy_entities':r['graphic_proxy_entity_count'],'status':r['status']}))
if __name__=='__main__':main()
