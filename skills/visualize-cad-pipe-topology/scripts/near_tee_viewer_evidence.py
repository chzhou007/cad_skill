"""Attach source-bound near-tee review state to a viewer-only graph copy."""
import copy

def attach(graph,screen,graph_sha256,screen_sha256,extractor_sha256):
 if (not graph_sha256 or not screen_sha256 or not extractor_sha256 or screen.get('graph_sha256')!=graph_sha256
     or screen.get('source_sha256')!=graph.get('metadata',{}).get('source_sha256') or screen.get('script_sha256')!=extractor_sha256
     or screen.get('status')!='applied_near_tees_pending_review' or screen.get('graph_mutated') is not False
     or screen.get('human_accepted') is not False or screen.get('hil_ready') is not False):raise ValueError('stale near-tee evidence')
 result=copy.deepcopy(graph);nodes={n['node_id']:n for n in result['nodes']};edges=result['edges'];records=screen.get('records')
 if len(nodes)!=len(result['nodes']) or not isinstance(records,list) or not records or len({x.get('node_id') for x in records})!=len(records):raise ValueError('invalid near-tee records')
 for item in records:
  node=nodes.get(item.get('node_id'));incident=[e for e in edges if item.get('node_id') in (e.get('start_node_id'),e.get('end_node_id'))]
  main=item.get('main_handle');branch=item.get('branch_handle')
  if (not node or node.get('node_type')!='tee' or node.get('system')!=item.get('system') or item.get('status')!='source_normalized_tee_not_human_accepted'
      or len(incident)!=3 or sorted(e['edge_id'] for e in incident)!=item.get('incident_edge_ids')
      or any(e.get('system')!=node.get('system') for e in incident) or not main or not branch or main==branch
      or sum(main in e.get('source_handles',[]) for e in incident)!=2 or sum(branch in e.get('source_handles',[]) for e in incident)!=1
      or not {main,branch}<=set(node.get('source_handles',[]))):raise ValueError('near-tee incidence mismatch')
  if node.get('resolution_state') not in (None,'source_contact_reconstructed_pending_comparison'):raise ValueError('existing node review state needs reconciliation')
  node.update(resolution_state='source_contact_reconstructed_pending_comparison',review_required=True,source_near_tee_screen_sha256=screen_sha256)
 return result
