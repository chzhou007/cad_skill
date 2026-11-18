"""Compare device graph anchors with native drawing datums; infer no physical floor."""
import argparse,hashlib,json,math
from pathlib import Path
from source_readability import read_source

def interpretation_families(rows):
 groups={}
 for row in rows:
  extent=row.get('anchor_x_within_claimed_native_baseline')
  fid='DATUM-IN-SPAN' if extent is True else 'DATUM-EXTRAPOLATED' if extent is False else 'DATUM-NO-CLAIMED-BASELINE'
  group=groups.setdefault(fid,{'id':fid,'member_equipment_ids':[],'unresolved_equipment_ids':[],
   'numeric_match_control_ids':[],'status':'technical_anchor_interpretation_not_expert_errors',
   'physical_floor_verified':False,'human_accepted':False})
  ident=row['equipment_id'];group['member_equipment_ids'].append(ident)
  key='numeric_match_control_ids' if row['status']=='anchor_band_matches_graph_label' else 'unresolved_equipment_ids'
  group[key].append(ident)
 for group in groups.values():
  for key in ('member_equipment_ids','unresolved_equipment_ids','numeric_match_control_ids'):group[key].sort()
 return [groups[k] for k in sorted(groups)]

def screen(doc,graph,datum,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or datum.get('source_sha256')!=source_hash or datum.get('hil_ready') is not False:raise ValueError('stale source, graph or datum')
 levels=[]
 for level in datum.get('levels',[]):
  floor=level.get('floor_number');handles=level.get('source_handles',{});line=doc.entitydb.get(handles.get('baseline'));text=doc.entitydb.get(handles.get('floor_text'))
  if isinstance(floor,bool) or not isinstance(floor,int) or not line or line.dxftype()!='LINE' or line not in doc.modelspace() or not text or text.dxftype() not in ('TEXT','MTEXT') or text not in doc.modelspace() or text.plain_text()!=level.get('floor_text'):raise ValueError('native datum identity mismatch')
  a,b=line.dxf.start,line.dxf.end;y=level.get('datum_y_drawing_units')
  if not isinstance(y,(int,float)) or not math.isfinite(y) or abs(a.y-b.y)>.05 or abs(a.y-y)>.05 or abs(a.x-b.x)<=.05:raise ValueError('native datum geometry mismatch')
  levels.append({'floor':floor,'y':y,'xmin':min(a.x,b.x),'xmax':max(a.x,b.x),'baseline_handle':line.dxf.handle,'floor_text_handle':text.dxf.handle,'source_label':text.plain_text()})
 levels.sort(key=lambda x:x['y'])
 if not levels or len({x['floor'] for x in levels})!=len(levels) or any(levels[i]['y']>=levels[i+1]['y'] or levels[i]['floor']>=levels[i+1]['floor'] for i in range(len(levels)-1)):raise ValueError('invalid datum order')
 nodes=[n for n in graph['nodes'] if n.get('node_type') in ('equipment','physical_equipment')];ids=[n.get('node_id') for n in nodes]
 if len(set(ids))!=len(ids):raise ValueError('duplicate equipment ID')
 selected=policy.get('equipment_ids')
 if not isinstance(selected,list) or not selected or len(set(selected))!=len(selected) or not set(selected)<=set(ids):raise ValueError('invalid equipment scope')
 nodes={n['node_id']:n for n in nodes};captions={}
 for e in doc.modelspace().query('TEXT MTEXT'):
  if e.plain_text() in selected:captions.setdefault(e.plain_text(),[]).append(e.dxf.handle)
 rows=[]
 for id in selected:
  n=nodes[id];x,y=n.get('x'),n.get('y');floor=n.get('floor')
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (x,y)):raise ValueError('invalid equipment anchor')
  if isinstance(floor,bool) or not isinstance(floor,int):raise ValueError('unsupported equipment floor label')
  on=[v for v in levels if abs(y-v['y'])<=.05];below=[v for v in levels if v['y']<y-.05];band=below[-1] if below else None;claimed=next((v for v in levels if v['floor']==floor),None)
  status='on_datum' if on else 'below_first_known_datum' if band is None else 'anchor_band_matches_graph_label' if floor==band['floor'] else 'anchor_band_differs_from_graph_label'
  rows.append({'equipment_id':id,'graph_floor_label':floor,'anchor':[x,y],'drawing_anchor_band_floor':band['floor'] if band else None,'status':status,'claimed_floor_baseline_handle':claimed['baseline_handle'] if claimed else None,'anchor_x_within_claimed_native_baseline':claimed['xmin']<=x<=claimed['xmax'] if claimed else None,'anchor_y_minus_claimed_datum':y-claimed['y'] if claimed else None,'exact_modelspace_label_handles':captions.get(id,[]),'physical_floor_verified':False})
 unscreened=sorted(set(ids)-set(selected))
 return {'status':'drawing_anchor_datum_comparison_not_floor_assignment','source_sha256':source_hash,'graph_sha256':graph_hash,'levels':levels,'records':rows,'interpretation_families':interpretation_families(rows),'eligible_equipment_count':len(ids),'unscreened_equipment_ids':unscreened,'scope_complete':not unscreened,'graph_mutated':False,'human_accepted':False,'hil_ready':False,'limitations':['Equipment drawing anchors and extents may straddle or lie outside datum bands; coordinate comparison does not establish physical floor.','Datum lines are source segments; comparisons outside their horizontal extent use an extrapolation and are explicitly marked.','Exact modelspace captions exclude nested text and do not establish cross-view identity.','Numeric matches outside the finite datum span are retained as controls, not accepted physical floors. Resolve shared projection/anchor semantics technically before asking per-device expert questions.']}

def main():
 p=argparse.ArgumentParser()
 for k in ('source','graph','datum','policy','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();load=lambda p:json.loads(p.read_text(encoding='utf8'));policy=load(a.policy)
 if policy.get('datum_sha256')!=sha(a.datum):raise ValueError('stale datum evidence hash')
 doc,proof=read_source(a.source);result=screen(doc,load(a.graph),load(a.datum),policy,proof['source_sha256'],sha(a.graph));result.update(datum_sha256=sha(a.datum),policy_sha256=sha(a.policy),source_preflight=proof['status']);
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'status':result['status'],'equipment':len(result['records']),'different':sum(x['status']=='anchor_band_differs_from_graph_label' for x in result['records'])}))
if __name__=='__main__':main()
