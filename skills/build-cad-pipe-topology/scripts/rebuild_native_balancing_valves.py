"""Source-bound batch adapter; immutable old graph/CSV remain authoritative inputs."""
import argparse,csv,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_balancing_valve_recovery import recover,MODE

def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('native_balancing_valve_recovery','native_inline_coordinates','native_line_path_evidence','source_readability')})
def compute(manifest):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=v['sha256']for k,v in inputs.items()):raise ValueError('native valve input changed')
    checked();doc,preflight=read_source(paths['source']);graph=load(paths['graph'])
    if graph['metadata']['source_sha256']!=inputs['source']['sha256']:raise ValueError('native valve graph/source differs')
    with paths['components'].open(encoding='utf-8-sig',newline='')as f:components=list(csv.DictReader(f))
    r=recover(doc,graph,components);checked()
    return dict(r,inputs=inputs,source_preflight=preflight,published_graph_changed=False)
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('native valve implementation changed')
    output.mkdir(parents=True);p=output/'native-balancing-valves.json';p.write_bytes(encode(r))
    cp=output/'edge_device_instances.csv'
    with cp.open('w',encoding='utf-8-sig',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(r['components'][0]));w.writeheader();w.writerows(r['components'])
    (output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p),components_sha256=sha(cp))))
    return r
def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'native-balancing-valves.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']or sha(output/'edge_device_instances.csv')!=rc['components_sha256']:raise ValueError('native valve receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('native valve native replay differs')
    with (output/'edge_device_instances.csv').open(encoding='utf-8-sig',newline='')as f:
        if list(csv.DictReader(f))!=r['components']:raise ValueError('native valve output CSV differs')
    return r
def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('manifest and new output required')
        r=produce(a.manifest,a.output)
    print(r['counts'],flush=True)
if __name__=='__main__':main()
