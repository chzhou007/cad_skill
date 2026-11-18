"""Compare all source interface glyphs of scoped main/detail candidates.

Identical geometry is evidence of a shared drawing convention, not identity.
"""
import argparse,hashlib,json,math
from collections import Counter
from pathlib import Path
from source_readability import read_source


def glyph(doc,node,precision=2):
 handles=node.get('source_handles')
 if node.get('subtype')!='out_of_plane_interface' or not isinstance(handles,list) or len(handles)!=5 or len(set(handles))!=5:raise ValueError('unsupported interface glyph')
 entities=[doc.entitydb.get(h) for h in handles]
 if any(e is None or e not in doc.modelspace() for e in entities):raise ValueError('missing native modelspace glyph')
 if sorted(e.dxftype() for e in entities)!=['CIRCLE','LINE','LINE','LINE','LINE']:raise ValueError('incomplete native glyph')
 c=next(e for e in entities if e.dxftype()=='CIRCLE');center=c.ocs().to_wcs(c.dxf.center)
 if math.dist((center.x,center.y),(node['x'],node['y']))>.05:raise ValueError('glyph centre differs from graph')
 def point(p):return [round(p.x-center.x,precision),round(p.y-center.y,precision)]
 lines=[]
 for e in entities:
  if e.dxftype()!='LINE':continue
  points=sorted([point(e.dxf.start),point(e.dxf.end)])
  lines.append({'layer':e.dxf.layer,'points':points})
 lines.sort(key=lambda row:(row['layer'],row['points']))
 return {'signature':{'circle_layer':c.dxf.layer,'radius':round(c.dxf.radius,precision),'lines':lines},'handles':handles,'center':[center.x,center.y,center.z],'z_values':[e.dxf.center.z if e.dxftype()=='CIRCLE' else [e.dxf.start.z,e.dxf.end.z] for e in entities]}


def analyze(doc,graph,policy,source_hash,graph_hash):
 if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('input identity mismatch')
 from canonicalize_confirmed_sideviews import source_expression_context
 graph=source_expression_context(graph)
 detail=graph.get('sourceDetailComparison') or {};pairs=detail.get('pairs')
 if detail.get('source_sha256')!=source_hash or not isinstance(pairs,list) or not pairs:raise ValueError('missing source-bound detail candidates')
 nodes={n['node_id']:n for n in graph['nodes']};edges={e['edge_id']:e for e in graph['edges']}
 if len(nodes)!=len(graph['nodes']) or len(edges)!=len(graph['edges']):raise ValueError('duplicate graph ids')
 seen=set();rows=[]
 for pair in pairs:
  key=(pair.get('system'),pair.get('rank'))
  if key in seen:raise ValueError('duplicate candidate rank')
  seen.add(key);service=pair['system'];upper=edges.get(pair['upper_edge']);tee=pair['detail_tee']
  if not upper or upper.get('system')!=service or pair['upper_pipe'] not in upper.get('source_handles',[]) or pair['upper_terminal'] not in (upper['start_node_id'],upper['end_node_id']):raise ValueError('upper candidate mismatch')
  other=upper['end_node_id'] if upper['start_node_id']==pair['upper_terminal'] else upper['start_node_id']
  lower=[e for e in edges.values() if e.get('system')==service and tee in (e.get('start_node_id'),e.get('end_node_id')) and pair['detail_pipe'] in e.get('source_handles',[])]
  if len(lower)!=1:raise ValueError('detail candidate ambiguous')
  le=lower[0];down=le['end_node_id'] if le['start_node_id']==tee else le['start_node_id']
  if other not in nodes or down not in nodes or nodes[other].get('system')!=service or nodes[down].get('system')!=service:raise ValueError('glyph node mismatch')
  rows.append({'system':service,'rank':pair['rank'],'upper_edge':upper['edge_id'],'upper_glyph':other,'upper':glyph(doc,nodes[other]),'detail_edge':le['edge_id'],'detail_glyph':down,'detail':glyph(doc,nodes[down]),'candidate_exception':pair.get('exception','')})
 for row in rows:
  alternatives=[x for x in rows if x['system']==row['system'] and x['detail']['signature']==row['upper']['signature']]
  row['same_signature_detail_ranks']=[x['rank'] for x in alternatives]
  row['matched_detail_signature_identical']=row['rank'] in row['same_signature_detail_ranks']
  row['status']='individual_mapping_ambiguous' if len(alternatives)>1 else 'unique_glyph_shape_not_identity_proof' if alternatives else 'glyph_shape_mismatch'
 return {'status':'native_glyph_comparison_not_mapping','source_sha256':source_hash,'graph_sha256':graph_hash,'candidate_count':len(rows),'rows':rows,'summary':dict(Counter(r['status'] for r in rows)),'graph_mutated':False,'hil_ready':False,'limitations':['Compares only selected modelspace circle plus four LINE glyphs under translation in XY; rotation, mirror, other views and other drawing features are not compared.','Matching shape, rank, proximity or translation does not establish equipment, port, path or hydraulic equivalence.','Z evidence is recorded but excluded from the XY glyph signature.']}


def main():
 p=argparse.ArgumentParser()
 for key in ('source','graph','policy','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();doc,proof=read_source(a.source);gb=a.graph.read_bytes();pb=a.policy.read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();r=analyze(doc,json.loads(gb),json.loads(pb),proof['source_sha256'],sha(gb));r.update(policy_sha256=sha(pb),script_sha256=sha(Path(__file__).read_bytes()),source_preflight=proof)
 with a.output.open('x',encoding='utf8',newline='\n') as f:json.dump(r,f,ensure_ascii=False,indent=2);f.write('\n')
 print(json.dumps({'candidate_count':r['candidate_count'],'summary':r['summary']}))
if __name__=='__main__':main()
