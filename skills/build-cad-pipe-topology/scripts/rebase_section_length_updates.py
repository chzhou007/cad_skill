"""Rebase source-only section lengths onto a later compatible graph."""
import copy
import math
import argparse
import hashlib
import json
from pathlib import Path

CHANGED = {'length_scope', 'length_scope_before_graphic_separation', 'path_length',
           'path_length_before_graphic_separation', 'path_length_complete', 'path_length_scope'}
WITNESS = ('system', 'source_handles', 'attribute_paths', 'path_points', 'path_length',
           'source_path_length', 'source_connector_handles', 'semantic_bridge_drawing_length',
           'path_length_complete', 'path_length_scope')


def apply(control, variant, target, source_sha):
    if not source_sha or any(g.get('metadata', {}).get('source_sha256') != source_sha for g in (control, variant, target)):
        raise ValueError('section length rebase source mismatch')
    if control['nodes'] != variant['nodes']:
        raise ValueError('entry nodes changed')
    def index(g):
        result = {e['edge_id']: e for e in g['edges']}
        if len(result) != len(g['edges']): raise ValueError('duplicate edge identity')
        return result
    a, b, t = index(control), index(variant), index(target)
    if set(a) != set(b): raise ValueError('entry edge identities changed')
    changes=[]
    for eid, old in a.items():
        new=b[eid]
        diff={k for k in set(old)|set(new) if old.get(k)!=new.get(k)}
        if not diff:continue
        if diff != CHANGED or old.get('connection_mode') != 'source_calibrated_pipe_section_continuity' or new.get('path_length_complete') is not False or new.get('path_length_scope') != 'source_drawn_pipe_only_section_connector_length_unknown':
            raise ValueError('unexpected entry graph change: '+eid)
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (new.get('path_length'),old.get('source_path_length'),new.get('path_length_before_graphic_separation'),old.get('path_length'))) or abs(new['path_length']-old['source_path_length'])>.1 or new['path_length_before_graphic_separation'] != old['path_length']:
            raise ValueError('entry source length mismatch: '+eid)
        if eid not in t or any(old.get(k) != t[eid].get(k) for k in WITNESS):
            raise ValueError('target source path or length changed: '+eid)
        changes.append(eid)
    if not changes:raise ValueError('no source length updates')
    result=copy.deepcopy(target);dest=index(result)
    for eid in changes:
        for key in sorted(CHANGED):dest[eid][key]=copy.deepcopy(b[eid][key])
    result.setdefault('metadata',{})['hil_ready']=False
    return result, {'changed_edge_ids': sorted(changes), 'node_count':len(result['nodes']),
                    'edge_count':len(result['edges']), 'topology_changed':False,
                    'requires_expert_review':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('control','variant','target','policy','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    policy=json.loads(args.policy.read_text(encoding='utf8'))
    inputs=[]
    for name in ('control','variant','target'):
        data=getattr(args,name).read_bytes();actual=hashlib.sha256(data).hexdigest()
        if actual!=policy.get(name+'_sha256'):raise ValueError(name+' graph hash mismatch')
        inputs.append(json.loads(data))
    result,audit=apply(*inputs,policy.get('source_sha256'))
    if args.output.exists():raise ValueError('output already exists')
    args.output.mkdir(parents=True)
    path=args.output/'graph_with_edges.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    audit.update(input_hashes={name:policy[name+'_sha256'] for name in ('control','variant','target')},source_sha256=policy['source_sha256'],output_graph_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (args.output/'composition-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'changed_edges':len(audit['changed_edge_ids']),'output_graph_sha256':audit['output_graph_sha256'],'hil_ready':False},ensure_ascii=False))


if __name__=='__main__':main()
