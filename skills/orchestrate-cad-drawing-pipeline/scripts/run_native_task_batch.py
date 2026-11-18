"""Run independent native owners under one core budget; preserve every outcome.

The manifest is authored by the operator, never inferred from CAD text. Commands
are argument arrays, not shell strings. Dependency failures block descendants;
other drawings continue. This does not cache verification or accept topology.
"""
import argparse,concurrent.futures,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def validate(manifest,budget):
    if type(budget)is not int or not 1<=budget<=32:raise ValueError('core budget must be1..32')
    if manifest.get('schema_version')!=1 or not isinstance(manifest.get('jobs'),list)or not manifest['jobs']:raise ValueError('nonempty task manifest required')
    jobs={};outputs={}
    for row in manifest['jobs']:
        ident=row.get('id','');cores=row.get('cores',1);command=row.get('command');cwd=Path(row.get('cwd','')).resolve()
        if not re.fullmatch(r'[A-Za-z0-9_-]+',ident)or ident in jobs:raise ValueError('unique safe job ID required')
        if type(cores)is not int or not 1<=cores<=budget:raise ValueError('job exceeds shared core budget')
        if not isinstance(command,list)or not command or not all(isinstance(x,str)and x and '\x00'not in x for x in command):raise ValueError('explicit command argument array required')
        if not cwd.is_dir():raise ValueError('job cwd must exist')
        codes=row.get('success_exit_codes',[0])
        if not isinstance(codes,list)or not codes or any(type(x)is not int for x in codes):raise ValueError('explicit success exit codes required')
        for path,digest in row.get('inputs',{}).items():
            if not Path(path).is_absolute()or not Path(path).is_file()or sha(path)!=digest:raise ValueError('pinned job input changed: '+path)
        for path in row.get('outputs',[]):
            output=Path(path)
            if not output.is_absolute():raise ValueError('absolute output path required')
            resolved=output.resolve()
            for previous,owner in outputs.items():
                if resolved==previous or resolved in previous.parents or previous in resolved.parents:raise ValueError('overlapping task output ownership')
            outputs[resolved]=ident
        jobs[ident]=dict(row,cwd=str(cwd),cores=cores,success_exit_codes=codes)
    active=set();done=set()
    def visit(ident):
        if ident in active:raise ValueError('task dependency cycle')
        if ident in done:return
        active.add(ident)
        for dep in jobs[ident].get('depends_on',[]):
            if dep not in jobs:raise ValueError('unknown task dependency')
            visit(dep)
        active.remove(ident);done.add(ident)
    for ident in jobs:visit(ident)
    return jobs

def execute(row,output):
    started=time.monotonic();log=output/(row['id']+'.log')
    env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',CAD_NATIVE_WORKERS=str(row['cores']),CAD_TEST_WORKERS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    code=None;error=None
    try:
        if any(sha(path)!=digest for path,digest in row.get('inputs',{}).items()):raise ValueError('job input changed before execution')
        with log.open('x',encoding='utf8',newline='\n')as stream:
            result=subprocess.run(row['command'],cwd=row['cwd'],env=env,stdout=stream,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        code=result.returncode
        if any(sha(path)!=digest for path,digest in row.get('inputs',{}).items()):raise ValueError('job input changed during execution')
        if code in row['success_exit_codes']and any(not Path(path).exists()for path in row.get('outputs',[])):raise ValueError('successful job omitted declared output')
    except Exception as exc:error=dict(type=type(exc).__name__,message=str(exc))
    return dict(id=row['id'],status='passed'if error is None and code in row['success_exit_codes']else'failed',exit_code=code,error=error,
        cores=row['cores'],elapsed_seconds=time.monotonic()-started,log=str(log),log_sha256=sha(log)if log.exists()else None)

def run(manifest,output,budget=22):
    jobs=validate(manifest,budget);output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    waiting=set(jobs);finished={};live={};used=0;peak=0;started=time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(budget,len(jobs)))as pool:
        while waiting or live:
            for ident in jobs:
                if ident not in waiting:continue
                row=jobs[ident];deps=row.get('depends_on',[])
                if any(dep in finished and finished[dep]['status']!='passed'for dep in deps):
                    finished[ident]=dict(id=ident,status='blocked_by_dependency',dependencies=deps);waiting.remove(ident);continue
                if all(dep in finished for dep in deps)and used+row['cores']<=budget:
                    waiting.remove(ident);live[pool.submit(execute,row,output)]=ident;used+=row['cores'];peak=max(peak,used)
            if not live:
                if waiting:raise RuntimeError('no task can be scheduled')
                break
            completed,_=concurrent.futures.wait(live,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in completed:
                ident=live.pop(future);used-=jobs[ident]['cores'];finished[ident]=future.result()
                print(json.dumps(finished[ident],ensure_ascii=False),flush=True)
    report=dict(schema_version=1,status='all_tasks_passed'if all(row['status']=='passed'for row in finished.values())else'task_failures_or_blocked',
        core_budget=budget,peak_allocated_core_slots=peak,elapsed_seconds=time.monotonic()-started,jobs=[finished[ident]for ident in jobs],
        persisted_verification_reuse=False,human_accepted=False,whole_goal_complete=False)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--monitor',action='store_true');parser.add_argument('--cores',type=int,default=min(22,max(1,(os.cpu_count()or 2)-2)));args=parser.parse_args()
    before=sha(args.manifest);implementation=sha(__file__);manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'));monitor=None
    validate(manifest,args.cores)
    if args.output.exists():raise FileExistsError(args.output)
    if args.monitor:
        stop=args.output.with_suffix('.stop');resources=args.output.with_suffix('.resources.json')
        if stop.exists()or resources.exists():raise FileExistsError(resources)
        monitor=subprocess.Popen([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('native_resource_monitor_v1.py')),'--pid',str(os.getpid()),'--output',str(resources),'--stop',str(stop)],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:result=run(manifest,args.output,args.cores)
    finally:
        if monitor is not None:stop.write_text('stop\n',encoding='utf8');monitor.wait(timeout=10)
    if sha(args.manifest)!=before:raise ValueError('task manifest changed during batch')
    if sha(__file__)!=implementation:raise ValueError('batch runner changed during execution')
    result.update(manifest=dict(path=str(args.manifest.resolve()),sha256=before),implementation_sha256=implementation)
    (args.output/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return 0 if result['status']=='all_tasks_passed'else 1
if __name__=='__main__':raise SystemExit(main())
