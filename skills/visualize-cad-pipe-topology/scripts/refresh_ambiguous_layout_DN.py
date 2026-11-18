"""Adopt re-used layout DN through the actual complete app attribute reader."""
import argparse, copy, hashlib, json, shutil, zipfile
from pathlib import Path
import refresh_attribute_templates as base
from refresh_reviewed_ring_partition_DN import effective
from refresh_typed_inline_attribute_DN import delta
from reapply_ambiguous_layout_DN import verify_output, MODE as NATIVE_MODE, DIRECT, BEND

sha, load, encode = base.sha, base.load, base.encoded
MODE = 'qualified_ambiguous_layout_vertical_DN_viewer_v1'
AUDIT = 'ambiguous-layout-DN-refresh.json'
EVIDENCE = 'ambiguous-layout-DN-refresh'
TEMPLATE = 'public/axis-rule-vertical-DN.js'
key = lambda r: (r['edge_id'],r['path_index'],r['segment_index'])


def context_from(parent, proof, path):
    m = load(Path(parent)/'public/data/manifest.json'); c = copy.deepcopy(m['attributeValueContext'])
    root = c['axis_rule_vertical_DN']; oldkeys = {key(r) for r in root['records']}
    edges = {e['edge_id']:e for e in load(Path(parent)/'public/data/graph.json')['edges']}
    if (proof['mode'] != NATIVE_MODE or proof['human_accepted'] is not False or proof['graph_mutated'] is not False
            or proof['components_reassigned'] is not False or proof['physical_lengths_assigned'] != 0
            or proof['horizontal_values_assigned'] != 0 or proof['whole_edge_DN_assigned'] != 0
            or proof['original_readers_and_thresholds_unchanged'] is not True
            or proof['all_target_texts_excluded_from_controls'] is not True):
        raise ValueError('original layout source qualification required')
    if (sha(Path(parent)/'public/data/manifest.json') != proof['inputs']['parent_viewer_manifest']['sha256']
            or c['current_rendered_graph_sha256'] != sha(Path(parent)/'public/data/graph.json')
            or root['all_current_vertical_domains'] != proof['counts']['previous_known']
            or root['source_bindings']['native_source'] != proof['inputs']['axis_source']['sha256']
            or root['source_bindings']['native_graph'] != proof['inputs']['axis_graph']['sha256']):
        raise ValueError('current complete parent differs')
    new = []
    for r in proof['records']:
        k = key(r); edge = edges[k[0]]; seed = r.get('seed_record',r); owners = [o['native_evidence'] for o in seed['observations']]
        if (k in oldkeys or r['system'] != edge['system'] or r['connection_rule'] not in (DIRECT,BEND)
                or edge['attribute_paths'][k[1]][k[2]:k[2]+2] != r['scope_points']
                or r['physical_length_mm'] is not None or r['whole_edge_DN_assigned'] is not False
                or r['annotation_guard']['other_in_scope_DN_annotations'] or r['annotation_guard']['F_crossings']):
            raise ValueError('new exact vertical extent or transition guard differs')
        layout = []
        for owner in owners:
            controls = owner['independent_control_roots']; chain = owner['source_chain']
            if (len(set(controls)) < 4 or chain[0] in controls or owner['native_binding']['Z_coincident'] is not True
                    or owner['current_edge_id'] != k[0] or owner['nominal_mm_candidate'] != r['nominal_mm']):
                raise ValueError('original independent native controls differ')
            layout.append(dict(text_handle=owner['source_text']['handle'], source_chain=chain,
                independent_control_roots=controls, source_Z_checked=True))
        bend = r['connection_rule'] == BEND
        if bend and not r.get('continuity_evidence',{}).get('native_chain'):
            raise ValueError('source two-arm continuity missing')
        new.append(dict(edge_id=k[0],path_index=k[1],segment_index=k[2],system=r['system'],nominal_mm=r['nominal_mm'],
            scope_points=r['scope_points'],axis_source_sha256=proof['inputs']['axis_source']['sha256'],
            seed_text_handles=[o['source_text']['handle'] for o in owners],source_chains=[o['source_chain'] for o in owners],
            seed_domains=[{f:seed[f] for f in ('edge_id','path_index','segment_index','system','nominal_mm')}],
            source_rules=[r['connection_rule']],layout_ownership=layout,original_layout_reader_and_thresholds_unchanged=True,
            target_texts_used_as_controls=False,annotation_barriers_checked=True,native_two_arm_continuity_replayed=bend,
            physical_length_mm=None,whole_edge_DN_assigned=False,related_HIL_confirmation_inherited=False,human_accepted=False))
    if len(new) != proof['counts']['new_known'] or len({key(r) for r in new}) != len(new):
        raise ValueError('new layout population differs')
    root['history_before_ambiguous_layout_DN'] = {k:copy.deepcopy(v) for k,v in root.items() if k!='records'}
    root['records'].extend(new); root.update(count=len(root['records']),all_current_vertical_domains=proof['counts']['current_known'],
        remaining_unknown=proof['counts']['remaining_unknown'])
    root['source_bindings']['native_proof'] = sha(path)
    return json.loads(encode(c))


def provider_from(proof,path):
    p = copy.deepcopy(load(proof['inputs']['parent_provider']['path']))
    if p['counts']['all_current_vertical_DN_domains'] != proof['counts']['previous_known']:
        raise ValueError('complete source parent provider differs')
    p['history_before_ambiguous_layout_DN'] = dict(counts=copy.deepcopy(p['counts']),mode=p['mode'])
    p['counts']['all_current_vertical_DN_domains'] = proof['counts']['current_known']
    p['all_current_vertical_DN_domains'] = proof['counts']['current_known']
    p['ambiguous_layout_vertical_DN'] = dict(native_proof_sha256=sha(path),new_domains=len(proof['records']),human_accepted=False)
    p['mode'] = MODE
    return p


