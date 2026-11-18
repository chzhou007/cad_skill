"""Native WCS paths for explicit top-level handles or a verified INSERT chain."""
import json
from ezdxf.disassemble import recursive_decompose
from ezdxf.math import Vec3
from cad_geometry import strokes

def source_paths(doc,handles=None,chain=None):
 matrices=[]
 if chain:
  if any(h not in doc.entitydb for h in chain):raise ValueError('Invalid native source chain')
  if doc.entitydb[chain[0]] not in doc.modelspace():raise ValueError('Source chain must start at modelspace')
  for parent,child in zip(chain,chain[1:]):
   e=doc.entitydb[parent]
   if e.dxftype()!='INSERT' or doc.entitydb[child].dxf.owner!=doc.blocks[e.dxf.name].block_record_handle:raise ValueError('Source chain is not a real nested INSERT path')
   matrices.append(e.matrix44())
  if handles and list(handles)!=[chain[-1]]:
   # A source assembly can contain several equipment items. Select only actual
   # immediate children, while preserving every ancestor placement transform.
   parent=doc.entitydb[chain[-1]]
   if parent.dxftype()!='INSERT':raise ValueError('Native member selection needs an INSERT parent')
   if len(set(handles))!=len(handles):raise ValueError('Duplicate native assembly member')
   if any(h not in doc.entitydb or doc.entitydb[h].dxf.owner!=doc.blocks[parent.dxf.name].block_record_handle for h in handles):
    raise ValueError('Native assembly member is not owned by the source parent')
   matrices.append(parent.matrix44())
  else:handles=[chain[-1]]
 out=[]
 for h in handles or []:
  if h not in doc.entitydb:raise ValueError('Invalid native source handle: '+h)
  for e in recursive_decompose([doc.entitydb[h]]):
   for vertices,fill in strokes(e):
    if len(vertices)<2:continue
    pts=[]
    for p in vertices:
     v=Vec3(p[0],p[1],0)
     for matrix in reversed(matrices):v=matrix.transform(v)
     pts.append([v.x,v.y])
    out.append({'points':pts,'fill':bool(fill)})
 return out

def find_insert_chains(doc,root_handle,block_name,point,tolerance=.01):
 """Find actual matching child INSERT identity at an audited WCS insertion point."""
 found=[]
 def walk(e,parents,matrices,depth):
  if e.dxftype()!='INSERT' or depth>12:return
  chain=parents+[e.dxf.handle];p=e.ocs().to_wcs(e.dxf.insert)
  for matrix in reversed(matrices):p=matrix.transform(p)
  if e.dxf.name==block_name and (p.x-point[0])**2+(p.y-point[1])**2<=tolerance*tolerance:found.append(chain)
  for child in doc.blocks[e.dxf.name].query('INSERT'):walk(child,chain,matrices+[e.matrix44()],depth+1)
 if root_handle in doc.entitydb:walk(doc.entitydb[root_handle],[],[],0)
 return found


