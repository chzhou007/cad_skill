"""Record disjoint native equipment group candidates without hydraulic merging."""
import copy

def attach(graph,evidence,source_03_sha256,graph_sha256,source_02_sha256):
 if (evidence.get('source_03_sha256'),evidence.get('graph_03_sha256'),evidence.get('source_02_sha256'))!=(source_03_sha256,graph_sha256,source_02_sha256):
  raise ValueError('Stale drawing or graph evidence')
 if evidence.get('caption_03_fragments')!=['冷塔单模块','17T','，一组','2','台','17*2','余同'] or len(evidence.get('caption_03_handles',[]))!=7:raise ValueError('Readable grouping evidence is incomplete')
 pairs=evidence.get('pairs_03',[])
 if len(pairs)!=evidence.get('native_03_module_pairs') or len(evidence.get('groups_02',[]))!=evidence.get('native_02_tagged_two_cell_groups'):
  raise ValueError('Incomplete native grouping evidence')
 out=copy.deepcopy(graph);nodes={n['node_id']:n for n in out['nodes']};used=set();ids=set();groups=[]
 for p in pairs:
  group=p['pair_id'];members=p['module_node_ids'];chains=p['source_chains']
  if group in ids or len(members)!=2 or len(set(members))!=2 or len(chains)!=2 or used.intersection(members):raise ValueError('Group members are not disjoint and unique')
  if not 0<=p['native_gap']<=100:raise ValueError('Group gap outside calibrated candidate profile')
  for nid,chain in zip(members,chains):
   n=nodes.get(nid)
   if not n or n.get('node_type')!='equipment' or n.get('display_source_chain')!=chain or n.get('source_assembly_candidate'):raise ValueError('Stale or competing source body')
  for nid in members:
   peer=next(x for x in members if x!=nid)
   nodes[nid]['source_assembly_candidate']={'group_id':group,'peer_node_id':peer,'native_gap':p['native_gap'],
      'caption_handles':evidence['caption_03_handles'],'source_03_sha256':source_03_sha256,'source_02_sha256':source_02_sha256,
      'status':'source_pair_candidate_not_hydraulically_merged','scope':'Project note and aligned source modules support a pair candidate; no 02 tag mapping or port connection is asserted.'}
  groups.append({'id':group,'members':members,'status':'source_pair_candidate_not_hydraulically_merged','native_gap':p['native_gap'],
    'source_chains':chains,'source_03_sha256':source_03_sha256,'source_02_sha256':source_02_sha256})
  ids.add(group);used.update(members)
 if out.get('sourceEquipmentAssemblies'):raise ValueError('Do not overwrite existing assembly inventory')
 out['sourceEquipmentAssemblies']=groups
 return out,{'pair_candidates':len(groups),'member_nodes':len(used),'nodes_merged':0,'edges_unchanged':out['edges']==graph['edges'],
             'source_03_sha256':source_03_sha256,'source_graph_sha256':graph_sha256,'source_02_sha256':source_02_sha256}
