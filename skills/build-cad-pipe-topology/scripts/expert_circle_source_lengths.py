"""Remove only an expert-backed symbol radius from a branch's source path."""
import math

def correct_circle_branch_lengths(nodes,edges,bridges,tol=.05,crossovers=()):
 audit=[]
 for b in bridges:
  if not b.get('expert_issue') and not b.get('source_comparison'):continue
  center=b['semantic_endpoint'];rim=b['original_endpoint'];h=b['branch_handle'];span=math.dist(center,rim)
  hit=[n for n in nodes if n['node_type']=='tee' and n['system']==b['system'] and math.dist((n['x'],n['y']),center)<=tol]
  if len(hit)!=1:raise ValueError('expert circle tee missing or ambiguous')
  node=hit[0];es=[e for e in edges if node['node_id'] in (e['start_node_id'],e['end_node_id']) and h in e['source_handles']]
  if len(es)!=1:raise ValueError('expert circle branch missing or ambiguous')
  e=es[0]
  if len(e['attribute_paths'])!=1 or len(e['attribute_paths'][0])<2:raise ValueError('unsupported circle branch path')
  path=[list(p) for p in e['attribute_paths'][0]];index,neighbor=(0,1) if e['start_node_id']==node['node_id'] else (-1,-2)
  if math.dist(path[index],center)>tol or abs(math.dist(path[index],path[neighbor])-span-math.dist(rim,path[neighbor]))>tol:raise ValueError('circle rim does not lie on branch terminal')
  path[index]=list(rim);pieces=[[path[0]]];gap_evidence=[]
  for a,z in zip(path,path[1:]):
   matching=[x for x in crossovers if set(x.get('source_handles',[])).issubset(set(e['source_handles'])) and ((math.dist(a,x['a'])<=tol and math.dist(z,x['b'])<=tol) or (math.dist(a,x['b'])<=tol and math.dist(z,x['a'])<=tol))]
   if len(matching)>1:raise ValueError('ambiguous normalized crossover span')
   if matching:
    c=matching[0];gap_evidence.append({'source_handles':c['source_handles'],'a':list(a),'b':list(z),'crossings':c['crossings'],'crossing_connectivity':'independent_pipes_no_junction','physical_length':'unknown','relative_elevation':'unknown'});pieces.append([z])
   else:pieces[-1].append(z)
  if any(len(p)<2 for p in pieces):raise ValueError('crossover removal produced empty source path')
  e['attribute_paths']=pieces;gap_length=sum(math.dist(z['a'],z['b']) for z in gap_evidence);e['path_length']-=span+gap_length;e['path_length_complete']=False;e['path_length_scope']='source_drawn_pipe_only_circle_and_crossover_lengths_unknown'
  if gap_evidence:e['source_normalized_crossovers']=gap_evidence
  e['source_circle_connection']={**({'expert_issue':b['expert_issue']} if b.get('expert_issue') else {'source_comparison':b['source_comparison']}),'circle_handle':b['circle_handle'],'main_pipe_handle':b['main_handle'],'branch_pipe_handle':h,'branch_rim':list(rim),'center':list(center),'graphic_radius_not_physical_length':span,'physical_length':'unknown'}
  audit.append({'node_id':node['node_id'],'edge_id':e['edge_id'],'circle_handle':b['circle_handle'],'branch_handle':h,'graphic_radius_excluded':span,'graphic_crossover_spans_excluded':gap_length})
 return audit
