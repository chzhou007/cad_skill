"""Refine coarse composite-edge risk origins without assigning a pipe member.

A label near one arm of an edge must not seed every native LINE on that edge.
The original risk reader still owns grammar and geometry. Unsupported source
ownership or leader contexts retain the old barrier.
"""
import copy,math
from compound_carrier_members import carrier_risks
from compound_pipe_label_evidence import collect as compound_labels
from source_compound_dn_evidence import extract
from pipe_annotation_attributes import source_texts
from native_dn_text_position import supported
from native_line_path_evidence import LAYERS,_on
from native_paired_caption_geometry import leader_claims
from calibrated_direct_dn_evidence import profile
MODE='native_atom_scoped_compound_carrier_risks_v1'

def refine(doc,graph,source_hash):
    # The legacy risk owner requires explicit annotation layers. An empty native
    # declaration population is a valid no-risk drawing, not a failed scan.
    declarations=compound_labels(doc,source_hash)
    old=carrier_risks(doc,graph,source_hash)if declarations['records']else dict(status='native_compound_carrier_LINE_lineage_barriers_not_member_assignments',corridors=[],barriers_propagated_by_exact_source_LINE_not_proximity=True,scalar_DN_allowed_without_member_proof=False)
    atoms=[];origin={}
    for e in graph['edges']:
        for pi,path in enumerate(e.get('attribute_paths',[])):
            for si,(a,b)in enumerate(zip(path,path[1:])):
                eid='ATOM:'+e['edge_id']+':'+str(pi)+':'+str(si)
                row=dict(e,edge_id=eid,attribute_paths=[[copy.deepcopy(a),copy.deepcopy(b)]])
                atoms.append(row);origin[eid]=dict(edge_id=e['edge_id'],path_index=pi,segment_index=si,points=[a,b],system=e['system'],source_handles=e.get('source_handles',[]))
    text=source_texts(doc,'source',source_hash);layers={r['layer']for c in old['corridors']for r in c['declarations']}
    atomic=extract(text,atoms,layers)if layers else dict(records=[])
    declarations={r['source_text']['handle']:r for r in atomic['records']}
    observed=[]
    for h in declarations:
        ent=doc.entitydb.get(h)
        if ent is not None and supported(ent):observed.append(dict(handle=h,position=list(ent.dxf.insert)[:2],rotation=ent.dxf.rotation,profile=profile(doc,ent)))
    reserved=leader_claims(doc,observed)if observed else{}
    lines={s:[l for l in doc.modelspace().query('LINE')if l.dxf.layer==layer]for s,layer in LAYERS.items()};support={};kept=[];excluded=[]
    def owners(atom_id):
        if atom_id not in support:
            a=origin[atom_id];p,q=a['points'];hits=[l for l in lines[a['system']]if _on(p,list(l.dxf.start)[:2],list(l.dxf.end)[:2],.05)and _on(q,list(l.dxf.start)[:2],list(l.dxf.end)[:2],.05)]
            valid=len(hits)==1 and hits[0].dxf.handle in a['source_handles']
            support[atom_id]=dict(**a,source_LINE=hits[0].dxf.handle if valid else None,native_witness_handles=sorted(l.dxf.handle for l in hits),unique_modelspace_LINE=valid)
        return support[atom_id]
    for corridor in old['corridors']:
        retained=[]
        for declaration in corridor['declarations']:
            h=declaration['handle'];ent=doc.entitydb.get(h);row=declarations.get(h);reason=None;proof=[]
            if ent is None or not supported(ent)or ent.plain_text()!=declaration['raw_text']:reason='unsupported_or_changed_native_TEXT'
            elif h in reserved:reason='native_F_or_leader_precedence'
            elif not row or not row['candidate_edge_ids']:reason='no_atom_candidate_proves_another_origin'
            else:
                proof=[owners(a)for a in row['candidate_edge_ids']]
                if any(not p['unique_modelspace_LINE']for p in proof):reason='ambiguous_or_unsupported_atom_source'
                elif corridor['source_LINE']in {p['source_LINE']for p in proof}:reason='this_LINE_is_a_native_atom_candidate'
            if reason is not None:retained.append(declaration)
            else:excluded.append(dict(source_LINE=corridor['source_LINE'],declaration=copy.deepcopy(declaration),native_atom_origins=copy.deepcopy(proof),reason='coarse_composite_edge_other_arm_not_this_native_LINE',physical_member_identity_inferred=False))
        if retained:kept.append(dict(copy.deepcopy(corridor),declarations=retained))
    return dict(mode=MODE,original_risks=old,corridors=kept,excluded_other_arm_origins=excluded,native_atom_support=list(support.values()),reserved_leader_texts=reserved,
        original_risk_reader_reused=True,only_existing_candidate_origins_refined=True,source_or_graph_mutated=False,physical_members_assigned=0,DN_or_lengths_assigned=0,human_accepted=False)
