"""Inherit segment DN checks, excluding only freshly qualified display stems.

The original reader stays unchanged. Its private dependency namespace filters
exact source-chain primitives from pipe competition; the original document,
F checks, label/transform checks and all remaining competitors are preserved.
"""
import argparse,copy,math,runpy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_valve_display_stub_evidence import collect as qualify_stubs,implementation_hashes as stub_hashes
from native_segment_dn_candidates import collect as inherited_collect
from native_line_path_evidence import collect as collect_lines
from source_readability import read_source

MODE='native_segment_DN_display_stub_qualified_v1'


def collect(doc,graph,line_evidence,policy,source_hash,graph_hash,line_hash):
    if not policy.get('display_stub_policy'):return inherited_collect(doc,graph,line_evidence,policy,source_hash,graph_hash,line_hash)
    qualification=qualify_stubs(doc,graph,policy['display_stub_policy'],source_hash,graph_hash)
    exclusions={(r['root_handle'],r['source_chain'][-1]):r for r in qualification['records']}
    if len(exclusions)!=len(qualification['records']):raise ValueError('duplicate qualified display-stem exclusion')
    namespace=runpy.run_path(str(Path(__file__).with_name('native_segment_dn_candidates.py')))
    reader=namespace['collect'];original=reader.__globals__['recursive_decompose'];consumed={key:0 for key in exclusions}
    def primitives(roots):
        if len(roots)!=1:raise ValueError('qualified competitor decomposition needs one native source root')
        root=roots[0]
        for entity in original(roots):
            source=entity.source_of_copy;key=(root.dxf.handle,source.dxf.handle if source is not None else None)
            if key in exclusions:
                row=exclusions[key]
                if entity.dxftype()!='LINE' or entity.dxf.layer!=row['source_layer']:raise ValueError('qualified display primitive type/layer changed')
                xyz=[list(entity.dxf.start),list(entity.dxf.end)]
                if any(math.dist(a,b)>.05 for a,b in zip(xyz,row['native_XYZ'])):raise ValueError('qualified display primitive transform changed')
                consumed[key]+=1
                if consumed[key]!=1:raise ValueError('qualified display primitive decomposes more than once')
                continue
            yield entity
    reader.__globals__['recursive_decompose']=primitives
    result=reader(doc,graph,line_evidence,copy.deepcopy(policy),source_hash,graph_hash,line_hash)
    if any(n!=1 for n in consumed.values()):raise ValueError('qualified display source chain was not independently encountered')
    result.update(native_display_stem_qualification=qualification,excluded_competing_source_chains=[r['source_chain'] for r in qualification['records']],
        original_native_document_unchanged=True,all_other_native_competitors_retained=True,physical_values_fused=False,human_accepted=False)
    return result


def implementation_hashes():
    hashes=stub_hashes()
    for name in ('native_segment_dn_candidates_v2.py','native_segment_dn_candidates.py','native_dn_text_position.py','source_direct_dn_evidence.py','pipe_annotation_attributes.py'):
        hashes[name]=sha(Path(__file__).with_name(name))
    return hashes


def compute(paths,policy):
    for key in ('source','graph','line_policy','line_evidence'):
        if sha(paths[key])!=policy.get(key+'_sha256'):raise ValueError('qualified segment-DN input changed '+key)
    doc,preflight=read_source(paths['source']);graph=load(paths['graph']);linepolicy=load(paths['line_policy'])
    fresh=collect_lines(doc,graph,linepolicy,sha(paths['source']),sha(paths['graph']))
    if encode(fresh)!=Path(paths['line_evidence']).read_bytes():raise ValueError('segment-DN native line evidence does not replay')
    result=collect(doc,graph,fresh,policy,sha(paths['source']),sha(paths['graph']),sha(paths['line_evidence']))
    result.update(mode=MODE,source_preflight=preflight,local_graph_mutated=False,physical_values_fused=False,human_accepted=False)
    return result


def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'source-segment-DN-receipt.json')
    if receipt.get('mode')!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('qualified segment-DN implementation changed')
    for item in receipt['inputs'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('qualified segment-DN dependency changed')
    paths={k:v['path'] for k,v in receipt['inputs'].items()};result=compute(paths,load(paths['policy']))
    if encode(result)!=(directory/'segment-DN-evidence.json').read_bytes() or sha(directory/'segment-DN-evidence.json')!=receipt['output_sha256']:raise ValueError('qualified segment-DN native replay differs')
    return result


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','line-policy','line-evidence','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args();paths={k:getattr(a,k) for k in ('source','graph','line_policy','line_evidence','policy')}
    if a.output.exists():raise FileExistsError(a.output)
    result=compute(paths,load(a.policy));a.output.mkdir(parents=True);(a.output/'segment-DN-evidence.json').write_bytes(encode(result))
    receipt=dict(mode=MODE,inputs={k:dict(path=str(v.resolve()),sha256=sha(v)) for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(a.output/'segment-DN-evidence.json'),human_accepted=False)
    (a.output/'source-segment-DN-receipt.json').write_bytes(encode(receipt));print(dict(observations=len(result['observations']),qualified_display_stems=len(result.get('excluded_competing_source_chains',[])),physical_values_fused=False),flush=True)


if __name__=='__main__':main()
