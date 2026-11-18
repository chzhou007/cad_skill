"""Pin current read-only frontend readers from templates and audited ancestry.

The supplied current audit digest is the trust anchor. Each ancestor JS byte
must match its child-recorded inventory. Native correctness is still replayed
by the original current verifier; this tool constructs no graph values.
"""
import argparse,importlib,json,sys
from pathlib import Path
from current_attribute_read_runtime import MODE,command,command_inputs,module_closure
from native_attribute_read_runtime import sha,function_fingerprint

READERS=(('refresh_anchored_native_plan_metrics','effective_attributes'),
 ('refresh_anchored_terminal_branches','effective'),
 ('refresh_anchor_bounded_main_attributes','effective_attributes'),
 ('refresh_attribute_templates','effective_attributes'),
 ('refresh_axis_rule_vertical_DN','effective'),
 ('refresh_complementary_plan_attributes','effective'),
 ('refresh_compound_member_attributes','effective_attributes'),
 ('refresh_confirmed_member_attributes','effective_attributes'),
 ('refresh_continuous_axis_DN','effective'),
 ('refresh_native_two_arm_routes','effective'),
 ('refresh_nested_direct_axis_DN','effective'),
 ('refresh_nested_paired_axis_DN','effective'),
 ('refresh_noncompound_main_attributes','effective_attributes'),
 ('refresh_ordered_branch_attributes','effective_attributes'),
 ('refresh_ordered_group_attributes','effective_attributes'),
 ('refresh_plan_crossover_centrelines','effective'),
 ('refresh_reviewed_ring_partition_DN','effective'))

def build(root,viewer,audit_sha256):
    root,viewer=Path(root).resolve(),Path(viewer).resolve()
    audit=viewer/'effective-provider-refresh.json'
    if sha(audit)!=audit_sha256:raise ValueError('current audit trust anchor differs')
    modules={};evidence=[];bundles=[];pending=[(viewer,json.loads(audit.read_text('utf8'))['output_hashes'])];seen=set()
    inherited=root/'orchestrate-cad-drawing-pipeline/assets/pure-attribute-reader-policy.json'
    old=json.loads(inherited.read_text('utf8'))
    if old.get('mode')!='shipped_pure_attribute_reader_inputs_v1':raise ValueError('original pure reader policy required')
    # Inherit every already qualified legacy version; do not rediscover a
    # historical module merely because its current audit shape is older.
    for name,versions in old['module_sha256'].items():modules.setdefault(name,set()).update(versions)
    def add(folder,inventory):
        for name,digest in inventory.items():
            p=folder/name
            if not(name.startswith('public/')and name.endswith('.js')and p.parent==folder/'public'):continue
            if p.is_symlink()or sha(p)!=digest:raise ValueError('audited frontend module bytes differ: '+str(p))
            modules.setdefault(p.name,set()).add(digest)
    while pending:
        folder,inventory=pending.pop()
        if folder in seen:continue
        seen.add(folder);add(folder,inventory);bundles.append(folder)
        for p in sorted(folder.glob('*.json')):
            try:value=json.loads(p.read_text('utf8'))
            except ValueError:continue
            if not isinstance(value,dict)or not isinstance(value.get('parent'),str):continue
            parent_inventory=next((value[k]for k in ('parent_files','parent_file_hashes')if isinstance(value.get(k),dict)),None)
            if parent_inventory is None:continue
            # A historical audit must itself be witnessed in the child inventory.
            if p!=audit and inventory.get(p.name)!=sha(p):continue
            evidence.append(dict(path=str(p),sha256=sha(p)))
            parent=Path(value['parent']).resolve()
            if(parent/'public/data/manifest.json').is_file():pending.append((parent,parent_inventory))
    templates=root/'visualize-cad-pipe-topology/assets/viewer/public'
    for p in templates.glob('*.js'):modules.setdefault(p.name,set()).add(sha(p))
    rows=[]
    for name,entry in READERS:
        module=importlib.import_module(name);path=root/'visualize-cad-pipe-topology/scripts'/(name+'.py')
        if Path(module.__file__).resolve()!=path:raise ValueError('reader resolved outside supplied skills')
        before=sha(path);fn=getattr(module,entry);scripts=set()
        for bundle in bundles:
            try:_,_,_,script=command_inputs(command(fn,bundle),bundle)
            except (ValueError,FileNotFoundError):continue
            scripts.add(script)
        if not scripts or sha(path)!=before:raise ValueError('reader has no stable qualified command: '+name)
        rows.append(dict(module=name,function=entry,module_sha256=before,function_fingerprint=function_fingerprint(fn),cli_script_sha256=sorted(scripts)))
    # Confirm the current actual facade is included, including transitive files.
    actual=importlib.import_module('refresh_reviewed_ring_partition_DN').effective
    entry,*_=command_inputs(command(actual,viewer),viewer)
    if any(h not in modules.get(n,set())for n,h in module_closure(entry).items()):raise ValueError('current actual facade closure is not audited')
    return dict(mode=MODE,readers=rows,module_sha256={k:sorted(v)for k,v in sorted(modules.items())},inherited_pure_reader_policy_sha256=sha(inherited),audited_ancestry=evidence,current_audit_sha256=audit_sha256,current_viewer=str(viewer),graph_values_generated=0,human_acceptance_inferred=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--skills-root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--viewer',type=Path,required=True);p.add_argument('--audit-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    for n in ['build-cad-pipe-topology','visualize-cad-pipe-topology']:sys.path.insert(0,str(a.skills_root/n/'scripts'))
    if a.output.exists():raise FileExistsError(a.output)
    value=build(a.skills_root,a.viewer,a.audit_sha256);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(dict(readers=len(value['readers']),module_names=len(value['module_sha256']),audited_ancestors=len(value['audited_ancestry'])),flush=True)
if __name__=='__main__':main()
