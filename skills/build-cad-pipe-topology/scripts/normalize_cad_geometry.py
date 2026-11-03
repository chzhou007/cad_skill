"""Inventory and normalize source pipe crossover curves before graph extraction."""
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
import ezdxf
from pipe_geometry import xy,curve_candidates,normalize_arc,set_tolerance

def normalize_document(d,config):
 layers=config['system_layers'];evidence=set(config.get('crossing_evidence_layers',[]));set_tolerance(config.get('tolerance_native_units',.5));segments=[];witnesses=[];curves=[];inventory=Counter();unsupported=[]
 for e in d.modelspace():
  layer=e.dxf.layer
  if layer not in layers and layer not in evidence:continue
  typ=e.dxftype();inventory[layer+' / '+typ]+=1;sy=layers.get(layer,'evidence_only:'+layer)
  if typ=='LINE':
   record={'a':xy(e.dxf.start),'b':xy(e.dxf.end),'system':sy,'handle':e.dxf.handle,'source_layer':layer};witnesses.append(record)
   if layer in layers:segments.append(record)
  elif typ in ('LWPOLYLINE','POLYLINE'):
   for i,part in enumerate(e.virtual_entities()):
    if part.dxftype()=='LINE':
     record={'a':xy(part.dxf.start),'b':xy(part.dxf.end),'system':sy,'handle':str(e.dxf.handle)+':LINE:'+str(i),'source_handles':[e.dxf.handle],'source_layer':layer};witnesses.append(record)
     if layer in layers:segments.append(record)
   if layer in layers:curves.extend(curve_candidates(e,sy))
  elif typ=='ARC'and layer in layers:curves.extend(curve_candidates(e,sy))
  elif typ=='SPLINE':unsupported.append({'source_handle':e.dxf.handle,'layer':layer,'type':typ,'status':'pending_curve_family_not_implemented'})
 audit=[];normalized=list(segments)
 for a in curves:
  n,st=normalize_arc(a,witnesses,segments);audit.append(dict(a,normalization_status=st,crossings=n['crossings']if n else [],relative_elevation='unknown',source_layer=d.entitydb[a['source_entity_handle']].dxf.layer))
  if n:normalized.append(n)
 return {'schema_version':1,'geometry_module_version':'1.0.0','segments':normalized,'crossing_witnesses':witnesses,'curve_audit':audit,'unsupported_curves':unsupported,'source_inventory':dict(inventory),'connectivity_policy':'A normalized jump continues its owner pipe; crossing channels remain independent. No elevation or flow inference.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dxf',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
 if a.output_dir.exists():p.error('Output directory exists; select a new versioned path')
 cfg=json.loads(a.config.read_text(encoding='utf8'));result=normalize_document(ezdxf.readfile(a.dxf),cfg);result['source']={'dxf':str(a.dxf.resolve()),'sha256':hashlib.sha256(a.dxf.read_bytes()).hexdigest(),'config_sha256':hashlib.sha256(a.config.read_bytes()).hexdigest()};a.output_dir.mkdir(parents=True)
 (a.output_dir/'normalized-pipe-geometry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps({'source_curves':len(result['curve_audit']),'normalized_jumps':sum(c['normalization_status']=='normalized'for c in result['curve_audit']),'pending_or_physical_curves':sum(c['normalization_status']!='normalized'for c in result['curve_audit']),'unsupported_curves':len(result['unsupported_curves'])},indent=2))
if __name__=='__main__':main()
