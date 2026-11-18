import argparse,importlib,sys,csv
from pathlib import Path
for name in('orchestrate-cad-drawing-pipeline','visualize-cad-pipe-topology'):
    p=Path(__file__).resolve().parents[2]/name/'scripts'
    if str(p)not in sys.path:sys.path.insert(0,str(p))
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from rebuild_native_balancing_valves import verify_output as valve_inventory
from compound_carrier_atom_origins import refine
from native_paired_caption_geometry import collect as captions
from compound_riser_header_members import reconstruct,MODE

def compute(manifest):
    inputs=manifest['inputs'];paths={k:Path(v['path'])for k,v in inputs.items()}
    def checked():
        if any(sha(paths[k])!=s['sha256']for k,s in inputs.items()):raise ValueError('riser member source input changed')
    checked();pg=load(paths['plan_graph']);ag=load(paths['axis_graph']);pd,pp=read_source(paths['plan_source']);ad,ap=read_source(paths['axis_source'])
    if any(g['metadata']['source_sha256']!=inputs[k]['sha256']for g,k in[(pg,'plan_source'),(ag,'axis_source')]):raise ValueError('riser graph source differs')
    inv=valve_inventory(paths['valve_inventory'].parent)
    for k,v in [('source','axis_source'),('graph','axis_graph')]:
        if inv['inputs'][k]['sha256']!=inputs[v]['sha256']:raise ValueError('riser supplemental component source differs')
    with paths['plan_components'].open(encoding='utf-8-sig')as f:pc=list(csv.DictReader(f))
    proposal=load(paths['riser_proposals']);floor=str(manifest['floor']);roles=proposal['floors'][floor]['discovery']['riser_role_evidence']
    # Old role artifacts are discovery inputs only. Native roles, paths and Ts
    # are independently checked here; old gate identities still need revalidation.
    risks=refine(pd,pg,inputs['plan_source']['sha256'])
    r=reconstruct(pd,ad,pg,ag,pc,inv['components'],roles,risks,captions(ad),{k:inputs[k]['sha256']for k in('plan_source','plan_graph','axis_source','axis_graph')});checked()
    return dict(r,inputs=inputs,source_preflight=dict(plan=pp,axis=ap),balancing_inventory_native_replayed=True,old_role_candidates_not_promoted_to_confirmed_anchors=True)
def implementation_hashes():
    return dict(entry=sha(__file__),**{n:sha(importlib.import_module(n).__file__)for n in('compound_riser_header_members','compound_carrier_atom_origins','native_paired_caption_geometry','native_inline_coordinates','crossview_equipment_branch_inventory','batch_native_path_coverage','compound_member_interfaces','rebuild_native_balancing_valves','native_balancing_valve_recovery','source_readability')})
def produce(manifest,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    code=implementation_hashes();r=compute(load(manifest))
    if code!=implementation_hashes():raise ValueError('riser member implementation changed')
    output.mkdir(parents=True);p=output/'compound-riser-header-members.json';p.write_bytes(encode(r));(output/'receipt.json').write_bytes(encode(dict(mode=MODE,manifest=dict(path=str(Path(manifest).resolve()),sha256=sha(manifest)),implementation_sha256=code,output_sha256=sha(p))))
    return r
def verify_output(output):
    output=Path(output);rc=load(output/'receipt.json');m=rc['manifest'];p=output/'compound-riser-header-members.json'
    if rc['mode']!=MODE or rc['implementation_sha256']!=implementation_hashes()or sha(m['path'])!=m['sha256']or sha(p)!=rc['output_sha256']:raise ValueError('riser member receipt changed')
    r=compute(load(m['path']))
    if encode(r)!=p.read_bytes():raise ValueError('riser member native replay differs')
    return r
def main():
    p=argparse.ArgumentParser()
    for n in('manifest','output','verify-output'):p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.verify_output:r=verify_output(a.verify_output)
    else:
        if not a.manifest or not a.output:p.error('manifest and new output required')
        r=produce(a.manifest,a.output)
    print(dict(scoped_member_edges=r['scoped_member_edges'],conditional_interval_candidates=r['conditional_interval_candidates'],pending=r['pending']),flush=True)
if __name__=='__main__':main()
