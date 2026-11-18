"""Apply rebuilt member intervals and precisely cleared cycle metrics.

Native readers still own labels, units and path lengths. This owner establishes
the new member endpoints and preserves riser-symbol offsets as unknown lengths.
"""
import argparse,copy,hashlib,importlib,json,math,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_replay_session import verify_once
from rebuild_compound_riser_header_members import verify_output as member_owner
from rebuild_compound_carrier_atom_origins import verify_output as origin_owner
from rebuild_anchored_cycle_gate_batch import verify_output as gate_owner
from cycle_gate_plan_lengths import verify_output as metric_owner
from axis_attribute_source_routing import verify_output as direction_owner
from native_plan_projection_lengths import unit_evidence,lengths
from native_main_interval_metrics import touching_projection
from batch_native_path_coverage import collect as coverage
from native_paired_caption_geometry import collect as captions
from compound_member_interfaces import native_label_guard
from native_line_path_evidence import _on
MODE='native_reanchored_riser_header_interval_application_v1'

class CaptionOwnedProjection:
    """Exclude only captions already read by the exact member declaration owner."""
    def __init__(self,doc,handles):self.doc=doc;self.handles=set(handles)
    def __getattr__(self,name):return getattr(self.doc,name)
    def modelspace(self):return self
    def query(self,query):return [e for e in self.doc.modelspace().query(query)if e.dxf.handle not in self.handles]

def member_dn_guard(doc,edge,caption_evidence,origin):
    declared={x['text_handle']for x in edge['member']['plan_declarations']}
    if declared & set(origin['reserved_leader_texts']):raise ValueError('member caption has unresolved F/leader ownership')
    originals=[]
    for h in sorted(declared):
        ent=doc.entitydb.get(h)
        source=[d for c in origin['corridors']for d in c['declarations']if d['handle']==h]
        if ent is None or not source or any(d['raw_text']!=ent.plain_text()for d in source):raise ValueError('owned compound caption changed')
        originals.append(dict(handle=h,raw_text=ent.plain_text()))
    checks=native_label_guard(CaptionOwnedProjection(doc,declared),edge['source_handles'],edge['member']['nominal_mm'],caption_evidence)
    return dict(owned_compound_captions=originals,other_native_DN_checks=checks,source_document_mutated=False,F_precedence_preserved=True)

def clear_cycle_records(metric_records,held,origin,plan):
    by={e['edge_id']:e for e in plan['edges']};old={r['axis_edge_id']:r for r in held};records=[];pending=[]
    for row in metric_records:
        eid=row['axis_edge_id'];prior=old.get(eid)
        if not prior:raise ValueError('metric is not one of the original held scopes')
        if prior['mapping_id']!=row['mapping_id']or prior['plan_edge_id']!=row['plan_edge_id']or prior['prior_complete_centerline_mm']!=row['complete_horizontal_centerline_mm']:raise ValueError('old held metric scope differs')
        edge=by[row['plan_edge_id']];remaining=[c for c in origin['corridors']if c['system']==edge['system']and c['source_LINE']in edge.get('source_handles',[])and any(_on(a,*c['native_endpoints'],.05)and _on(b,*c['native_endpoints'],.05)for p in edge['attribute_paths']for a,b in zip(p,p[1:]))]
        if remaining:pending.append(dict(axis_edge_id=eid,reason='remaining_native_compound_member_barrier'));continue
        excluded={(x['source_LINE'],x['declaration']['handle']):x for x in origin['excluded_other_arm_origins']};proof=[]
        for barrier in prior['barriers']:
            for d in barrier['declarations']:
                p=excluded.get((barrier['source_LINE'],d['handle']))
                if p is None:raise ValueError('old origin was not independently excluded')
                proof.append(p)
        records.append(dict(axis_edge_id=eid,mapping_id=row['mapping_id'],plan_edge_id=row['plan_edge_id'],system=row['system'],axis_nodes=row['axis_nodes'],axis_attribute_paths=row['axis_attribute_paths'],complete_horizontal_centerline_mm=row['complete_horizontal_centerline_mm'],excluded_native_origins=proof,source_plan_scope_no_remaining_compound_barrier=True,physical_metric_native_replayed=True,related_HIL_confirmation_inherited=False,human_accepted=False))
    if set(old)!={r['axis_edge_id']for r in metric_records}:raise ValueError('incomplete original held metric population')
    return records,pending

