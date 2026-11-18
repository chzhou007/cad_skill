"""Run an original native job with an explicit isolated projection backend."""
import argparse,hashlib,json,os,runpy,sys,time,traceback,subprocess
from pathlib import Path
from native_projection_runtime_v1 import accelerated_native_runtime

def main():
    p=argparse.ArgumentParser();p.add_argument('--skills',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--monitor',action='store_true');p.add_argument('--workers',type=int,default=min(22,max(1,(os.cpu_count()or 2)-2)));p.add_argument('job',type=Path);p.add_argument('arguments',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.report.exists():raise FileExistsError(a.report)
    if not 1<=a.workers<=32:raise ValueError('workers1..32 required')
    files=[Path(__file__),Path(__file__).with_name('native_projection_runtime_v1.py'),Path(__file__).with_name('native_projection_service_v1.py'),Path(__file__).with_name('native_projection_value_runtime_v1.py')]
    implementation={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
    source_sha=hashlib.sha256(a.job.read_bytes()).hexdigest();started=time.monotonic();code=0;error=None;runtime=None;saved=list(sys.argv);monitor=None
    if a.monitor:
        stop=a.report.with_suffix('.stop');resources=a.report.with_suffix('.resources.json')
        if stop.exists()or resources.exists():raise FileExistsError(resources)
        monitor=subprocess.Popen([sys.executable,'-X','utf8','-B',str(Path(__file__).with_name('native_resource_monitor_v1.py')),'--pid',str(os.getpid()),'--output',str(resources),'--stop',str(stop)],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        with accelerated_native_runtime(a.skills,a.workers)as runtime:
            sys.argv=[str(a.job),*a.arguments]
            try:runpy.run_path(str(a.job),run_name='__main__')
            except SystemExit as exc:code=exc.code or 0
    except BaseException as exc:traceback.print_exc();code=1;error=dict(type=type(exc).__name__,message=str(exc))
    finally:
        sys.argv=saved
        if monitor is not None:stop.write_text('stop\n',encoding='utf8');monitor.wait(timeout=10)
    if hashlib.sha256(a.job.read_bytes()).hexdigest()!=source_sha:raise RuntimeError('original job changed')
    report=dict(status='original_native_job_finished'if code in (0,2)else'failed',exit_code=code,error=error,elapsed_seconds=time.monotonic()-started,
        original_job=str(a.job.resolve()),original_job_sha256=source_sha,original_job_source_modified=False,execution_backend='isolated_parallel_projection_same_job_input_bound_cache_v1',
        statistics=runtime.stats if runtime else{},implementation_sha256=implementation,persisted_pass_flags_used=False,human_accepted=False,whole_goal_complete=False)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h for p,h in implementation.items()):raise RuntimeError('accelerator implementation changed during original job')
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');print(json.dumps(report,ensure_ascii=False),flush=True)
    return code
if __name__=='__main__':raise SystemExit(main())
