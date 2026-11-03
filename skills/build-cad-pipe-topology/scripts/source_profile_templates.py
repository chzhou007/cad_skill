"""Source-bound whole exploded prototypes; no subtype inferred from primitive count."""
import hashlib
from ezdxf.path import from_hatch
import pipe_geometry as pg

def hatch_points(e):
 return [pg.xy(p)for path in from_hatch(e)for p in path.flattening(max(.01,pg.TOL*.1))]

def install_templates(doc,config):
 result={}
 for rule in config.get('source_native_component_templates',[]):
  handles=rule['prototype_handles'];entities=[doc.entitydb[h]for h in handles]
  if len(entities)<5 or not any(e.dxftype()=='LINE'for e in entities):raise ValueError('Incomplete source prototype')
  if any(e.dxftype()not in ['LINE','HATCH']for e in entities):raise ValueError('Unsupported source prototype primitive')
  name='PROFILE_NATIVE_'+hashlib.sha256('|'.join(handles).encode()).hexdigest()[:12]
  block=doc.blocks.new(name)
  for e in entities:
   if e.dxftype()=='LINE':block.add_entity(e.copy())
  config['inline_types'][name]=[rule['label'],rule['type_code']]
  config.setdefault('exploded_template_blocks',[]).append(name)
  result[name]=rule
 return result

def validate_template_fills(doc,items,rules):
 result=[];audit=[];hatches=list(doc.modelspace().query('HATCH'))
 for item in items:
  rule=rules.get(item['block'])
  if rule is None:result.append(item);continue
  transform=item['prototype_transform'];origin=transform['origin'];xx=transform['xaxis'];yy=transform['yaxis']
  def tr(p):return(origin[0]+p[0]*xx[0]+p[1]*yy[0],origin[1]+p[0]*xx[1]+p[1]*yy[1])
  fill_handles=[];valid=True
  for handle in rule['prototype_handles']:
   e=doc.entitydb[handle]
   if e.dxftype()!='HATCH':continue
   target=[tr(p)for p in hatch_points(e)];matches=[]
   for hatch in hatches:
    pts=hatch_points(hatch)
    if len(pts)!=len(target):continue
    if all(any(pg.dist(p,q)<=pg.TOL for q in pts)for p in target)and all(any(pg.dist(q,p)<=pg.TOL for p in target)for q in pts):matches.append(hatch.dxf.handle)
   if len(matches)!=1:valid=False;break
   fill_handles+=matches
  row={'source_handles':item['source_handles'],'prototype_handles':rule['prototype_handles'],'status':'recognized_complete_profile_native_geometry'if valid else'pending_missing_or_ambiguous_native_fills','semantic_status':rule.get('semantic_status','subtype_pending')};audit.append(row)
  if valid:
   item['source_handles']=sorted(set(item['source_handles']+fill_handles));item['semantic_status']=row['semantic_status'];item['recognition_rule']='all_profile_native_lines_and_fill_boundaries_similarity_matched';result.append(item)
 return result,audit