def compute(manifest):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in inputs.items()):raise ValueError('riser interval input changed')
    checked();parent=load(paths['parent_manifest']);context=parent['attributeValueContext'];members=verify_once(paths['member_proof'].parent,member_owner);origins=verify_once(paths['atom_proof'].parent,origin_owner);gates=verify_once(paths['cycle_gate_proof'].parent,gate_owner);metrics=verify_once(paths['cycle_metric'].parent,metric_owner);routes=verify_once(paths['routing_proof'].parent,direction_owner)
    for data,key in[(members,'member_proof'),(origins,'atom_proof'),(gates,'cycle_gate_proof'),(metrics,'cycle_metric'),(routes,'routing_proof')]:
        if encode(data)!=paths[key].read_bytes():raise ValueError('riser interval parent replay differs')
    plan,axis,raw,rendered=[load(paths[k])for k in('plan_graph','axis_graph','raw_axis_graph','rendered_graph')];floor=manifest['floor'];f=str(floor)
    for artifact,key,ik in[(members,'plan_graph','plan_graph'),(members,'plan_source','plan_source'),(members,'axis_graph','axis_graph'),(members,'axis_source','axis_source'),(metrics,'plan_graph','plan_graph'),(metrics,'plan_source','plan_source'),(metrics,'axis_graph','axis_graph'),(gates,'plan_graph_'+f,'plan_graph'),(gates,'plan_source_'+f,'plan_source'),(gates,'axis_graph','axis_graph'),(gates,'axis_source','axis_source'),(origins,'plan_graph_'+f,'plan_graph'),(origins,'plan_source_'+f,'plan_source')]:
        if artifact['inputs'][key]['sha256']!=inputs[ik]['sha256']:raise ValueError('member/metric/anchor source ancestry differs')
    if routes['inputs']['graph']['sha256']!=inputs['axis_graph']['sha256']or routes['inputs']['source']['sha256']!=inputs['axis_source']['sha256']:raise ValueError('member interval routing source differs')
    if context['source_graph_sha256']!=sha(paths['raw_axis_graph'])or context['rendered_graph_sha256']!=sha(paths['rendered_graph'])or context['graph_first_extensions']['source_bindings']['cycle_metric_proof']!=sha(paths['cycle_metric']):raise ValueError('riser application viewer ancestry differs')
    doc,preflight=read_source(paths['plan_source']);units=unit_evidence(doc,load(paths['unit_policy']));cap=captions(doc);origin=origins['floors'][f];ae={e['edge_id']:e for e in axis['edges']};re={e['edge_id']:e for e in raw['edges']};ve={e['edge_id']:e for e in rendered['edges']};route={e['edge_id']:e for e in routes['edges']};records=[];pending=[]
    for group in members['records']:
        scope=group['scoped_graph'];nodes={n['node_id'].rsplit(':',1)[1]:n for n in scope['nodes']};edges={e['edge_id'].rsplit(':',1)[1]:e for e in scope['edges']};gate=nodes['gate']['source_node_id'];approach=ae[edges['approach']['candidate_axis_edge']];axgate=next(n for n in(approach['start_node_id'],approach['end_node_id'])if n!=group['new_axis_tee'])
        if group['floor']!=floor or gates['floors'][f]['new_junction_mapping'].get(gate)!=axgate or group['lower_terminal_identity_selected']is not False:raise ValueError('rebuilt member gate lacks its independently revalidated identity')
        for kind in('approach','riser'):
            e=edges[kind];eid=e['candidate_axis_edge'];axis_edge=ae[eid]
            if route[eid]['classification']!='horizontal_only'or any(axis_edge.get(k)!=floor for k in('floor_start','floor_end')):raise ValueError('member interval contains a vertical or foreign-floor segment')
            if any(axis_edge.get(k)!=re[eid].get(k)or re[eid].get(k)!=ve[eid].get(k)for k in('edge_id','start_node_id','end_node_id','system','attribute_paths')):raise ValueError('member axis source/rendered extent differs')
            row=dict(plan_edges=[e['edge_id']],system=e['system']);digest=hashlib.sha256(encode(scope)).hexdigest();cov=coverage(doc,scope,row['plan_edges'],inputs['plan_source']['sha256'],digest)
            try:projection=lengths(scope,cov,row,units)
            except ValueError:projection=touching_projection(scope,cov,row,units)
            try:guard=member_dn_guard(doc,e,cap,origin);nominal=e['member']['nominal_mm'];dn_status='native_plan_member_declaration_and_direct_labels_checked'
            except ValueError as exc:guard=dict(conflict=str(exc));nominal=None;dn_status='native_plan_member_DN_conflict';pending.append(dict(axis_edge_id=eid,reason=str(exc)))
            complete=projection['value_mm']if kind=='approach'else None
            if kind=='approach'and (nodes['tee']['node_type']!='tee'or nodes['gate']['source_node_id']!=gate):raise ValueError('approach endpoint proof differs')
            row=dict(mapping_id='RISER-MEMBER-'+hashlib.sha256(encode([group['scope_id'],kind,eid])).hexdigest()[:16],axis_edge_id=eid,system=e['system'],floor=floor,axis_nodes=[axis_edge['start_node_id'],axis_edge['end_node_id']],axis_attribute_paths=axis_edge['attribute_paths'],member_scope_id=group['scope_id'],plan_member_edge_id=e['edge_id'],member_kind=kind,plan_attribute_paths=e['attribute_paths'],nominal_mm=nominal,DN_status=dn_status,member_declaration=e['member'],native_DN_guard=guard,complete_horizontal_centerline_mm=complete,drawn_plan_projection_mm=projection['value_mm'],projection=projection,native_plan_coverage=cov,endpoint_evidence=dict(plan_gate=gate,axis_gate=axgate,plan_circle=group['source_circle'],axis_tee=group['new_axis_tee'],native_axis_T_evidence=group['native_axis_T_evidence'],riser_symbol_offset_added_to_length=False),source_component_ids=e['component_ids'],unshown_connection_length_mm=None,installed_length_mm=None,net_pipe_cut_length_mm=None,source_paths_mutated=False,lower_terminal_identity_selected=False,related_HIL_confirmation_inherited=False,human_accepted=False)
            records.append(row)
    clearances,held=clear_cycle_records(metrics['records'],context['cycle_carrier_guards']['records'],origin,plan);pending.extend(held)
    if len({r['axis_edge_id']for r in records+clearances})!=len(records)+len(clearances):raise ValueError('competing member and cycle writers')
    checked();return dict(mode=MODE,inputs=inputs,member_records=records,cycle_clearances=clearances,pending=pending,counts=dict(member_intervals=len(records),member_DN_known=sum(r['nominal_mm']is not None for r in records),member_complete_lengths=sum(r['complete_horizontal_centerline_mm']is not None for r in records),cleared_cycle_metrics=len(clearances)),units=units,source_preflight=preflight,independent_gate_ancestry_replayed=True,member_and_origin_native_sources_replayed=True,old_graphs_unchanged=True,all_horizontal_values_from_plan=True,vertical_values_assigned=0,installed_lengths_assigned=0,lower_terminal_identities_assigned=0,human_accepted=False,viewer_publication_pending=True)

def implementation_hashes():
    names=('rebuild_compound_riser_header_members','rebuild_compound_carrier_atom_origins','rebuild_anchored_cycle_gate_batch','cycle_gate_plan_lengths','axis_attribute_source_routing','native_plan_projection_lengths','native_main_interval_metrics','batch_native_path_coverage','native_paired_caption_geometry','compound_member_interfaces','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('riser application implementation changed')
    output.mkdir(parents=True);p=output/'riser-header-intervals.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'riser-header-intervals.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('riser application receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('riser application source replay differs')
    return r
def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if a.verify_output:r=verify_output(a.verify_output)
        else:
            if not a.manifest or not a.output:p.error('manifest and new output required')
            r=produce(a.manifest,a.output)
    print(dict(r['counts'],pending=r['pending']),flush=True)
if __name__=='__main__':main()
