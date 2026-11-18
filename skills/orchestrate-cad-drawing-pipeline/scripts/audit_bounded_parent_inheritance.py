"""Audit exact historical runtime and test bytes before full parent replay.

This preflight deliberately calls the original strict checker. It cannot certify
the native computation or replace that computation's independent verifier.
"""
import argparse,hashlib,json
from pathlib import Path
from checked_bounded_attribute_parent import check,OWNER
from checked_native_parent_application import tree,sha,encode
MODE='inherited_bounded_parent_asset_audit_v1'

def audit(spec,current_root):
    root=Path(spec['skills_root']).resolve();current_root=Path(current_root).resolve();files=tree(root)
    if hashlib.sha256(encode(files)).hexdigest()!=spec['skill_tree_sha256']:raise ValueError('immutable historical asset tree changed')
    selected={n:h for n,h in files.items()if n.endswith('.py')and '/scripts/'in n and n.startswith(('build-cad-pipe-topology/','orchestrate-cad-drawing-pipeline/'))and n!='orchestrate-cad-drawing-pipeline/scripts/pipeline.py'}
    differences=[]
    for name,h in selected.items():
        p=current_root/name
        if not p.is_file()or sha(p)!=h:differences.append(dict(path=name,kind='test'if Path(name).name.startswith('test_')else'production',historical_sha256=h,current_sha256=sha(p)if p.is_file()else None))
    # No test exclusion, tolerance or alias is introduced here.
    if differences:raise ValueError('historical bounded parent assets differ: '+json.dumps(differences,ensure_ascii=False))
    checked_root,proof,_=check(spec,current_root)
    if checked_root!=root:raise ValueError('strict checker selected another historical root')
    return dict(mode=MODE,status='exact_asset_preflight_passed_native_replay_not_performed',owner=OWNER,immutable_skill_tree_sha256=spec['skill_tree_sha256'],historical_proof_sha256=sha(proof),checked_assets=selected,production_assets=sum(not Path(n).name.startswith('test_')for n in selected),test_assets=sum(Path(n).name.startswith('test_')for n in selected),original_strict_checker_used=True,tests_excluded_from_original_guard=False,native_replay_performed=False,human_accepted=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--current-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    m=json.loads(a.manifest.read_text(encoding='utf8'));r=audit(m['parent_application'],a.current_root);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(encode(r));print({k:v for k,v in r.items()if k!='checked_assets'},flush=True)
if __name__=='__main__':main()
