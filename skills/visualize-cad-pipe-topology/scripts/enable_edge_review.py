"""Add current frontier labels and persistent manual lengths to an existing viewer."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ASSETS=Path(__file__).resolve().parents[1]/'assets/viewer'
sys.path.insert(0,str(ASSETS))
from hil_server import identity

REASONS={
 'known_inline_assembly_interiors_missing_physical_length':'阀件组合内部的实际长度未给出',
 'known_legacy_named_scope_incomplete_whole_attributes':'已有范围对应，整边属性仍不完整',
 'known_local_correspondence_incomplete_attributes':'局部已对应，整边长度或管径待核',
 'known_member_correspondence_incomplete_metric':'支管已对应，整边长度未给出',
 'known_riser_member_connector_length_unproved':'立管接口接管长度未给出',
 'reviewed_range_per_edge_length_allocation_unresolved':'已有范围总长，尚未分配到本边',
}

def enable(parent,output,provider,port):
 parent=Path(parent).resolve();output=Path(output).resolve()
 if output.exists():raise ValueError('Output already exists')
 manifest=json.loads((parent/'public/data/manifest.json').read_text(encoding='utf8'))
 graph=json.loads((parent/'public/data/graph.json').read_text(encoding='utf8'))
 inv=json.loads(Path(provider).read_text(encoding='utf8')) if provider else {}
 items={}
 for r in inv.get('remaining_horizontal_attributes',[]):
  items[r['edge_id']]={'edgeId':r['edge_id'],'label':'长度/属性','reasons':[REASONS.get(r['next_scope'],r['next_scope'])],'sourceScope':r['next_scope']}
 for r in inv.get('records',[]):
  if r.get('classification')=='mixed_horizontal_vertical' and not r.get('has_existing_correspondence'):
   items[r['edge_id']]={'edgeId':r['edge_id'],'label':'对应','reasons':['水平部分的设备/路径个体对应尚未确认'],'sourceScope':'mixed_individual_correspondence'}
 # Generic explicitly edge-scoped review hints remain separate from source coverage.
 edge_ids={e['edge_id'] for e in graph['edges']}
 for hint in graph.get('review',[]):
  key=hint.get('edge_id') or (hint.get('id') if hint.get('id') in edge_ids else None)
  if key:items.setdefault(key,{'edgeId':key,'label':'待判断','reasons':[hint.get('reason') or hint.get('message') or '已有边级审查提示'],'sourceScope':'explicit_edge_review_hint'})
 if set(items)-edge_ids:raise ValueError('Queue contains non-current edge IDs')
 q={'schemaVersion':1,'datasetId':identity(manifest),'graphSha256':hashlib.sha256((parent/'public/data/graph.json').read_bytes()).hexdigest(),'items':list(items.values()),'automatic_hint_is_not_confirmed_fault':True,'missing_attributes_are_not_new_expert_questions':True}
 shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 for rel in ['hil_server.py','edge_review_store.py','review_backup.py','public/edge-review.js','public/hil.js']:
  shutil.copy2(ASSETS/rel,output/rel)
 # Retain the actual current attribute chain and source-specific display decorators.
 app=(output/'public/app.js').read_text(encoding='utf8')
 if 'initEdgeReview' in app:raise ValueError('Already enabled')
 app="import {reviewCsvValues,reviewCsvFields,reviewAttributeCsvFields} from './edge-review.js';\n"+app
 replacements={"$('#detail-content').innerHTML=html;":"$('#detail-content').innerHTML=html;\n  document.dispatchEvent(new Event('cad-details-changed'));", "...ownershipLengthScopeCsvValues(e,data),source_dimensioned_segments_json":"...ownershipLengthScopeCsvValues(e,data),...reviewCsvValues(e,crossViewAttributeCsvValues(e,data.attribute_value_context)),source_dimensioned_segments_json", "'connection_mode',...edgeAttributeCsvFields]":"'connection_mode',...edgeAttributeCsvFields,...reviewCsvFields,...reviewAttributeCsvFields]", "await (await import('./hil.js')).initHil(window.cadViewer);":"await (await import('./hil.js')).initHil(window.cadViewer);\n    await (await import('./edge-review.js')).initEdgeReview(window.cadViewer);"}
 for old,new in replacements.items():
  if app.count(old)!=1:raise ValueError('Unsupported app integration: '+old)
  app=app.replace(old,new)
 (output/'public/app.js').write_text(app,encoding='utf8')
 # The latest source-only connection description fixes the complete old/new cohort.
 for rel in ['public/checked-source-connection-display.js','public/edge-attributes-inherited-entries.js']:
  if (output/rel).exists():shutil.copy2(ASSETS/rel,output/rel)
 (output/'public/data/edge-review-queue.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf8')
 hashes={r:hashlib.sha256((output/r).read_bytes()).hexdigest() for r in ['public/app.js','public/hil.js','hil_server.py','edge_review_store.py','public/edge-review.js','public/data/edge-review-queue.json','public/checked-source-connection-display.js','public/edge-attributes-inherited-entries.js'] if (output/r).exists()}
 manifest['edgeReviewUI']={'parentBundleId':manifest['bundleId'],'assets':hashes,'lengthUnit':'m','source_values_preserved':True}
 old=manifest['bundleId'];manifest['bundleId']=hashlib.sha256(json.dumps([old,hashes],sort_keys=True).encode()).hexdigest()[:20];manifest['preferredPort']=port
 (output/'public/data/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
 p=output/'public/index.html';s=p.read_text(encoding='utf8');p.write_text(s.replace(old,manifest['bundleId']),encoding='utf8')
 report={'viewer':str(output),'bundleId':manifest['bundleId'],'review_edges':len(items),'counts':{s:sum(x['sourceScope']==s for x in items.values()) for s in sorted({x['sourceScope'] for x in items.values()})},'graph_bytes_unchanged':(parent/'public/data/graph.json').read_bytes()==(output/'public/data/graph.json').read_bytes(),'datasetId':identity(manifest),'url':f'http://127.0.0.1:{port}/?edge=E0313'}
 (output/'edge-review-enablement.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--parent',required=True);p.add_argument('--output',required=True);p.add_argument('--provider');p.add_argument('--port',type=int,default=10559);a=p.parse_args();print(json.dumps(enable(a.parent,a.output,a.provider,a.port),ensure_ascii=False))
