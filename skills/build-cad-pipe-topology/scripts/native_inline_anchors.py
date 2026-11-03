"""Opt-in source prototype anchors for inline context; never hydraulic links."""
import hashlib,json
from ezdxf.math import Vec3
import pipe_geometry as pg

def block_signature(doc,name):
 def value(v):
  if isinstance(v,float):return round(v,8)
  if isinstance(v,(tuple,list))or hasattr(v,'x'):return [value(z)for z in v]
  return v
 records=[]
 for e in doc.blocks[name]:
  attrs={k:value(v)for k,v in e.dxf.all_existing_dxf_attribs().items()if k not in ['handle','owner']}
  if e.dxftype()=='LWPOLYLINE':attrs['vertices']=[[float(z)for z in p]for p in e.get_points()]
  records.append([e.dxftype(),attrs])
 return hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def anchor_contacts(symbol,edges,doc,rules):
 entity=symbol.get('entity')
 if entity is None or entity.dxftype()!='INSERT':return None
 for rule in rules:
  if entity.dxf.name!=rule['source_block']:continue
  if block_signature(doc,entity.dxf.name)!=rule['block_signature_sha256']:continue
  if not rule.get('source_evidence'):continue
  point=entity.matrix44().transform(Vec3(rule['anchor_local']))
  contacts=[e for e in edges if any(pg.segdist((point.x,point.y),a,b)<=pg.TOL for p in e['attribute_paths']for a,b in zip(p,p[1:]))]
  return contacts
 return None
