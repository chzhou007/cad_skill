import argparse,importlib,sys
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from compound_carrier_atom_origins import refine,MODE

def compute(manifest):
    paths={k:Path(v['path'])for k,v in manifest['inputs'].items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in manifest['inputs'].items()):raise ValueError('atom-origin source input changed')
    checked();floors={}
    for floor in manifest['floors']:
        f=str(floor);graph=load(paths['plan_graph_'+f]);doc,preflight=read_source(paths['plan_source_'+f])
        if graph['metadata']['source_sha256']!=sha(paths['plan_source_'+f]):raise ValueError('atom-origin graph source differs')
        floors[f]=dict(refine(doc,graph,sha(paths['plan_source_'+f])),source_preflight=preflight)
    checked();return dict(mode=MODE,inputs=manifest['inputs'],floors=floors,counts=dict(original_corridors=sum(len(f['original_risks']['corridors'])for f in floors.values()),retained_corridors=sum(len(f['corridors'])for f in floors.values()),excluded_other_arm_origins=sum(len(f['excluded_other_arm_origins'])for f in floors.values())),
        source_or_graph_mutated=False,physical_members_assigned=0,DN_or_lengths_assigned=0,human_accepted=False)
def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('compound_carrier_atom_origins','compound_carrier_members','source_compound_dn_evidence','native_paired_caption_geometry','source_readability')})
def produce(manifest_path,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest_path))
    if code!=implementation_hashes():raise ValueError('atom-origin implementation changed')
    output.mkdir(parents=True);p=output/'compound-carrier-atom-origins.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest_path).resolve()),sha256=sha(manifest_path)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);receipt=load(output/'receipt.json');m=receipt['manifest'];p=output/'compound-carrier-atom-origins.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=receipt['output_sha256']:raise ValueError('atom-origin receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('atom-origin source replay differs')
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
