"""Read-only CAD routing plans and artifact-contract validation, not an extraction engine."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from source_comparison_gate import check as check_comparison

FAMILIES={
    'schedule':{'parameters'},
    'plant_schematic':{'parameters','topology','visualization'},
    'outdoor_plan':{'parameters','topology','architecture','visualization'},
    'ceiling_plan':{'parameters','topology','architecture','visualization'},
    'isometric':{'parameters','topology','visualization'},
    'architectural_support':{'architecture'},
}
OWNERS={'source':'orchestrate-cad-drawing-pipeline','parameters':'build-cad-pipe-topology',
        'topology':'build-cad-pipe-topology','architecture':'extract-cad-building-context',
        'source_comparison':'build-cad-pipe-topology','visualization':'visualize-cad-pipe-topology'}
STATES={'completed','not_applicable','pending','failed'}
ROLES={'source':{'inventory','parse_issues'},'parameters':{'parameter_library','parameter_bindings','audit'},
       'topology':{'graph','nodes','edges','ports','components','audit','quality'},
       'architecture':{'building_context','building_svg','audit','quality'},
       'source_comparison':{'comparison','audit'},
       'visualization':{'viewer','pair','quality','audit'}}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

def applicable(t):
    active=set(FAMILIES.get(t['family'],set()))|{'source'};tags=set(t['tags'])
    if 'architecture'in tags:active.add('architecture')
    if tags & {'parameters','equipment'}:active.add('parameters')
    if 'pipe'in tags:active.update(['parameters','topology','visualization'])
    if 'topology'in active:active.add('source_comparison')
    return active if t['family']in FAMILIES else set(OWNERS)

def plan(config,output):
    config=Path(config).resolve();output=Path(output).resolve();cfg=read(config)
    if output.exists():raise ValueError('Choose a new output directory')
    if not cfg.get('project_id') or not cfg.get('tasks'):raise ValueError('Project and tasks required')
    tasks=[];ids=set()
    for t in cfg['tasks']:
        tid=t['task_id']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',tid) or tid in ids:raise ValueError('Invalid/duplicate task ID')
        ids.add(tid)
        if not t.get('evidence') or not isinstance(t.get('tags'),list):raise ValueError('Family evidence and tag list required')
        source=(config.parent/t['source']).resolve()
        if not source.is_file():raise ValueError('Missing source: '+str(source))
        family=t['family'];known=family in FAMILIES;active=applicable(t)
        stages={}
        for name,owner in OWNERS.items():
            deps=[] if name=='source' else ['source']
            if name=='topology':deps.append('parameters')
            if name=='source_comparison':deps.extend(x for x in ('parameters','topology','architecture')if x in active)
            if name=='visualization':deps.extend(x for x in ('parameters','topology','architecture','source_comparison')if x in active)
            required=name in active
            stages[name]={'owner':owner,'required':required,'status':'pending' if required else 'not_applicable',
                          'reason':'Await stage execution' if required else 'Excluded by evidence-backed family/tags',
                          'evidence':t['evidence'],'depends_on':deps,'artifacts':[]}
        tasks.append({'schema_version':1,'pipeline_version':'1.1.1','task_id':tid,'source':str(source),
                      'source_sha256':sha(source),'family':family,'tags':t['tags'],'family_evidence':t['evidence'],
                      'routing_status':'completed' if known else 'pending','stages':stages,
                      'review':{'scope':'this_task_only','confirmation':None}})
    profiles=[]
    for value in cfg.get('profile_files',[]):
        p=(config.parent/value).resolve();profiles.append({'path':str(p),'sha256':sha(p)})
    output.mkdir(parents=True)
    write(output/'configuration.json',cfg)
    for t in tasks:
        folder=output/t['task_id'];folder.mkdir();write(folder/'task-plan.json',t)
    code_locks=[];skill_root=Path(__file__).resolve().parents[2]
    for owner in sorted(set(OWNERS.values())):
        base=skill_root/owner
        for p in sorted(base.rglob('*')):
            if p.is_file()and '__pycache__'not in p.parts and (p.name=='SKILL.md'or ('scripts'in p.relative_to(base).parts or 'assets'in p.relative_to(base).parts)and p.suffix in ('.py','.js','.mjs','.html','.css','.json')):
                code_locks.append({'path':str(p),'sha256':sha(p)})
    manifest={'schema_version':1,'pipeline_version':'1.1.1','project_id':cfg['project_id'],
              'config_sha256':sha(config),'frozen_config_sha256':sha(output/'configuration.json'),'profile_locks':profiles,'tasks':[t['task_id']for t in tasks],
              'source_locks':{t['task_id']:{'path':t['source'],'sha256':t['source_sha256']}for t in tasks},'implementation_locks':code_locks,
              'execution':'planned_only','human_review':'unconfirmed'}
    write(output/'batch-plan.json',manifest);return manifest

def validate(run):
    run=Path(run).resolve();batch=read(run/'batch-plan.json');results=[]
    if sha(run/'configuration.json')!=batch['frozen_config_sha256']:raise ValueError('Frozen configuration changed')
    cfg=read(run/'configuration.json');expected={t['task_id']:t for t in cfg['tasks']}
    if len(batch['tasks'])!=len(expected)or set(batch['tasks'])!=set(expected):raise ValueError('Batch tasks differ from frozen configuration')
    for lock in batch.get('profile_locks',[])+batch.get('implementation_locks',[]):
        if not Path(lock['path']).is_file()or sha(lock['path'])!=lock['sha256']:raise ValueError('Profile/implementation lock mismatch: '+lock['path'])
    for tid in batch['tasks']:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',tid):raise ValueError('Unsafe task ID')
        folder=run/tid;t=read(folder/'task-plan.json');errors=[];pending=[];claimed={};coordinates=[]
        original=expected[tid];active=applicable(original)
        locked=batch['source_locks'][tid]
        if t['source']!=locked['path']or t['source_sha256']!=locked['sha256']:errors.append('Receipt source differs from frozen input')
        if t.get('family')!=original['family']or t.get('tags')!=original['tags']:errors.append('Routing changed without new plan')
        if t['task_id']!=tid:errors.append('Task identity mismatch')
        if not Path(t['source']).is_file()or sha(t['source'])!=t['source_sha256']:errors.append('Source changed')
        if original['family']not in FAMILIES or t.get('routing_status')!='completed':pending.append('Unresolved family routing')
        if set(t['stages'])!=set(OWNERS):errors.append('Missing or unexpected stage')
        for name,s in t['stages'].items():
            status=s.get('status')
            if name not in OWNERS or s.get('owner')!=OWNERS[name]:errors.append(name+': wrong owner')
            deps=[]if name=='source'else ['source']
            if name=='topology':deps.append('parameters')
            if name=='source_comparison':deps.extend(x for x in ('parameters','topology','architecture')if x in active)
            if name=='visualization':deps.extend(x for x in ('parameters','topology','architecture','source_comparison')if x in active)
            if s.get('depends_on')!=deps:errors.append(name+': altered dependencies')
            if s.get('required')!=(name in active):errors.append(name+': altered applicability')
            if status not in STATES:errors.append(name+': invalid state')
            if not s.get('reason')or not s.get('evidence'):errors.append(name+': missing reason/evidence')
            if status=='failed':errors.append(name+': stage failed')
            if s.get('required')and status!='completed':pending.append(name+': incomplete')
            if status!='completed':continue
            if s.get('task_id')!=tid or s.get('source_sha256')!=t['source_sha256']:errors.append(name+': receipt identity mismatch')
            if not s.get('artifacts'):errors.append(name+': completed without artifacts')
            for dep in s.get('depends_on',[]):
                if dep not in t['stages']or t['stages'][dep]['status']!='completed':errors.append(name+': unmet dependency '+dep)
            if name=='source_comparison'and not any(a.get('role')=='comparison'for a in s.get('artifacts',[])):errors.append('Missing comparison gate report')
            for a in s.get('artifacts',[]):
                p=(folder/a['path']).resolve()
                if not p.is_relative_to(folder.resolve()):errors.append(name+': artifact outside task');continue
                if p in claimed:errors.append(name+': duplicate artifact writer '+claimed[p])
                claimed[p]=name
                if a.get('role')not in ROLES.get(name,set()):errors.append(name+': invalid artifact role')
                if not p.is_file()or sha(p)!=a.get('sha256'):errors.append(name+': artifact hash mismatch')
                if name=='source_comparison'and a.get('role')=='comparison'and p.is_file():
                    graphs=[a for a in t['stages']['topology']['artifacts']if a.get('role')=='graph']
                    check=check_comparison(read(p),graphs[0]['sha256']if len(graphs)==1 else None,folder)
                    errors.extend(check['errors']);pending.extend(check['pending'])
                if a.get('role')in ('graph','building_context'):
                    c=a.get('coordinate_contract',{})
                    if c.get('frame')!='WCS'or not c.get('units')or c.get('source_sha256')!=t['source_sha256']:errors.append(name+': invalid WCS contract')
                    coordinates.append(c)
        if coordinates and any(c!=coordinates[0]for c in coordinates):errors.append('Coordinate contracts differ')
        results.append({'task_id':tid,'status':'failed'if errors else 'pending'if pending else 'completed','errors':errors,'pending':pending})
    status='failed'if any(t['errors']for t in results)else 'pending'if any(t['pending']for t in results)else 'completed'
    return {'status':status,'tasks':results,'scope':'Artifact contracts only; no physical or human attestation'}

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('plan');q.add_argument('--config',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('validate');q.add_argument('--run',type=Path,required=True);args=p.parse_args()
    try:
        result=plan(args.config,args.output)if args.command=='plan'else validate(args.run)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return {'failed':1,'pending':2}.get(result.get('status'),0)
    except (ValueError,KeyError,TypeError,OSError)as exc:print(json.dumps({'status':'failed','error':str(exc)},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