def recover_block_insert_chains(doc,instances,tolerance=.05):
 """Bind unique renderable block INSERTs for display; infer no connectivity."""
 import collections,math
 if not math.isfinite(tolerance) or not 0<tolerance<=.05:raise ValueError('invalid source-chain tolerance')
 existing=[];explicit_handles=set()
 for item in instances:
  chain=_existing_chain(item)
  if chain:existing.append(tuple(chain))
  hs=item.get('source_handles') or []
  if isinstance(hs,str):
   try:hs=json.loads(hs)
   except (ValueError,TypeError):hs=[]
  if isinstance(hs,list):explicit_handles.update(hs)
 def intersects(a,b):return a[:min(len(a),len(b))]==b[:min(len(a),len(b))]
 def valid_tree(insert,stack,depth):
  if depth>12 or insert.dxftype()!='INSERT' or insert.dxf.get('row_count',1)!=1 or insert.dxf.get('column_count',1)!=1:return False
  name=insert.dxf.name
  if name in stack or name not in doc.blocks:return False
  block=doc.blocks[name]
  if block.block.dxf.get('flags',0)&(4|8|16):return False
  if any(e.dxftype() in {'ACAD_PROXY_ENTITY','ACAD_PROXY_OBJECT','3DSOLID','BODY','REGION','SURFACE','UNDERLAY'} for e in block):return False
  return all(valid_tree(child,stack+(name,),depth+1) for child in block.query('INSERT'))
 def valid_chain(chain):
  for handle in chain:
   e=doc.entitydb[handle];matrix=e.matrix44()
   if abs(matrix[2,0])>1e-10 or abs(matrix[2,1])>1e-10:return False
  leaf=doc.blocks[doc.entitydb[chain[-1]].dxf.name]
  permitted={'LINE','LWPOLYLINE','ARC','CIRCLE','SPLINE','ELLIPSE','POINT'}
  if not leaf or any(e.dxftype() not in permitted for e in leaf):return False
  try:
   native=list(recursive_decompose([doc.entitydb[chain[-1]]]))
   return bool(native) and all(e.dxftype()=='POINT' or bool(strokes(e)) for e in native) and bool(source_paths(doc,chain=list(chain)))
  except (KeyError,TypeError,ValueError,NotImplementedError):return False
 proposals=[];tree_cache={}
 for item in instances:
  if item.get('source_kind')!='block_insert' or item.get('display_source_chain') or item.get('source_handles') or item.get('sourceGeometry'):continue
  root=item.get('source_top_handle');block=item.get('source_block_name');x=item.get('x');y=item.get('y')
  if not root or not block or root not in doc.entitydb or doc.entitydb[root] not in doc.modelspace():continue
  if not isinstance(x,(int,float)) or not isinstance(y,(int,float)) or not math.isfinite(x) or not math.isfinite(y):continue
  if root not in tree_cache:tree_cache[root]=valid_tree(doc.entitydb[root],(),0)
  if not tree_cache[root]:continue
  matches=find_insert_chains(doc,root,block,(x,y),tolerance)
  if len(matches)!=1:continue
  chain=tuple(matches[0])
  if chain[-1] in explicit_handles or any(intersects(chain,e) for e in existing) or not valid_chain(chain):continue
  proposals.append((item,chain))
 counts=collections.Counter(chain for _,chain in proposals);recovered=0
 for item,chain in proposals:
  if counts[chain]!=1 or any(chain!=other and intersects(chain,other) for _,other in proposals):continue
  item['display_source_chain']=list(chain)
  item['display_source_status']='verified_unique_named_block_insert_chain'
  item['display_source_rule']='unique_planar_insert_tree_at_original_source_position'
  recovered+=1
 return recovered


def _existing_chain(item):
 chain=item.get('display_source_chain')
 if isinstance(chain,str):
  try:chain=json.loads(chain)
  except (ValueError,TypeError):return None
 return chain if isinstance(chain,list) else None


def recover_folded_valve_chains(doc, instances, tolerance=.05):
 """Recover unambiguous native display identity, without changing connectivity.

 Only the explicit folded-valve source kind is eligible. The top-level source
 INSERT, exact named nested block, and original drawing position must all agree.
 Ambiguous or shared chains stay unresolved.
 """
 import collections, math
 if not math.isfinite(tolerance) or tolerance <= 0:
  raise ValueError('invalid source-chain tolerance')
 existing=set()
 for item in instances:
  chain=_existing_chain(item)
  if chain:existing.add(tuple(chain))
 proposals=[]
 for item in instances:
  if item.get('source_kind')!='turn_display_valve_folded_to_elbow' or item.get('display_source_chain') or item.get('source_handles'):
   continue
  root=item.get('source_top_handle');block=item.get('source_block_name');x=item.get('x');y=item.get('y')
  if not root or not block or root not in doc.entitydb or doc.entitydb[root] not in doc.modelspace():continue
  if not isinstance(x,(int,float)) or not isinstance(y,(int,float)) or not math.isfinite(x) or not math.isfinite(y):continue
  matches=find_insert_chains(doc,root,block,(x,y),tolerance)
  if len(matches)==1:proposals.append((item,tuple(matches[0])))
 counts=collections.Counter(chain for _,chain in proposals)
 recovered=0
 for item,chain in proposals:
  if counts[chain]!=1 or chain in existing:continue
  item['display_source_chain']=list(chain)
  item['display_source_status']='verified_nested_folded_valve_insert_chain'
  item['display_source_rule']='unique_named_child_at_original_drawing_position'
  recovered+=1
 return recovered


