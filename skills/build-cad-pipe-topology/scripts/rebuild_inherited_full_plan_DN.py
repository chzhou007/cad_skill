"""Versioned whole-plan DN producer using inherited native annotation entries."""
import argparse,copy,importlib,sys,types
from pathlib import Path
_PIPELINE=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(_PIPELINE)not in sys.path:sys.path.insert(0,str(_PIPELINE))
from confirm_crossview_paths import load,sha,encode
from rebuild_full_plan_DN import compute as original_compute,implementation_hashes as original_hashes,checked
from full_plan_DN_inherited_annotations import collect

MODE='complete_local_plan_native_DN_inherited_annotations_v2'


def configuration(item):
    specs=item.get('inherited_annotation_inputs',{});paths={k:checked(v)for k,v in specs.items()};config={}
    source_hash=item['inputs']['source']['sha256']
    if 'F_origin'in paths:
        origin=load(paths['F_origin'])
        if origin['source_sha256']!=source_hash:raise ValueError('ordered F origin belongs to another native source')
        frames=[r for g in origin['groups']for r in g.get('line_F_frames',[])]
        if not frames:raise ValueError('ordered F origin has no explicit native frames')
        config['line_F_frames']=frames
    if 'calibration_policy'in paths or 'calibration_origin_graph'in paths:
        if not {'calibration_policy','calibration_origin_graph'}<=paths.keys():raise ValueError('complete original native calibration inputs required')
        policy=load(paths['calibration_policy']);origin=load(paths['calibration_origin_graph'])
        if policy['source_sha256']!=source_hash or policy['graph_sha256']!=sha(paths['calibration_origin_graph']):
            raise ValueError('original native calibration source or graph changed')
        config['calibration']=dict(policy=policy,original_graph=origin,original_graph_sha256=sha(paths['calibration_origin_graph']))
    if set(paths)-{'F_origin','calibration_policy','calibration_origin_graph'}:raise ValueError('unsupported inherited annotation input')
    return config


def compute(manifest,announce=lambda x:None):
    configs={item['inputs']['graph']['sha256']:configuration(item)for item in manifest['plans']}
    namespace=dict(original_compute.__globals__)
    namespace['collect']=lambda doc,graph,sh,gh,seeds,log,circle:collect(doc,graph,sh,gh,seeds,log,circle,configs[gh])
    reader=types.FunctionType(original_compute.__code__,namespace,original_compute.__name__)
    result=reader(manifest,announce)
    result['previous_mode']=result['mode'];result['mode']=MODE
    result['inherited_annotation_origins']={str(item['floor']):copy.deepcopy(item.get('inherited_annotation_inputs',{}))for item in manifest['plans']}
    for item in manifest['plans']:configuration(item)
    result['historical_native_implementations_or_globals_changed']=False
    return result


def implementation_hashes():
    result=original_hashes()
    for name in ('full_plan_DN_inherited_annotations','current_graph_calibrated_dn','calibrated_direct_dn_evidence','native_line_f_diameter_evidence'):
        result[name]=sha(importlib.import_module(name).__file__)
    result['inherited_entry']=sha(__file__)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'inherited-plan-DN-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('inherited full-plan DN implementation changed')
    result=compute(load(checked(receipt['manifest'])))
    target=directory/'inherited-plan-DN-results.json'
    if sha(target)!=receipt['output_sha256']or encode(result)!=target.read_bytes():raise ValueError('complete inherited plan DN native independent replay differs')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.manifest or a.output:p.error('verification cannot replace inputs')
        print(verify_output(a.verify_output)['counts']);return
    if not a.manifest or not a.output:p.error('fixed manifest and new output required')
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(load(a.manifest),lambda s:print(s,flush=True));a.output.mkdir(parents=True)
    target=a.output/'inherited-plan-DN-results.json';target.write_bytes(encode(result))
    (a.output/'inherited-plan-DN-receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(a.manifest.resolve()),sha256=sha(a.manifest)),
        implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(result['counts'],flush=True)


if __name__=='__main__':main()
