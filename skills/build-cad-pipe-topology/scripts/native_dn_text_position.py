"""Guard insertion-point DN geometry against unsupported native TEXT transforms."""
import math

def supported(ent):
 if ent.dxftype()!='TEXT':return False
 try:
  if tuple(ent.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):return False
  if ent.dxf.get('text_generation_flag',0)!=0 or ent.dxf.get('halign',0)!=0 or ent.dxf.get('valign',0)!=0 or ent.dxf.get('invisible',0)!=0:return False
  oblique=float(ent.dxf.get('oblique',0));width=float(ent.dxf.get('width',1));height=float(ent.dxf.height);rotation=float(ent.dxf.get('rotation',0));p=ent.dxf.insert
  return all(math.isfinite(x) for x in (oblique,width,height,rotation,p.x,p.y,p.z)) and abs(oblique)<1e-9 and width>0 and height>0
 except (TypeError,ValueError,AttributeError):return False
