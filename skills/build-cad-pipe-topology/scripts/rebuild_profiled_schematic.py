"""Apply inherited source-profile instrumentation in the shared schematic entry.

Uses an isolated function namespace; original builder and instrumentation module
bytes/globals stay unchanged. No geometry, source layers or project IDs are
hardcoded. Unsupported shapes remain in the original unresolved inventory.
"""
import argparse,hashlib,json,types
from pathlib import Path
import build_schematic as original
from profiled_single_tap_instruments import single_tap_measurements,INHERITED_RECOGNIZER_AST_SHA256

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def measurement_reader(base,statistics):
    def profiled(doc,segments,symbols,config):
        kept,groups,members=base(doc,segments,symbols,config)
        remaining=[s for s in symbols if s['handle']not in members]
        extra,consumed=single_tap_measurements(doc,kept,remaining,config.get('single_tap_rules',[]))
        if len({g['id']for g in groups+extra})!=len(groups)+len(extra):raise ValueError('measurement assembly identity conflict')
        statistics.append(dict(inherited_groups=len(groups),profiled_groups=len(extra),source_members=sorted(consumed),hydraulic_connections_created=0))
        return kept,groups+extra,members|consumed
    return profiled

def build(args):
    paths=[args.dxf,args.bindings,args.profiles,args.config]+([args.materials]if args.materials else[])
    inputs={str(Path(p).resolve()):sha(p)for p in paths};statistics=[]
    globals_=dict(original.build.__globals__,measurement_assemblies=measurement_reader(original.measurement_assemblies,statistics))
    entry=types.FunctionType(original.build.__code__,globals_,original.build.__name__,original.build.__defaults__,original.build.__closure__);entry.__kwdefaults__=original.build.__kwdefaults__
    entry(args)
    if any(sha(p)!=h for p,h in inputs.items()):raise ValueError('profiled schematic inputs changed during reconstruction')
    graph=args.output_dir/'graph_with_edges.json';report=dict(mode='inherited_profiled_single_tap_schematic_rebuild_v1',inputs=inputs,graph_sha256=sha(graph),inherited_recognizer_ast_sha256=INHERITED_RECOGNIZER_AST_SHA256,original_builder_sha256=sha(original.__file__),reader_sha256=sha(Path(__file__).with_name('profiled_single_tap_instruments.py')),statistics=statistics,original_builder_globals_changed=False,source_geometry_modified=False,hydraulic_connections_created_by_instrumentation=0,human_accepted=False)
    (args.output_dir/'profiled-instrumentation-rebuild.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8');return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['dxf','bindings','profiles','config','output-dir']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--materials',type=Path);p.add_argument('--previous-graph',type=Path);p.add_argument('--no-overwrite',action='store_true');a=p.parse_args();r=build(a);print(json.dumps({k:v for k,v in r.items()if k not in ['inputs']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
