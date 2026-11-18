"""Publish exact vertical DN while retaining the component-only graph overlay."""
import argparse
import copy
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
for skill in ('build-cad-pipe-topology','orchestrate-cad-drawing-pipeline'):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/skill/'scripts'))
import refresh_attribute_templates as base
from confirm_crossview_paths import load,sha,encode
from refresh_reviewed_ring_partition_DN import effective
from refresh_typed_inline_attribute_DN import delta
from expanded_main_seed_bend_DN import verify_output, MODE as NATIVE_MODE, RULE

MODE='qualified_expanded_main_seed_bend_DN_viewer_v1'
AUDIT='expanded-main-seed-bend-refresh.json'
FOLDER='expanded-main-seed-bend-refresh'
TEMPLATE='public/axis-rule-vertical-DN.js'
key=lambda r:(r['edge_id'],r['path_index'],r['segment_index'])


def context_from(parent,proof,path):
    manifest=load(Path(parent)/'public/data/manifest.json');context=copy.deepcopy(manifest['attributeValueContext'])
    root=context['axis_rule_vertical_DN'];edges={e['edge_id']:e for e in load(Path(parent)/'public/data/graph.json')['edges']}
    actual=sha(Path(parent)/'public/data/graph.json');overlay=manifest.get('componentFragmentOverlay')
    attribute_hash=context['current_rendered_graph_sha256']
    if attribute_hash!=actual and (not overlay or overlay['current_graph_sha256']!=actual or overlay['parent_graph_sha256']!=attribute_hash):
        raise ValueError('explicit current component overlay required; never rebase old proof hashes')
    if (proof['mode']!=NATIVE_MODE or proof['complete_current_viewer_replayed'] is not True
        or proof['known_parent_and_seed_bytes_requalified_in_parent_replay'] is not True
        or proof['original_two_arm_and_annotation_owners_reused'] is not True
        or proof['graph_mutated'] is not False or proof['components_reassigned'] is not False
        or proof['horizontal_values_assigned']!=0 or proof['whole_edge_DN_assigned']!=0
        or proof['physical_lengths_assigned']!=0 or proof['human_accepted'] is not False):
        raise ValueError('complete source-replayed expansion/bend qualification required')
    if (sha(Path(parent)/'public/data/manifest.json')!=proof['inputs']['parent_viewer_manifest']['sha256']
        or root['all_current_vertical_domains']!=proof['counts']['previous_known']
        or root['source_bindings']['native_source']!=proof['inputs']['axis_source']['sha256']
        or root['source_bindings']['native_graph']!=proof['inputs']['axis_graph']['sha256']):
        raise ValueError('current native parent differs')
    oldkeys={key(r) for r in root['records']};new=[]
    for record in proof['records']:
        k=key(record);edge=edges[k[0]];continuity=record['continuity_evidence'];guard=record['annotation_guard']
        if (k in oldkeys or record['connection_rule']!=RULE or record['system']!=edge['system']
            or edge['attribute_paths'][k[1]][k[2]:k[2]+2]!=record['scope_points']
            or abs(record['scope_points'][0][0]-record['scope_points'][1][0])>.05
            or record['physical_length_mm'] is not None or record['whole_edge_DN_assigned'] is not False
            or guard['other_in_scope_DN_annotations'] or guard['F_crossings']
            or not continuity['bends'] or any(b['source_arms']!=2 or b['physical_T_crossed'] is not False for b in continuity['bends'])):
            raise ValueError('exact vertical extent, two-arm continuity or caption barriers differ')
        owners=[];domains={}
        for seed in record['all_qualified_same_path_seeds']:
            expansion=seed['source_scope_expansion']
            if (key(seed)[:2]!=k[:2] or seed['nominal_mm']!=record['nominal_mm']
                or expansion['branch_DN_used_as_main_seed'] is not False):
                raise ValueError('source main seed escaped its original path')
            domains[key(seed)]={f:seed[f] for f in ('edge_id','path_index','segment_index','system','nominal_mm')}
            through=sorted({j['node_id']for p in expansion['junctions']for j in p['junctions']})
            owners.extend(dict(text_handle=o['source_text']['handle'],source_LINE=seed['source_line_handle'],
                nominal_mm=seed['nominal_mm'],system=seed['system'],source_Z=seed['source_Z'],
                through_T_node_ids=through,source_LINE_scope_native_replayed=True) for o in seed['observations'])
        new.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],system=record['system'],
            scope_points=record['scope_points'],nominal_mm=record['nominal_mm'],source_rules=[RULE],
            axis_source_sha256=proof['inputs']['axis_source']['sha256'],seed_text_handles=sorted({o['text_handle']for o in owners}),
            seed_domains=list(domains.values()),main_line_handles=sorted({o['source_LINE']for o in owners}),
            source_chains=[[s['root_handle'],s['child_handle']]for s in continuity['native_chain']],
            expanded_main_seed_owners=owners,two_arm_bends=[{f:b[f]for f in ('point_xy','source_Z','source_arms','physical_T_crossed')}for b in continuity['bends']],
            original_caption_owner_rules_replayed=True,source_LINE_scope_expansion_replayed=True,
            native_two_arm_continuity_replayed=True,same_original_path_seed=True,branch_DN_used_as_main_seed=False,
            annotation_barriers_checked=True,physical_length_mm=None,whole_edge_DN_assigned=False,
            related_HIL_confirmation_inherited=False,human_accepted=False))
    if len(new)!=proof['counts']['new_known'] or len({key(r)for r in new})!=len(new):raise ValueError('new domain census differs')
    root['history_before_expanded_main_seed_bend_DN']={f:copy.deepcopy(v)for f,v in root.items()if f!='records'}
    root['records'].extend(new);root.update(count=len(root['records']),
        all_current_vertical_domains=proof['counts']['current_known'],remaining_unknown=proof['counts']['remaining_unknown'])
    root['source_bindings']['native_proof']=sha(path)
    return json.loads(encode(context))


