"""Apply version-bound HIL answers through registered native owners and publication.

Expert reply text is data, never executable instructions. A trusted catalog owns
the rule/manifest/command mapping. Existing verified applications are retained;
only unfamiliar or contradictory decisions enter the new-conflict queue.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

SCRIPTS = Path(__file__).resolve().parent
SKILLS = SCRIPTS.parent.parent
VIEWER = SKILLS/'visualize-cad-pipe-topology/scripts'
SCHEMA = 'cad_hil_feedback_pipeline_v1'

def load(path):
    return json.loads(Path(path).read_text('utf-8-sig'))

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def pin(path):
    path = Path(path).resolve()
    return {'path':str(path), 'sha256':digest(path)}

def checked(binding):
    path = Path(binding['path'])
    if not path.is_absolute() or not path.is_file() or digest(path) != binding['sha256']:
        raise ValueError('changed or missing bound input: '+str(path))
    return path

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.writing')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    os.replace(temporary,path)

def stable(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()

def semantics(answer):
    # Export time is not a new decision. Free-text comments are material until
    # an explicit registered authority has classified them.
    return {k:answer[k] for k in ('decision','comment') if answer.get(k) not in (None,'')}

def pointer(value, path):
    if not path.startswith('/'):
        raise ValueError('JSON pointer required')
    for key in path[1:].split('/'):
        key = key.replace('~1','/').replace('~0','~')
        value = value[int(key)] if isinstance(value,list) else value[key]
    return value

def verify_evidence(spec):
    path = checked(spec)
    if spec.get('assertions'):
        data = load(path)
        for key, expected in spec['assertions'].items():
            if pointer(data,key) != expected:
                raise ValueError('evidence assertion differs: '+str(path)+' '+key)
    return pin(path)

def verify_history(catalog):
    result = {}
    for row in catalog.get('history',[]):
        qid = row['question_id']
        if qid in result or not row.get('proofs') or not row.get('current_evidence'):
            raise ValueError('unique historical application and current evidence required: '+qid)
        if not all(any(s.get('assertions') for s in row[k]) for k in ('proofs','current_evidence')):
            raise ValueError('historical application and current evidence need explicit assertions: '+qid)
        proofs = [verify_evidence(s) for s in row['proofs']]
        current = [verify_evidence(s) for s in row['current_evidence']]
        result[qid] = dict(question_id=qid, answer=copy.deepcopy(row['answer']),
            state='previous_application_verified', rule_id=row.get('rule_id'),
            source_pair_sha256=row.get('pair_sha256',row['answer'].get('source_pair_sha256')),
            evidence=proofs, current_evidence=current, replayed_this_run=False,
            human_accepted=False)
        for key in ('validation_scope','remaining_technical_limits'):
            if key in row: result[qid][key]=copy.deepcopy(row[key])
    return result

def resolve(records, catalog, history):
    rules = {r['id']:r for r in catalog['rules']}
    if len(rules) != len(catalog['rules']):
        raise ValueError('duplicate rule id')
    bindings = {b['question_id']:b for b in catalog.get('bindings',[])}
    if len(bindings) != len(catalog.get('bindings',[])):
        raise ValueError('duplicate question binding')
    seen, applications, conflicts, rows = set(), {}, [], copy.deepcopy(history)
    for record in records:
        qid, answer = record['question_id'], record['explicit_answer']
        if qid in seen:
            raise ValueError('same question imported twice: '+qid)
        seen.add(qid)
        binding = bindings.get(qid)
        reason = None
        if record.get('conflicts_with_received_answer'):
            reason = 'decision_conflicts_with_previously_received_answer'
        elif qid in history and semantics(answer) != semantics(history[qid]['answer']):
            reason = 'decision_conflicts_with_previously_applied_rule'
        elif binding is None:
            if qid in history:
                if history[qid].get('source_pair_sha256') != record['pair_sha256']:
                    reason = 'source_pair_changed_requires_new_qualification'
                else:
                    continue
            else:
                reason = 'new_unregistered_interpretation'
        elif semantics(answer) != semantics(binding['approved_answer']):
            reason = 'decision_not_authorized_by_registered_rule'
        elif binding.get('pair_sha256') != record['pair_sha256']:
            reason = 'source_pair_changed_requires_new_qualification'
        if reason:
            conflict_id = 'HIL-'+stable({'question':qid,'answer':semantics(answer),
                                       'pair':record['pair_sha256'],'reason':reason})[:20]
            conflicts.append(dict(id=conflict_id,question_id=qid,reason=reason,
                answer=copy.deepcopy(answer),source_pair_sha256=record['pair_sha256'],
                source_evidence=copy.deepcopy(record.get('source_evidence',{})),
                source_views=copy.deepcopy(record.get('source_views',{})),
                affected_rule_ids=[binding['rule_id']] if binding else None,
                prior_answer=record.get('prior_received_answer',history.get(qid,{}).get('answer'))))
            rows[qid] = dict(question_id=qid,state='new_conflict',conflict_id=conflict_id)
            continue
        rid = binding['rule_id']
        if rid not in rules:
            # A missing implementation is an engineering failure, not another
            # expert question and not a successfully received-but-pending answer.
            raise ValueError('confirmed rule lacks executable registration: '+rid)
        if qid in history and not binding.get('reapply',False):
            continue
        applications.setdefault(rid,[]).append(qid)
        rows[qid] = dict(question_id=qid,answer=copy.deepcopy(answer),rule_id=rid,
            state='scheduled_native_application',intake_id=record['intake_id'],
            source_pair_sha256=record['pair_sha256'],human_accepted=False)
        for key in ('validation_scope','remaining_technical_limits'):
            if key in history.get(qid,{}):rows[qid][key]=copy.deepcopy(history[qid][key])
    # Known conflicts block only their registered owner. An unregistered scope
    # cannot be presumed independent, so it blocks all new applications without
    # inventing another question about already-confirmed decisions.
    blocked = set()
    for conflict in conflicts:
        blocked.update(conflict['affected_rule_ids'] if conflict['affected_rule_ids'] is not None else applications)
    for rid in blocked:
        for qid in applications.pop(rid,[]):
            rows[qid]['state']='blocked_by_new_conflict'
    return dict(records=list(rows.values()),applications=applications,new_conflicts=conflicts,
                pending_technical_applications=[],human_accepted=False)

def inventory(root):
    root = Path(root)
    return {p.relative_to(root).as_posix():digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')
            and 'startup-logs' not in p.relative_to(root).parts}

def _rule_script(spec):
    path = checked(spec)
    if path.suffix != '.py' or not path.is_relative_to(SKILLS):
        raise ValueError('rule executor must be an explicitly pinned shared Python owner')
    return path

def _command(spec, values):
    script = _rule_script(spec['script'])
    args = []
    for arg in spec['args']:
        if not isinstance(arg,str):
            raise ValueError('command arguments must be separate strings')
        for key,value in values.items():
            arg = arg.replace('{'+key+'}',str(value))
        if re.search(r'\{(?!stage_output)[^}]+\}',arg):
            raise ValueError('unknown command placeholder: '+arg)
        args.append(arg)
    return [sys.executable,'-X','utf8','-B',str(script),*args]

def prepare(config_path, output):
    config_path, output = Path(config_path).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError('fresh feedback output required: '+str(output))
    config = load(config_path)
    if config.get('schema') != SCHEMA:
        raise ValueError('versioned HIL feedback pipeline config required')
    catalog = load(checked(config['catalog']))
    if catalog.get('schema') != 'cad_confirmed_hil_rule_catalog_v1':
        raise ValueError('confirmed rule catalog required')
    checked(config['baseline_registry'])
    parent = Path(config['parent_viewer']).resolve()
    for spec in config.get('parent_bindings',[]):
        checked(spec)
    if not config.get('parent_bindings') or not (parent/'public/data/graph.json').is_file():
        raise ValueError('source-bound parent viewer required')
    parent_inventory = inventory(parent)
    history = verify_history(catalog)
    output.mkdir(parents=True)
    write(output/'status.json',dict(status='receiving',revision=1,human_accepted=False))
    write(output/'config.json',config)
    write(output/'catalog.json',catalog)
    write(output/'parent-inventory.json',parent_inventory)
    sys.path.insert(0,str(VIEWER))
    from receive_current_review_answers import produce,load as load_review
    from current_source_review_queue import questions
    intake_records, intake_paths, intake_specs = [], {}, {}
    for item in config['intakes']:
        ident = item['id']
        if not re.fullmatch('[a-z0-9][a-z0-9_-]*',ident) or ident in intake_paths:
            raise ValueError('unique path-safe intake id required')
        existing, reply = checked(item['definitions']), checked(item['reply'])
        folder = output/'intakes'/ident
        receipt = produce(existing,reply,Path(item['page_root']),item['question_ids'],folder,archive_conflicting_prior=True)
        intake_paths[ident] = folder/'receipt.json'
        intake_specs[ident] = item
        sections = {q['id']:s for s,q in questions(load_review(existing))}
        for record in receipt['records']:
            section = sections[record['question_id']]
            source_views = dict(page_root=str(Path(item['page_root']).resolve()),pair=section['image'],overviews=section.get('contexts',[]))
            intake_records.append(dict(record,intake_id=ident,source_views=source_views))
    resolution = resolve(intake_records,catalog,history)
    write(output/'resolution.json',resolution)
    write(output/'new-conflicts.json',dict(schema='cad_new_hil_conflicts_v1',
        records=resolution['new_conflicts'],previous_answers_preserved=True))
    safe_rows = []
    for conflict in resolution['new_conflicts']:
        pictures=[]
        views=conflict.get('source_views',{})
        for view in views.get('overviews',[])+([views['pair']] if views.get('pair') else []):
            source=(Path(views['page_root'])/view['path']).resolve()
            checked(dict(path=str(source),sha256=view['sha256']))
            target=output/'conflict-assets'/(view['sha256']+source.suffix)
            target.parent.mkdir(exist_ok=True)
            if not target.exists(): shutil.copy2(source,target)
            pictures.append('<figure><img style="max-width:100%" src="'+html.escape(target.relative_to(output).as_posix())+'"><figcaption>'+html.escape(view.get('title','原CAD与当前拓扑Pair'))+'</figcaption></figure>')
        safe_rows.append('<li><b>'+html.escape(conflict['question_id'])+'</b> '+html.escape(conflict['reason'])+'<pre>'+html.escape(json.dumps({'原答复':conflict['prior_answer'],'本次答复':conflict['answer']},ensure_ascii=False,indent=2))+'</pre>'+''.join(pictures)+'</li>')
    (output/'new-conflicts.html').write_text('<!doctype html><meta charset="utf-8"><title>新增HIL冲突</title>'
        '<h1>新增冲突</h1><ul>'+''.join(safe_rows)+'</ul><p>已确认且证据仍有效的答复不重复提问；缺少实现作为技术失败处理。</p>',encoding='utf8')
    if resolution['new_conflicts'] and not resolution['applications']:
        write(output/'application-ledger.json',dict(resolution,status='new_conflicts_require_HIL',
            applied_this_run=0,verified_existing_applications=sum(r['state']=='previous_application_verified' for r in resolution['records'])))
        write(output/'status.json',dict(status='new_conflicts_require_HIL',revision=2,
            conflict_count=len(resolution['new_conflicts']),applied=0,human_accepted=False))
        return output
    jobs = []
    common = {str(config_path):digest(config_path),str(checked(config['catalog'])):config['catalog']['sha256'],
              str(output/'resolution.json'):digest(output/'resolution.json')}
    for spec in config.get('parent_bindings',[]):
        common[str(checked(spec))] = spec['sha256']
    last_publisher, last_verifier, publish_specs = None, None, []
    for rule in catalog['rules']:
        rid = rule['id']
        if rid not in resolution['applications']:
            continue
        if not re.fullmatch('[a-z0-9][a-z0-9_-]*',rid):
            raise ValueError('path-safe rule id required')
        selected = resolution['applications'][rid]
        required = rule['question_ids']
        if set(selected) != set(required):
            raise ValueError('complete confirmed rule cohort required: '+rid)
        receipts = {r['intake_id'] for r in resolution['records'] if r.get('rule_id')==rid and r['question_id'] in selected}
        if len(receipts)!=1:
            raise ValueError('one source-bound receipt must authorize a rule cohort')
        intake_spec = intake_specs[next(iter(receipts))]
        cohort_folder = output/'rule-intakes'/rid
        produce(checked(intake_spec['definitions']),checked(intake_spec['reply']),
                Path(intake_spec['page_root']),selected,cohort_folder)
        receipt_path = cohort_folder/'receipt.json'
        template = load(checked(rule['manifest_template']))
        keys = rule.get('receipt_binding_path',['inputs','answer_receipt'])
        target = template
        for key in keys[:-1]:
            target = target[key]
        if keys[-1] not in target:
            raise ValueError('receipt slot missing from native owner manifest')
        target[keys[-1]] = pin(receipt_path)
        manifest_path = output/'native-manifests'/(rid+'.json')
        write(manifest_path,template)
        native, verify, publish, pubverify = [rid+'-'+suffix for suffix in ('native','verify','publish','publish-verify')]
        values = dict(manifest=manifest_path,
            native='{stage_output:'+native+'}/native',
            proof='{stage_output:'+native+'}/native/'+rule['proof_filename'],
            parent_viewer='{stage_output:'+last_publisher+'}/viewer' if last_publisher else parent,
            viewer='{stage_output:'+publish+'}/viewer',port=config.get('port',10638))
        fixed = dict(common,**{str(manifest_path):digest(manifest_path),str(receipt_path):digest(receipt_path)})
        for spec in rule.get('inputs',[]):
            fixed[str(checked(spec))] = spec['sha256']
        for ident,kind,deps in ((native,'native',[]),(verify,'verify',[native]),
                                (publish,'publish',[verify]+([last_verifier] if last_verifier else [])),
                                (pubverify,'publish_verify',[publish])):
            spec = rule[kind]
            command = _command(spec,values)
            if kind == 'verify':
                command = [sys.executable,'-X','utf8','-B',str(Path(__file__)),
                    '_verify-owner','--proof',values['proof'],'--receipt-output','{stage_output}/verification.json','--',*command]
            jobs.append(dict(id=ident,command=command,cwd=str(SKILLS.parent),
                cores=spec.get('cores',1),inputs=fixed,implementation={str(Path(__file__)):digest(__file__),
                    str(checked(spec['script'])):spec['script']['sha256']},
                outputs=['{stage_output}'],depends_on=deps,cacheable=False))
        publish_specs.append(dict(rule_id=rid,question_ids=selected,publish_stage=publish,
            verification_stage=pubverify,publication_receipt=rule['publication_receipt'],
            native_stage=native,native_verification_stage=verify,proof_filename=rule['proof_filename']))
        last_publisher = publish
        last_verifier = pubverify
    regression = dict(id='historical-regression',command=[sys.executable,'-X','utf8','-B',str(Path(__file__)),
        '_regression','--workflow',str(output),'--output','{stage_output}'],cwd=str(SKILLS.parent),
        cores=config.get('test_workers',4),inputs=common,outputs=['{stage_output}'],depends_on=[],cacheable=False)
    jobs.append(regression)
    finalized = dict(publish_specs=publish_specs,last_publisher=last_publisher,
                     original_config=pin(config_path),intakes={k:pin(v) for k,v in intake_paths.items()})
    write(output/'execution.json',finalized)
    jobs.append(dict(id='finalize',command=[sys.executable,'-X','utf8','-B',str(Path(__file__)),
        '_finalize','--workflow',str(output),'--output','{stage_output}'],cwd=str(SKILLS.parent),
        cores=1,inputs={**common,str(output/'execution.json'):digest(output/'execution.json')},
        outputs=['{stage_output}'],depends_on=['historical-regression']+[x['verification_stage'] for x in publish_specs],cacheable=False))
    write(output/'batch-manifest.json',dict(schema_version=1,jobs=jobs,scope='HIL_intake_to_native_application_regression_and_publication'))
    write(output/'status.json',dict(status='prepared',revision=2,intakes=len(intake_paths),
        confirmed_questions=len(resolution['records']),rule_batches=len(publish_specs),human_accepted=False))
    return output

def regress(workflow, output):
    from feature_impact import load_registry, run_selected
    from verify_dependencies import verify
    config = load(workflow/'config.json')
    previous = load(checked(config['baseline_registry']))
    registry, features = load_registry()
    for row in previous['features']:
        if features.get(row['id']) != row:
            raise ValueError('historical feature changed or removed: '+row['id'])
    tests = sorted({f for row in features.values() for f in row['tests']})
    locks = {str(p):digest(p) for skill in SKILLS.iterdir() if skill.is_dir() for p in (skill/'scripts').glob('*.py')}
    executions = run_selected(dict(tests=tests,fallback_full_suites=True),root=SKILLS,workers=config.get('test_workers',4))
    changed = [p for p,h in locks.items() if digest(p)!=h]
    dependencies = verify()
    passed = bool(executions) and all(x['exit_code']==0 for x in executions) and not changed
    write(output/'regression.json',dict(status='passed' if passed else 'failed',
        historical_features_preserved=len(previous['features']),features=len(features),
        registered_test_files=len(tests),executions=executions,implementation_changed=changed,
        dependencies=dependencies,human_accepted=False))
    if not passed:
        raise ValueError('historical or new regression failed')

def finalize(workflow, output):
    config, execution, resolution = [load(workflow/f) for f in ('config.json','execution.json','resolution.json')]
    catalog = load(workflow/'catalog.json')
    verify_history(catalog)
    if inventory(config['parent_viewer']) != load(workflow/'parent-inventory.json'):
        raise ValueError('parent payload or annotations changed during feedback application')
    stages = workflow/'batch/stages'
    regression = stages/'historical-regression/artifacts/regression.json'
    if load(regression)['status']!='passed':
        raise ValueError('regression gate has not passed')
    rows = {r['question_id']:copy.deepcopy(r) for r in resolution['records']}
    for spec in execution['publish_specs']:
        published = stages/spec['publish_stage']/'artifacts'
        locator = spec['publication_receipt']
        if isinstance(locator,dict):
            manifest_path = (published/locator['manifest_path']).resolve()
            if not manifest_path.is_relative_to(published.resolve()):
                raise ValueError('publication manifest outside stage')
            relative = pointer(load(manifest_path),locator['json_pointer'])
            receipt = (manifest_path.parent/locator.get('relative_root','.')/relative).resolve()
        else:
            receipt = (published/locator).resolve()
        if not receipt.is_relative_to(published.resolve()):
            raise ValueError('publication receipt outside stage')
        proof = stages/spec['native_stage']/'artifacts/native'/spec['proof_filename']
        proof_hash = digest(proof)
        if load(receipt).get('proof_sha256') != proof_hash:
            raise ValueError('publication does not bind this native proof')
        native_verification = stages/spec['native_verification_stage']/'artifacts/verification.json'
        if load(native_verification).get('proof_sha256') != proof_hash or load(native_verification).get('status') != 'passed':
            raise ValueError('independent native verification does not bind this proof')
        verify_receipt = stages/spec['verification_stage']/'artifacts/verification.json'
        if not verify_receipt.is_file() or load(verify_receipt).get('status') != 'passed':
            raise ValueError('independent publication proof missing')
        verification = load(verify_receipt)
        if verification.get('proof_sha256') != proof_hash or verification.get('publication',{}).get('sha256') != digest(receipt):
            raise ValueError('publication verification does not bind this receipt and native proof')
        for qid in spec['question_ids']:
            rows[qid].update(state='native_applied_regressed_and_published',replayed_this_run=True,
                native_proof=pin(proof),publication=pin(receipt),verification=pin(verify_receipt))
    if any(r['state']=='scheduled_native_application' for r in rows.values()):
        raise ValueError('confirmed answer left pending technical application')
    viewer = (stages/execution['last_publisher']/'artifacts/viewer' if execution['last_publisher'] else Path(config['parent_viewer']))
    if inventory(Path(config['parent_viewer'])/'annotations') != inventory(viewer/'annotations'):
        raise ValueError('annotation history not preserved')
    report = dict(schema='cad_hil_closed_loop_completion_v1',status='published_with_new_conflicts' if resolution['new_conflicts'] else 'published',
        records=list(rows.values()),new_conflicts=resolution['new_conflicts'],
        pending_technical_applications=[],published_viewer=str(viewer),
        applied_this_run=sum(r.get('replayed_this_run',False) for r in rows.values()),
        verified_existing_applications=sum(r['state']=='previous_application_verified' for r in rows.values()),
        regression=pin(regression),annotations_preserved=True,source_parent_unchanged=True,
        historical_validation_limits=copy.deepcopy(catalog.get('limitations',[])),
        human_accepted=False,whole_goal_complete=False)
    write(output/'application-ledger.json',report)

def run(config_path, output, cores=None):
    from pipeline_batch_runtime import run_manifest, query_status
    existed = Path(output).exists()
    try:
        workflow = prepare(config_path,output)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        if not existed and Path(output).is_dir():
            write(Path(output)/'status.json',dict(status='technical_failure',revision=2,error=str(exc),
                note='Technical failure; do not resend an already-answered expert question.',human_accepted=False))
        raise
    if load(workflow/'status.json')['status']=='new_conflicts_require_HIL':
        return load(workflow/'status.json')
    write(workflow/'status.json',dict(status='running',revision=3,batch=str(workflow/'batch'),human_accepted=False))
    try:
        run_manifest(workflow/'batch-manifest.json',workflow/'batch',cores=cores)
    except Exception as exc:
        write(workflow/'status.json',dict(status='technical_failure',revision=4,error=str(exc),
            note='Technical failures are not new expert questions.',human_accepted=False))
        raise
    status = query_status(workflow/'batch')
    if status['status']!='succeeded':
        write(workflow/'status.json',dict(status='technical_failure',revision=4,batch=status,
            note='Technical failures are not new expert questions.',human_accepted=False))
        raise ValueError('feedback application batch failed; see bounded batch status')
    ledger = workflow/'batch/stages/finalize/artifacts/application-ledger.json'
    result = load(ledger)
    final = {k:result[k] for k in ('status','applied_this_run','verified_existing_applications',
             'new_conflicts','pending_technical_applications','published_viewer','human_accepted')}
    final.update(revision=4,application_ledger=pin(ledger),batch=str(workflow/'batch'))
    write(workflow/'status.json',final)
    return final

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action',required=True)
    for name in ('run','start'):
        child=sub.add_parser(name);child.add_argument('--config',type=Path,required=True);child.add_argument('--output',type=Path,required=True);child.add_argument('--cores',type=int,default=16)
    child=sub.add_parser('status');child.add_argument('--run',type=Path,required=True)
    for name in ('_regression','_finalize'):
        child=sub.add_parser(name);child.add_argument('--workflow',type=Path,required=True);child.add_argument('--output',type=Path,required=True)
    child=sub.add_parser('_verify-owner');child.add_argument('--proof',type=Path,required=True)
    child.add_argument('--receipt-output',type=Path,required=True);child.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args(argv)
    try:
        if args.action=='start':
            if args.output.exists(): raise FileExistsError(args.output)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            log_path=args.output.with_name(args.output.name+'-launcher.log')
            command=[sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'run','--config',str(args.config.resolve()),'--output',str(args.output.resolve()),'--cores',str(args.cores)]
            with log_path.open('x',encoding='utf8') as stream:
                proc=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,
                    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            result=dict(status='launched',pid=proc.pid,workflow=str(args.output.resolve()),log=str(log_path.resolve()))
        elif args.action=='run': result=run(args.config,args.output,args.cores)
        elif args.action=='status':
            result=load(args.run/'status.json')
            if result['status']=='running':
                from pipeline_batch_runtime import query_status
                result['batch_status']=query_status(args.run/'batch',limit=12)
        elif args.action=='_verify-owner':
            command=args.command[1:] if args.command[:1]==['--'] else args.command
            before=digest(args.proof)
            if not command: raise ValueError('native verification command required')
            completed=subprocess.run(command,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
            if completed.returncode or digest(args.proof)!=before: raise ValueError('native owner verification failed or changed its proof')
            result=dict(status='passed',proof_sha256=before,command=command)
            write(args.receipt_output,result)
        elif args.action=='_regression': regress(args.workflow,args.output);result={'status':'passed'}
        else: finalize(args.workflow,args.output);result={'status':'passed'}
        print(json.dumps(result,ensure_ascii=False))
        return 2 if result.get('status')=='new_conflicts_require_HIL' else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'status':'failed','error':str(exc)},ensure_ascii=False))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