def refresh(parent,output,proof_path,templates,port):
    parent,output,proof_path,templates = map(lambda p:Path(p).resolve(),(parent,output,proof_path,templates))
    if output.exists() or output.with_suffix('.zip').exists(): raise FileExistsError(output)
    proof = verify_output(proof_path.parent); inventory = base.artifact_inventory(parent)
    c = context_from(parent,proof,proof_path); old = effective(parent); m = load(parent/'public/data/manifest.json')
    new_rows = c['axis_rule_vertical_DN']['records'][len(m['attributeValueContext']['axis_rule_vertical_DN']['records']):]
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));shutil.copy2(templates/TEMPLATE,output/TEMPLATE)
    revised = copy.deepcopy(m); revised['attributeValueContext']=c
    (output/'public/data/manifest.json').write_bytes(encode(revised)); actual=effective(output); change=delta(old,actual,c,new_rows)
    digest=hashlib.sha256(encode(actual)).hexdigest();revised['preferredPort']=port;revised['templateHashes'][TEMPLATE]=sha(output/TEMPLATE)
    revised['sourceHashes']['ambiguous_layout_DN']=sha(proof_path)
    revised['reviewContentHashes'].update(effective_edge_attributes=digest,attribute_value_context=hashlib.sha256(encode(c)).hexdigest())
    revised['ambiguousLayoutDNRefresh']=dict(mode=MODE,parent_bundle_id=m['bundleId'],native_proof_sha256=sha(proof_path),
        implementation_sha256=sha(__file__),human_confirmation_inherited=False)
    revised['bundleId']=hashlib.sha256(encode(dict(parent=m['bundleId'],proof=sha(proof_path),effective=digest,
        template=sha(output/TEMPLATE),implementation=sha(__file__),port=port))).hexdigest()[:20]
    (output/'public/data/manifest.json').write_bytes(encode(revised));index=output/'public/index.html'
    index.write_text(index.read_text(encoding='utf-8').replace(m['bundleId'],revised['bundleId']),encoding='utf-8')
    folder=output/EVIDENCE;folder.mkdir()
    for name,value in [('provider-inventory.json',provider_from(proof,proof_path)),('current-effective.json',actual)]:
        (folder/name).write_bytes(encode(value))
    shutil.copy2(proof_path,folder/'native-proof.json')
    from source_readability import read_source
    from validate_visualization import validate_bundle
    from post_drawing_gate import check
    source=proof['inputs']['axis_source']['path'];doc,preflight=read_source(source)
    schema=validate_bundle(output,native_doc=doc,native_source_sha256=sha(source));(output/'validation-report.json').write_bytes(encode(schema))
    quality=check(output,source)
    if schema['status']!='passed' or quality['machine_status']!='PASS': raise ValueError('native viewer schema/source gate failed')
    for name,h in inventory.items():
        if name.startswith(('public/data/','annotations/')) and name!='public/data/manifest.json' and sha(output/name)!=h:
            raise ValueError('source payload or annotations changed')
    if base.artifact_inventory(parent)!=inventory:raise ValueError('parent changed')
    a=dict(mode=MODE,status='source_and_actual_reader_passed_browser_pending',parent=str(parent),parent_file_hashes=inventory,
        proof_path=str(proof_path),proof_sha256=sha(proof_path),bundle_id=revised['bundleId'],template_sha256=sha(output/TEMPLATE),
        delta=change,new_rows=new_rows,source_preflight=preflight,human_accepted=False)
    a['output_hashes']=base.artifact_inventory(output);(output/AUDIT).write_bytes(encode(a))
    with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(base.inventory(output)):z.write(output/name,output.name+'/'+name)
    return a


def verify(output):
    output=Path(output);a=load(output/AUDIT);parent=Path(a['parent']);path=Path(a['proof_path']);proof=verify_output(path.parent)
    m=load(output/'public/data/manifest.json')
    if (a['mode']!=MODE or m['bundleId']!=a['bundle_id'] or sha(path)!=a['proof_sha256']
            or sha(output/TEMPLATE)!=a['template_sha256'] or sha(__file__)!=m['ambiguousLayoutDNRefresh']['implementation_sha256']
            or base.artifact_inventory(parent)!=a['parent_file_hashes']
            or {n:h for n,h in base.artifact_inventory(output).items() if n!=AUDIT}!=a['output_hashes']
            or context_from(parent,proof,path)!=m['attributeValueContext']):raise ValueError('viewer source/context/artifacts changed')
    if (delta(effective(parent),effective(output),m['attributeValueContext'],a['new_rows'])!=a['delta']
            or encode(provider_from(proof,path))!=(output/EVIDENCE/'provider-inventory.json').read_bytes()):
        raise ValueError('actual complete reader or provider differs')
    return dict(status='pending',artifact_replay='passed',bundle_id=a['bundle_id'],delta=a['delta'],human_accepted=False)


def main():
    p=argparse.ArgumentParser()
    for k in ('parent','output','proof','templates','verify-output'):p.add_argument('--'+k,type=Path)
    p.add_argument('--port',type=int);a=p.parse_args()
    r=verify(a.verify_output) if a.verify_output else refresh(a.parent,a.output,a.proof,a.templates,a.port)
    print(json.dumps({k:v for k,v in r.items() if k in ('status','artifact_replay','bundle_id','delta')},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
