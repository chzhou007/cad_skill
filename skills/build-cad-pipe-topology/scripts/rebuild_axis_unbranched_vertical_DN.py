"""Freshly replay original axis annotation owners, then inherit local vertical DN."""
import argparse,importlib,sys
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from axis_attribute_source_routing import verify_output as verify_route
from axis_vertical_DN_batch import verify_output as verify_annotations
from axis_unbranched_vertical_DN import collect,MODE

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in manifest['inputs'].items()):raise ValueError('axis unbranched DN input changed')
    checked();route=verify_route(paths['routing'].parent);annotations=verify_annotations(paths['annotations'].parent)
    if route['inputs']['source']['sha256']!=sha(paths['source'])or route['inputs']['graph']['sha256']!=sha(paths['graph']):raise ValueError('native axis direction source scope differs')
    current=load(paths['viewer_manifest'])
    if current['sourceHashes']['graph']!=sha(paths['raw_axis_graph'])or current['sourceHashes']['main_dxf']!=sha(paths['source']):raise ValueError('retained vertical values belong to another current axis source')
    doc,readable=read_source(paths['source']);result=collect(doc,load(paths['graph']),load(paths['raw_axis_graph']),route,annotations,sha(paths['source']),sha(paths['graph']))
    checked();result.update(inputs=manifest['inputs'],original_native_annotations_independently_replayed=True,original_direction_routing_independently_replayed=True,source_preflight=readable)
    return result

def implementation_hashes():
    names=('axis_unbranched_vertical_DN','axis_vertical_DN_batch','axis_attribute_source_routing','native_repeated_branch_DN_layout',
        'native_line_path_evidence','pipe_annotation_attributes','native_paired_caption_geometry','source_readability')
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in names})

def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    result=compute(load(manifest_path));output.mkdir(parents=True);target=output/'vertical-DN-inheritance.json';target.write_bytes(encode(result))
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    return result

def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];target=output/'vertical-DN-inheritance.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('axis unbranched DN source, code or artifact changed')
    fresh=compute(load(m['path']))
    if encode(fresh)!=target.read_bytes():raise ValueError('independent native vertical DN inheritance differs')
    return fresh

def main():
    p=argparse.ArgumentParser()
    for name in('manifest','output','verify-output'):p.add_argument('--'+name,type=Path)
    args=p.parse_args();from native_projection_runtime_v1 import default_native_runtime
    with default_native_runtime(Path(__file__).resolve().parents[2]):
        if args.verify_output:r=verify_output(args.verify_output)
        else:
            if not args.manifest or not args.output:p.error('fixed manifest and fresh output required')
            r=produce(args.manifest,args.output)
    print(r['counts'],flush=True)
if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
