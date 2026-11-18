"""Consume an explicit expert compound-pipe meaning without inventing LINE IDs."""
import argparse,copy,hashlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from compound_pipe_label_evidence import verify as verify_labels,collect
from source_readability import read_source

MODE='expert_confirmed_compound_pipe_lane_semantics_v1'

def resolve(observations,reply,policy):
    answer=reply['answers'][policy['question_id']]
    if (hashlib.sha256(encode(answer)).hexdigest()!=policy['answer_sha256']or answer['source_pair_sha256']!=policy['source_pair_sha256']
        or reply['source_evidence']['source_sha256']!=policy['source_sha256']or not policy.get('two_distinct_overlapping_pipes')is True):raise ValueError('explicit reply meaning/source binding differs')
    expected=policy['nominals_mm'];detail=policy['sideview_nominal_mm'];handles=policy['text_handles']
    if len(expected)!=2 or len(set(expected))!=2 or detail not in expected or len(set(handles))!=len(handles)or not handles:raise ValueError('two distinct source lane members required')
    by={r['handle']:r for r in observations['records']}
    if len(by)!=len(observations['records'])or not set(handles)<=set(by):raise ValueError('compound declaration source scope missing or duplicated')
    rows=[]
    for handle in handles:
        row=by[handle]
        if row['source_sha256']!=policy['source_sha256']or sorted(m['nominal_mm']for m in row['members'])!=sorted(expected):raise ValueError('native compound members differ from confirmed source scope')
        members=[]
        for item in row['members']:
            members.append(dict(item,declaration_slot_id=f'DECL:{row["source_sha256"][:12]}:{handle}:{item["declaration_index"]}',
                role='sideview_network_lane'if item['nominal_mm']==detail else'other_lane_separated_in_axis_view',
                physical_pipe_id=None,source_LINE_identity=None,physical_length_mm=None))
        rows.append(dict(source_text=copy.deepcopy(row),handle=handle,multiple_physical_pipes_confirmed=True,members=members,
            confirmation_basis=dict(question_id=policy['question_id'],source_pair_sha256=policy['source_pair_sha256'],answer_sha256=policy['answer_sha256']),
            declarations_are_not_unique_pipe_instances=True,scalar_whole_edge_DN_mm=None,source_LINE_membership_confirmed=False,
            parenthesis_datum_or_units_confirmed=False,topology_connections_assigned=0,human_accepted=False))
    return dict(mode=MODE,records=rows,confirmed_declarations=len(rows),confirmed_declaration_slots=sum(len(r['members'])for r in rows),
        other_source_declarations=[r['handle']for r in observations['records']if r['handle']not in handles],
        physical_pipe_instances_created=0,scalar_DN_assignments=0,source_LINE_assignments=0,physical_lengths_assigned=0,graph_mutated=False,human_accepted=False)

def implementation_hashes():
    return {p.name:sha(p)for p in (Path(__file__),Path(__file__).with_name('compound_pipe_label_evidence.py'),Path(__file__).with_name('source_readability.py'))}

def compute(manifest):
    for spec in manifest.values():
        if sha(spec['path'])!=spec['sha256']:raise ValueError('confirmed compound input changed')
    run=Path(manifest['observations']['path']).parent;verified=verify_labels(run)
    if verified['source_replay']!='passed':raise ValueError('native compound observations not replayed')
    policy=load(manifest['policy']['path']);reply=load(manifest['reply']['path']);r=load(run/'receipt.json');doc,preflight=read_source(r['input']['path']);fresh=collect(doc,r['input']['sha256'])
    # The branch declaration in the side view is source text, not an allocation
    # to a main LINE. Read both actual handles before recording the semantic link.
    sideview=[]
    from compound_pipe_label_evidence import TOKEN
    for handle in policy['sideview_text_handles']:
        e=doc.entitydb.get(handle);match=TOKEN.fullmatch(e.plain_text().strip())if e is not None and e.dxftype()in('TEXT','MTEXT')else None
        if not match or float(match[1])!=policy['sideview_nominal_mm']:raise ValueError('native sideview caption differs')
        sideview.append(dict(handle=handle,raw_text=e.plain_text(),position=list(e.dxf.insert),source_sha256=r['input']['sha256']))
    result=resolve(fresh,reply,policy);result.update(source_preflight=preflight,native_sideview_DN_captions=sideview,expert_reply_sha256=manifest['reply']['sha256'],
        source_sha256=r['input']['sha256'],axis_topology_correspondence_confirmed=False)
    if any(sha(spec['path'])!=spec['sha256']for spec in manifest.values()):raise ValueError('compound input changed during replay')
    return result

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'confirmed-compound-lanes.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);r=load(output/'receipt.json');m=r['manifest'];target=output/'confirmed-compound-lanes.json'
    if r['mode']!=MODE or r['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=r['output_sha256']:raise ValueError('confirmed compound dependencies changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('confirmed compound native replay differs')
    return fresh

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification uses original manifest')
        r=verify_output(a.verify_output)
    else:
        if not(a.manifest and a.output):p.error('manifest and new output required')
        r=produce(a.manifest,a.output)
    print(dict(confirmed_declarations=r['confirmed_declarations'],declaration_slots=r['confirmed_declaration_slots'],unique_pipe_instances_created=0,source_LINE_assignments=0),flush=True)
if __name__=='__main__':main()
