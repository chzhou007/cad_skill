"""Audit original skill assets and executable test evidence, never native acceptance."""
import argparse,hashlib,json
from pathlib import Path,PurePosixPath
import zipfile
from feature_impact import load_registry

OWNERS={'build-cad-pipe-topology','orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology','extract-cad-building-context'}
def sha(data):return hashlib.sha256(data).hexdigest()
def load(path):return json.loads(Path(path).read_text('utf-8-sig'))


def executed_tests(executions):
    result=set()
    if not executions:raise ValueError('No test executions')
    for row in executions:
        if row['exit_code']!=0:raise ValueError('Failed unit execution')
        command=row['command'];owner=row['skill']
        if owner not in OWNERS:raise ValueError('Unknown execution owner')
        if '-m' in command and command[command.index('-m')+1]=='unittest':
            modules=command[command.index('-m')+2:]
            if not modules or any(not name.startswith('test_') or '/' in name or '\\' in name for name in modules):raise ValueError('Unsupported Python test command')
            result.update(owner+'/scripts/'+name+'.py' for name in modules)
        elif '--test' in command:
            names=command[command.index('--test')+1:]
            if not names or any(not name.startswith('test_') or not name.endswith('.mjs') or '/' in name or '\\' in name for name in names):raise ValueError('Unsupported JavaScript test command')
            result.update(owner+'/scripts/'+name for name in names)
        else:raise ValueError('Unrecognized test command')
    return result


def unit_tests(report_path,active=None):
    report_path=Path(report_path).resolve();active=set() if active is None else active
    if report_path in active:raise ValueError('Cyclic inherited test evidence')
    active.add(report_path)
    try:
        report=load(report_path)
        if 'supplemental_executions' in report:
            inherited=report['inherited_report'];path=Path(inherited['path'])
            if sha(path.read_bytes())!=inherited['sha256']:raise ValueError('Inherited test report changed')
            before=unit_tests(path,active);fresh=executed_tests(report['supplemental_executions'])
            if fresh!=set(report['supplemental_tests']):raise ValueError('Supplemental execution does not cover declared tests')
            observed=before|fresh
        else:observed=executed_tests(report['executions'])
        if observed!=set(report['tests']):raise ValueError('Execution commands do not cover declared unit test files')
        return observed
    finally:active.remove(report_path)


def audit(baseline,root,registry,covered):
    root=Path(root).resolve();features=registry['features'];claims={p for f in features for p in f['files']+f['tests']}
    registered_tests={p for f in features for p in f['tests']};rows=[];archive_only=[];errors=[]
    with zipfile.ZipFile(baseline) as archive:
        names=[n for n in archive.namelist() if not n.endswith('/')]
        if len(names)!=len(set(names)):raise ValueError('Duplicate baseline archive member')
        for name in names:
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:raise ValueError('Unsafe baseline member')
            if path.parts[0]=='skills':path=PurePosixPath(*path.parts[1:])
            if not path.parts or path.parts[0] not in OWNERS:
                archive_only.append(name);continue
            relative=path.as_posix();target=root/relative;present=target.is_file();raw=archive.read(name)
            source_script='scripts' in path.parts and path.suffix in ('.py','.mjs')
            test=source_script and path.name.startswith('test_')
            row=dict(path=relative,original_sha256=sha(raw),current_sha256=sha(target.read_bytes()) if present else None,
                present=present,changed_since_original=present and sha(raw)!=sha(target.read_bytes()),
                feature_ids=[f['id'] for f in features if relative in f['files']+f['tests']],
                executable_source=source_script,is_test=test,current_unit_evidence=test and relative in covered)
            rows.append(row)
            if not present:errors.append('missing original skill asset: '+relative)
            if source_script and relative not in claims:errors.append('unregistered original executable: '+relative)
            if test and relative not in covered:errors.append('original test lacks current executable evidence: '+relative)
    missing_tests=sorted(registered_tests-covered)
    errors.extend('registered test lacks current executable evidence: '+path for path in missing_tests)
    return dict(status='asset_and_executable_unit_inheritance_checked_not_native_acceptance' if not errors else 'incomplete_asset_or_unit_inheritance',
        errors=errors,original_skill_assets=len(rows),original_tests=sum(row['is_test'] for row in rows),
        archive_only_artifacts=archive_only,assets=rows,registered_features=len(features),registered_test_files=len(registered_tests),
        missing_registered_tests=missing_tests,
        feature_ledger=[dict(feature_id=f['id'],origin=f['origin'],implementation_entries=f['files'],applicable_families=f['families'],
            tests=[dict(path=t,current_unit_evidence=t in covered) for t in f['tests']],depends_on=f.get('depends_on',[]),
            declared_acceptance_status=f['acceptance_status'],native_whole_scope_evidence='not_established_by_this_asset_audit',
            evidence_references=f['evidence_references']) for f in features],
        whole_historical_native_matrix_passed=False,LF20_native_regression_passed=False,human_accepted=False,whole_goal_complete=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,required=True)
    parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--registry',type=Path,default=Path(__file__).resolve().parents[1]/'assets/feature-registry.json')
    parser.add_argument('--unit-report',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    registry,_=load_registry(args.registry,args.source_root);covered=unit_tests(args.unit_report)
    result=audit(args.baseline,args.source_root,registry,covered)
    result['inputs']={key:dict(path=str(path.resolve()),sha256=sha(path.read_bytes())) for key,path in
        [('baseline',args.baseline),('registry',args.registry),('unit_report',args.unit_report)]}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps({key:result[key] for key in ('status','original_skill_assets','original_tests','registered_features','registered_test_files','errors')}))
    return 2 if result['errors'] else 0


if __name__=='__main__':raise SystemExit(main())
