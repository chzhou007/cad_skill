"""Native WCS paths for explicit top-level handles or a verified INSERT chain."""
from ezdxf.disassemble import recursive_decompose
from ezdxf.math import Vec3
from cad_geometry import strokes

def source_paths(doc,handles=None,chain=None):
 matrices=[]
 if chain:
  if any(h not in doc.entitydb for h in chain):raise ValueError('Invalid native source chain')
  for parent,child in zip(chain,chain[1:]):
   e=doc.entitydb[parent]
   if e.dxftype()!='INSERT' or doc.entitydb[child].dxf.owner!=doc.blocks[e.dxf.name].block_record_handle:raise ValueError('Source chain is not a real nested INSERT path')
   matrices.append(e.matrix44())
  handles=[chain[-1]]
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
  chain=parents+[e.dxf.handle];p=e.dxf.insert
  for matrix in reversed(matrices):p=matrix.transform(p)
  if e.dxf.name==block_name and (p.x-point[0])**2+(p.y-point[1])**2<=tolerance*tolerance:found.append(chain)
  for child in doc.blocks[e.dxf.name].query('INSERT'):walk(child,chain,matrices+[e.matrix44()],depth+1)
 if root_handle in doc.entitydb:walk(doc.entitydb[root_handle],[],[],0)
 return found
