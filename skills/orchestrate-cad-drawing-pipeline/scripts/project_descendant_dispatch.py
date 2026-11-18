"""Read graph-bound project scope declarations and dispatch native comparison."""
from pathlib import Path
from project_scoped_descendant_source_gate import check_project_descendant
from confirm_crossview_paths import load,sha


def snapshot_scope(graph_path,graph_hash,graph):
    graph_path=Path(graph_path).resolve()
    if 'sourceDeclaredCappedBranchInterfaces' not in graph:return None,None
    declaration=(graph_path.parent/'project-descendant-snapshot-scope.json').resolve()
    if not declaration.is_relative_to(graph_path.parent) or not declaration.is_file():raise ValueError('missing graph-bound project mapping scope declaration')
    value=load(declaration)
    if not isinstance(value,dict) or set(value)!={'graph_sha256','mapping'} or value['graph_sha256']!=graph_hash:raise ValueError('project scope declaration graph identity differs')
    row=value['mapping']
    if not isinstance(row,dict) or set(row)!={'path','sha256'} or not isinstance(row['path'],str) or not row['path']:raise ValueError('invalid project mapping snapshot declaration')
    mapping=Path(row['path']);mapping=(mapping if mapping.is_absolute() else declaration.parent/mapping).resolve()
    if not mapping.is_file() or sha(mapping)!=row['sha256']:raise ValueError('project mapping snapshot declaration is stale')
    return dict(path=str(mapping),sha256=row['sha256']),declaration


def check(root,report,graph_hash,graph_path):
    root=Path(root).resolve();graph_path=Path(graph_path).resolve();graph=load(graph_path)
    if not graph_path.is_relative_to(root) or sha(graph_path)!=graph_hash:raise ValueError('project comparison graph path or hash differs')
    scope,declaration=snapshot_scope(graph_path,graph_hash,graph)
    result=check_project_descendant(graph_path.parent,report,graph_path,Path(scope['path']) if scope else None,scope['sha256'] if scope else None)
    result['project_scoped_descendant_stage'].update(dispatch_sha256=sha(__file__),
        snapshot_declaration=None if declaration is None else dict(path=str(declaration),sha256=sha(declaration)))
    return result