def recover_exploded_ball_valve_chains(doc, instances, tolerance=.05):
 """Recover a self-contained six-primitive native ball-valve parent only.

 The existing source classification, unique modelspace INSERT, primitive types,
 colours, dimensions and observed hatch-centre position must all agree. The
 recovery is display provenance only and does not establish edge ownership.
 """
 import collections, math
 from ezdxf import bbox
 if not math.isfinite(tolerance) or tolerance <= 0:raise ValueError('invalid source-chain tolerance')
 used_roots=set()
 for item in instances:
  chain=_existing_chain(item)
  if chain:used_roots.add(chain[0])
 proposals=[]
 for item in instances:
  if item.get('source_kind')!='exploded_geometry' or item.get('source_block_name')!='EXPLODED:H-PICPNT-91' or item.get('display_source_chain') or item.get('source_handles'):
   continue
  root=item.get('source_top_handle');x=item.get('x');y=item.get('y')
  if not root or root not in doc.entitydb or doc.entitydb[root] not in doc.modelspace():continue
  if not isinstance(x,(int,float)) or not isinstance(y,(int,float)) or not math.isfinite(x) or not math.isfinite(y):continue
  parent=doc.entitydb[root]
  if parent.dxftype()!='INSERT':continue
  native_children=list(doc.blocks[parent.dxf.name])
  if sorted(e.dxftype() for e in native_children)!=['ELLIPSE','ELLIPSE','HATCH','LINE','LINE','LINE']:continue
  children=list(parent.virtual_entities())
  if sorted(e.dxftype() for e in children)!=['ELLIPSE','ELLIPSE','HATCH','LINE','LINE','LINE']:continue
  if any(int(e.dxf.get('color',256))!=2 for e in children):continue
  hatch=next(e for e in children if e.dxftype()=='HATCH');bounds=bbox.extents([hatch],fast=True)
  if not bounds.has_data:continue
  width=bounds.extmax.x-bounds.extmin.x;height=bounds.extmax.y-bounds.extmin.y;size=max(width,height)
  if not 30.<=size<=60. or min(width,height)/size<.8:continue
  center=(bounds.center.x,bounds.center.y)
  if math.dist(center,(x,y))>tolerance:continue
  ellipses=[e for e in children if e.dxftype()=='ELLIPSE'];lines=[e for e in children if e.dxftype()=='LINE']
  if any(math.dist(center,(e.dxf.center.x,e.dxf.center.y))>size for e in ellipses):continue
  if any(math.dist(center,((e.dxf.start.x+e.dxf.end.x)/2,(e.dxf.start.y+e.dxf.end.y)/2))>size*2.5 or not(size*4<=math.dist((e.dxf.start.x,e.dxf.start.y),(e.dxf.end.x,e.dxf.end.y))<=size*6) for e in lines):continue
  proposals.append((item,root))
 counts=collections.Counter(root for _,root in proposals);recovered=0
 for item,root in proposals:
  if counts[root]!=1 or root in used_roots:continue
  item['display_source_chain']=[root]
  item['display_source_status']='verified_exploded_ball_valve_parent_chain'
  item['display_source_rule']='unique_six_primitive_parent_at_original_hatch_center'
  recovered+=1
 return recovered
