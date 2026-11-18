"""Attach an explicit expert drawing-convention clarification to scoped wave joins."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path

STATEMENT='这个波浪已经找专家确认了，它的属性代表是两边的线太长了， 做图的时候把太长的线用波浪断开，所以只是一个做图规范的问题，没有任何其他的额外属性。'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def apply(graph,confirmation):
 if confirmation.get('statement')!=STATEMENT or confirmation.get('full_graph_accepted') is not False:raise ValueError('invalid expert convention evidence')
 g=copy.deepcopy(graph);specs=confirmation['wave_pairs'];ids=[frozenset(x['wave_handles']) for x in specs]
 if not ids or any(len(x)!=2 for x in ids) or len(set(ids))!=len(ids):raise ValueError('invalid wave pair scope')
 matched=[]
 for e in g['edges']:
  w=e.get('source_wave_omission')
  if not w or frozenset(w.get('wave_handles',[])) not in ids:continue
  key=frozenset(w['wave_handles']);spec=specs[ids.index(key)]
  if e.get('system')!=spec['system'] or e.get('path_length_complete') is not False or w.get('physical_length')!='unknown':raise ValueError('wave system or physical length mismatch')
  if e.get('connection_mode')!='source_calibrated_wave_omission_unreviewed':raise ValueError('unexpected wave provenance')
  w.update(drawing_convention='long_pipe_drawing_break',connectivity='continuous_same_pipe',
           physical_component=False,additional_physical_property=False,
           scoped_expert_convention_confirmed=True,human_accepted=True,
           confirmation_scope='pictured_wave_drawing_convention_and_continuity_only',confirmation_sha256=confirmation['confirmation_sha256'])
  matched.append({'edge_id':e['edge_id'],'wave_handles':w['wave_handles'],'system':e['system']})
 if len(matched)!=len(specs):raise ValueError('missing or duplicate selected wave pair')
 g['expertWaveDrawingConvention']={'confirmation_sha256':confirmation['confirmation_sha256'],
  'image_sha256':confirmation['image_sha256'],'scope':'six pictured pairs only; drawing convention and continuity',
  'pairs':matched,'full_graph_accepted':False,'hil_ready':False}
 g.setdefault('metadata',{}).update(hil_ready=False,graph_complete=False)
 return g,matched

def main():
 p=argparse.ArgumentParser()
 for k in ('graph','devices','confirmation','image','output'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();c=json.loads(a.confirmation.read_text(encoding='utf8'))
 for key,path in [('input_graph_sha256',a.graph),('devices_sha256',a.devices),('image_sha256',a.image)]:
  if c.get(key)!=sha(path):raise ValueError(key+' mismatch')
 c['confirmation_sha256']=sha(a.confirmation);g,matched=apply(json.loads(a.graph.read_text(encoding='utf8')),c)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.mkdir(parents=True);out=a.output/'graph_with_wave_convention.json';out.write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n',encoding='utf8');shutil.copyfile(a.devices,a.output/'assigned_edge_device_instances.csv')
 (a.output/'audit.json').write_text(json.dumps({'input_graph_sha256':c['input_graph_sha256'],'output_graph_sha256':sha(out),'confirmation_sha256':c['confirmation_sha256'],'image_sha256':c['image_sha256'],'pairs':matched,'full_graph_accepted':False},ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps({'scoped_pairs':len(matched),'full_graph_accepted':False}))
if __name__=='__main__':main()