def provider_from(proof,path):
    prior=load(proof['inputs']['parent_provider']['path']);result=copy.deepcopy(prior)
    if prior['counts']['all_current_vertical_DN_domains']!=proof['counts']['previous_known']:raise ValueError('current provider count differs')
    result['history_before_expanded_main_seed_bend_DN']=dict(mode=prior['mode'],counts=copy.deepcopy(prior['counts']))
    result['mode']=MODE;result['counts']['all_current_vertical_DN_domains']=proof['counts']['current_known']
    result['all_current_vertical_DN_domains']=proof['counts']['current_known']
    result['expanded_main_seed_bend_DN']=dict(native_proof_sha256=sha(path),new_vertical_domains=len(proof['records']),human_accepted=False)
    return result


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates=map(Path,(parent,output,proof_path,templates))
    if output.exists()or output.with_suffix('.zip').exists():raise FileExistsError(output)
    proof=verify_output(proof_path.parent);before=base.artifact_inventory(parent)
    original=load(parent/'public/data/manifest.json');context=context_from(parent,proof,proof_path)
    rows=context['axis_rule_vertical_DN']['records'][len(original['attributeValueContext']['axis_rule_vertical_DN']['records']):]
    old=effective(parent);shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(templates/TEMPLATE,output/TEMPLATE);manifest=copy.deepcopy(original);manifest['attributeValueContext']=context
    (output/'public/data/manifest.json').write_bytes(encode(manifest));actual=effective(output);change=delta(old,actual,context,rows)
    manifest['preferredPort']=port;manifest['templateHashes'][TEMPLATE]=sha(output/TEMPLATE)
    manifest['sourceHashes']['expanded_main_seed_bend_DN']=sha(proof_path)
    manifest['reviewContentHashes'].update(effective_edge_attributes=hashlib.sha256(encode(actual)).hexdigest(),attribute_value_context=hashlib.sha256(encode(context)).hexdigest())
    manifest['expandedMainSeedBendDNRefresh']=dict(mode=MODE,parent_bundle_id=original['bundleId'],native_proof_sha256=sha(proof_path),implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    manifest['bundleId']=hashlib.sha256(encode(dict(parent=original['bundleId'],proof=sha(proof_path),template=sha(output/TEMPLATE),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(manifest));index=output/'public/index.html';index.write_text(index.read_text(encoding='utf-8').replace(original['bundleId'],manifest['bundleId']),encoding='utf-8')
    folder=output/FOLDER;folder.mkdir()
    for name,value in [('provider-inventory.json',provider_from(proof,proof_path)),('current-effective.json',actual)]:
        (folder/name).write_bytes(encode(value))
    shutil.copy2(proof_path,folder/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source)
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema));quality=check(output,source)
    if schema['status']!='passed'or quality['machine_status']!='PASS':raise ValueError('source/schema gate failed')
    if base.artifact_inventory(parent)!=before:raise ValueError('parent mutated')
    for name,h in before.items():
        if name.startswith(('public/data/','annotations/'))and name!='public/data/manifest.json'and sha(output/name)!=h:raise ValueError('old graph/data/annotations changed')
    audit=dict(mode=MODE,parent=str(parent),parent_files=before,proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=manifest['bundleId'],new_rows=rows,delta=change,source_preflight=preflight,human_accepted=False)
    audit['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(audit))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED)as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    return audit


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent)
    m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or sha(path)!=a['proof_sha256']or a['bundle_id']!=m['bundleId']
        or m['expandedMainSeedBendDNRefresh']['implementation_sha256']!=sha(__file__)
        or base.artifact_inventory(parent)!=a['parent_files']
        or {n:h for n,h in base.artifact_inventory(output).items()if n!=AUDIT}!=a['output_hashes']
        or context_from(parent,proof,path)!=m['attributeValueContext']
        or delta(effective(parent),effective(output),m['attributeValueContext'],a['new_rows'])!=a['delta']
        or encode(provider_from(proof,path))!=(output/FOLDER/'provider-inventory.json').read_bytes()):
        raise ValueError('expanded main/bend viewer source, values or provider differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=m['bundleId'],delta=a['delta'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for n in ('parent','output','proof','templates','verify-output'):p.add_argument('--'+n,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        r=verify(a.verify_output)if a.verify_output else refresh(a.parent,a.output,a.proof,a.templates,a.port)
    print({k:v for k,v in r.items()if k in ('mode','status','artifact_replay','bundle_id','delta')},flush=True)


if __name__=='__main__':main()
