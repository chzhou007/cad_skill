"""Read multi-DN declarations without collapsing them into one pipe value.

Text evidence does not assign pipe identity, elevation semantics or a connection.
"""
import argparse,hashlib,inspect,json,math,re,unicodedata
from pathlib import Path
from source_readability import read_source

MODE='native_compound_pipe_label_observations_v1'
TOKEN=re.compile(r'DN\s*(\d+(?:\.\d+)?)(?:\s*\(\s*([+-]?\d+(?:\.\d+)?)\s*\))?',re.I)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf8')

def parse(text):
    if not isinstance(text,str):raise TypeError('native text required')
    value=unicodedata.normalize('NFKC',text).strip();parts=re.split(r'\s*/\s*',value)
    if len(parts)<2:return None
    members=[]
    for index,part in enumerate(parts):
        match=TOKEN.fullmatch(part.strip())
        if not match:return None
        dn=float(match[1]);level=match[2]
        if not math.isfinite(dn)or dn<=0:return None
        if level is not None and not math.isfinite(float(level)):return None
        members.append(dict(declaration_index=index,nominal_mm=dn,source_level_text=level,
            pipe_identity=None,physical_elevation_mm=None))
    return dict(raw_text=text,normalized_text=value,members=members,
        scalar_whole_edge_DN_mm=None,multiple_physical_pipes_proven=False,
        level_reference_and_units='not_established_by_text_reader')

def collect(doc,source_hash):
    records=[]
    for entity in doc.modelspace().query('TEXT MTEXT'):
        raw=entity.plain_text();observation=parse(raw)
        if observation is None:continue
        insertion=entity.dxf.insert;extrusion=list(entity.dxf.get('extrusion',(0,0,1)))
        # TEXT insertion is OCS; MTEXT insertion is WCS. Record their actual
        # source coordinate contract without claiming a geometric pipe binding.
        point=entity.ocs().to_wcs(insertion)if entity.dxftype()=='TEXT'else insertion
        position=list(point)
        if any(not math.isfinite(x)for x in position+extrusion):raise ValueError('nonfinite native label geometry')
        records.append(dict(**observation,handle=entity.dxf.handle,entity_type=entity.dxftype(),layer=entity.dxf.layer,
            source_sha256=source_hash,position_WCS=position,source_extrusion=extrusion,
            source_rotation=entity.dxf.get('rotation',0.0),source_scope='modelspace',
            connection_or_pipe_membership_proven=False,physical_length_mm=None,human_accepted=False))
    return dict(mode=MODE,records=records,observations=len(records),scalar_DN_assignments=0,
        physical_pipe_instances_created=0,physical_lengths_assigned=0,graph_mutated=False,
        unsupported_scope='nested/proxy labels are outside this modelspace-only reader; absence does not prove absence in the drawing',
        hil_ready=False,human_accepted=False)

def produce(source,output):
    source=Path(source).resolve();output=Path(output)
    if output.exists():raise FileExistsError(output)
    before=sha(source);doc,preflight=read_source(source)
    if preflight['source_sha256']!=before:raise ValueError('source changed during strict decoding')
    result=collect(doc,before)
    if sha(source)!=before:raise ValueError('source changed during native extraction')
    output.mkdir();(output/'compound-pipe-labels.json').write_bytes(encode(result))
    receipt=dict(mode=MODE,input=dict(path=str(source),sha256=before),source_preflight=preflight,
        implementation_sha256=sha(__file__),source_readability_sha256=sha(inspect.getfile(read_source)),output_sha256=sha(output/'compound-pipe-labels.json'),human_accepted=False)
    (output/'receipt.json').write_bytes(encode(receipt));return result

def verify(output):
    output=Path(output);receipt=json.loads((output/'receipt.json').read_text(encoding='utf8'))
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=sha(__file__)or receipt['source_readability_sha256']!=sha(inspect.getfile(read_source)):raise ValueError('compound label implementation changed')
    source=Path(receipt['input']['path']);before=sha(source)
    if before!=receipt['input']['sha256']or sha(output/'compound-pipe-labels.json')!=receipt['output_sha256']:raise ValueError('compound label input/output changed')
    doc,preflight=read_source(source);current=collect(doc,before)
    if preflight!=receipt['source_preflight']or encode(current)!=(output/'compound-pipe-labels.json').read_bytes()or sha(source)!=before:raise ValueError('native compound label replay differs')
    return dict(status='pending',source_replay='passed',observations=current['observations'],scalar_DN_assignments=0,
        physical_pipe_instances_created=0,hil_ready=False,human_accepted=False,
        pending=['Bind declarations to native physical pipe lanes and compare both views before assigning edge DN or lengths'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);a=p.parse_args()
    if a.verify_output:
        if a.source or a.output:p.error('verification uses its original pinned source')
        value=verify(a.verify_output)
    else:
        if not a.source or not a.output:p.error('--source and --output required')
        value=produce(a.source,a.output)
    print(json.dumps(dict(observations=value['observations'],scalar_DN_assignments=0,physical_lengths_assigned=0),ensure_ascii=False))
if __name__=='__main__':main()
