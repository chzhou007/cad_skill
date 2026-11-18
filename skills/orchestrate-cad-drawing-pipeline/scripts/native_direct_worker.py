"""Run named CAD native operations with the explicit no-cache backend.

Jobs are data with fixed operations, not executable commands. Every operation
uses the original owner/CLI and checks its actual result; job and runtime
identities are included in the worker report.
"""
import argparse,contextlib,hashlib,io,json,sys,time,traceback
from pathlib import Path
from native_direct_verification_runtime import install


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text('utf8'))
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')


def invoke(module,arguments):
    previous=sys.argv;sys.argv=[module.__file__]
    for key,value in arguments.items():sys.argv+=['--'+key.replace('_','-'),str(value)]
    try:module.main()
    finally:sys.argv=previous


def execute(job):
    operation=job['operation']
    if operation=='build_anchored_mains':
        import attach_anchored_floor_main_attributes as owner
        invoke(owner,job['arguments']);graph=Path(job['arguments']['output'])/'graph_with_edges.json'
        if digest(graph)!=job['expected_output_graph_sha256']:raise ValueError('native anchored main output differs from fixed source contract')
        return dict(source_replay='passed',output_graph_sha256=digest(graph))
    if operation=='verify_lower_parent':
        from attach_lower_floor_plan_attributes import verify_output
        result=verify_output(Path(job['run']))
        if result['output_graph_sha256']!=job['expected_output_graph_sha256']:raise ValueError('native lower parent output differs')
        return dict(source_replay='passed',output_graph_sha256=result['output_graph_sha256'],verified_audit_payload_sha256=hashlib.sha256(encode(result)).hexdigest())
    if operation=='build_adoption':
        import adopt_wave_rebased_plan_scopes as owner
        invoke(owner,job['arguments']);graph=Path(job['arguments']['output'])/'graph_with_edges.json'
        if digest(graph)!=job['expected_output_graph_sha256']:raise ValueError('native adoption output differs from fixed source contract')
        return dict(source_replay='passed',output_graph_sha256=digest(graph))
    if operation=='validate_adoption':
        import pipeline
        previous=sys.argv;sys.argv=[pipeline.__file__,'validate-wave-plan-scope-adoption','--adoption-run',job['run']];output=io.StringIO()
        try:
            with contextlib.redirect_stdout(output):code=pipeline.main()
        finally:sys.argv=previous
        result=json.loads(output.getvalue())
        if code!=2 or result.get('source_replay')!='passed' or result.get('hil_ready') is not False:raise ValueError('actual native adoption CLI failed')
        return dict(cli_exit_code=code,result=result,pipeline_sha256=digest(pipeline.__file__))
    if operation=='source_gate':
        from source_comparison_gate import check
        graph=Path(job['graph']);run=graph.parent
        if digest(graph)!=job['expected_output_graph_sha256']:raise ValueError('native gate graph changed')
        result=check(load(job['previous_report']),digest(graph),run,graph)
        stage=job.get('expected_stage','wave_plan_scope_adoption_stage')
        if stage not in ('wave_plan_scope_adoption_stage','anchored_floor_main_attribute_stage'):raise ValueError('unsupported native source gate stage')
        if result['errors'] or result.get(stage,{}).get('source_replay')!='passed':raise ValueError('native current scope source gate failed')
        target=run/'source-comparison-gate.json'
        if target.exists():raise FileExistsError(target)
        target.write_bytes(encode(result));return dict(source_replay='passed',report_sha256=digest(target),report_path=str(target),pending=result['pending'])
    if operation=='build_viewer':
        import build_visualization
        invoke(build_visualization,job['arguments']);folder=Path(job['arguments']['output']);quality=load(folder/'quality-gate.json')
        if quality.get('machine_status')!='PASS' or quality.get('blocking_defects'):raise ValueError('native viewer machine check failed')
        return dict(native_viewer='passed',viewer=str(folder),dataset_sha256=digest(folder/'public/data/graph.json'))
    raise ValueError('unsupported native worker operation')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);a=parser.parse_args()
    if a.report.exists():raise FileExistsError(a.report)
    job=load(a.job);runtime=install(job['expected_cache_library_sha256']);skills=Path(__file__).resolve().parents[2]
    sys.path[:0]=[str(skills/'build-cad-pipe-topology/scripts'),str(skills/'visualize-cad-pipe-topology/scripts')]
    started=time.monotonic();cpu=time.process_time();result=None;failure=None
    try:result=execute(job)
    except BaseException as exc:failure=exc;traceback.print_exc()
    report=dict(status='passed' if failure is None else 'failed',operation=job['operation'],job_path=str(a.job.resolve()),job_sha256=digest(a.job),
        runtime=runtime(),worker_sha256=digest(__file__),elapsed_seconds=time.monotonic()-started,process_cpu_seconds=time.process_time()-cpu,
        result=result,error=None if failure is None else type(failure).__name__+': '+str(failure),human_accepted=False,whole_goal_complete=False)
    a.report.write_bytes(encode(report))
    if failure is not None:raise RuntimeError('native direct worker failed; retain its job/report and logs') from failure
    print(json.dumps(dict(status='passed',operation=job['operation'],elapsed_seconds=report['elapsed_seconds'],runtime=report['runtime']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
