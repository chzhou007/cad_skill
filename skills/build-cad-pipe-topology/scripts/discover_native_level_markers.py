"""Discover policies for the existing native level-marker verifier.

Discovery adds no datum geometry algorithm or pipe metric interpretation.
Only unambiguous stacks accepted by native_level_evidence.verify are reported.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from native_level_evidence import verify,floor_number,elevation_value
from source_readability import read_source

MODE='native_level_marker_batch_discovery_using_original_verifier_v1'
TOL=.05

def point(entity,name):return list(getattr(entity.dxf,name))[:2]
def key(p):return tuple(math.floor(v/TOL)for v in p)
def add(index,p,value):index[key(p)].append((p,value))
def near(index,p):
    a,b=key(p)
    return [value for i in range(a-1,a+2)for j in range(b-1,b+2)for q,value in index.get((i,j),[])if math.dist(p,q)<=TOL]
def horizontal(entity):return abs(entity.dxf.start.y-entity.dxf.end.y)<=TOL and abs(entity.dxf.start.x-entity.dxf.end.x)>TOL
def plain_supported(entity):
    return abs(float(entity.dxf.get('rotation',0)))<=1e-8 and math.dist(list(entity.dxf.get('extrusion',(0,0,1))),(0,0,1))<=1e-8 and float(entity.dxf.height)>0

def discover(doc,source_hash):
    if len(source_hash)!=64 or any(c not in'0123456789abcdef'for c in source_hash):raise ValueError('native source SHA256 required')
    text=[e for e in doc.modelspace().query('TEXT')];floors=[e for e in text if floor_number(e.plain_text())is not None]
    numerics=[]
    for entity in text:
        try:elevation_value(entity.plain_text())
        except ValueError:continue
        if plain_supported(entity):numerics.append(entity)
    lines=[e for e in doc.modelspace().query('LINE')if all(math.isfinite(v)for p in(e.dxf.start,e.dxf.end)for v in p)]
    starts=collections.defaultdict(list);endpoints=collections.defaultdict(list);baselines=collections.defaultdict(list)
    for line in lines:
        add(starts,point(line,'start'),line)
        if horizontal(line):
            add(endpoints,point(line,'start'),line);add(endpoints,point(line,'end'),line)
            baselines[math.floor(line.dxf.start.y/TOL)].append(line)
    candidates=[];signatures=set()
    for left in lines:
        apex=point(left,'start');tip=point(left,'end');layer=left.dxf.layer
        if not(tip[0]<apex[0]-TOL and tip[1]>apex[1]+TOL):continue
        for right in near(starts,apex):
            rt=point(right,'end')
            if (right.dxf.layer!=layer or rt[0]<=apex[0]+TOL or abs(rt[1]-tip[1])>TOL
                or abs((apex[0]-tip[0])-(rt[0]-apex[0]))>TOL):continue
            row=math.floor(apex[1]/TOL)
            bases=[e for i in range(row-1,row+2)for e in baselines.get(i,[])if abs(e.dxf.start.y-apex[1])<=TOL
                and min(e.dxf.start.x,e.dxf.end.x)<=apex[0]<=max(e.dxf.start.x,e.dxf.end.x)]
            leaders=[e for e in near(endpoints,rt)if e.dxf.layer==layer]
            for baseline in bases:
                for leader in leaders:
                    if len({left.dxf.handle,right.dxf.handle,baseline.dxf.handle,leader.dxf.handle})!=4:continue
                    lx=min(leader.dxf.start.x,leader.dxf.end.x);ly=leader.dxf.start.y
                    for ft in floors:
                        fp=point(ft,'insert');fh=float(ft.dxf.height)
                        if (ft.dxf.layer!=layer or not plain_supported(ft)or not(apex[0]<fp[0]<=max(baseline.dxf.start.x,baseline.dxf.end.x))
                            or not 0<=fp[1]-baseline.dxf.start.y<=2*fh):continue
                        for et in numerics:
                            ep=point(et,'insert');eh=float(et.dxf.height)
                            if et.dxf.layer!=layer or abs(ep[0]-lx)>eh or not 0<=ep[1]-ly<=2*eh:continue
                            spec=dict(floor_number=floor_number(ft.plain_text()),floor_text=ft.dxf.handle,elevation_text=et.dxf.handle,
                                baseline=baseline.dxf.handle,left_arm=left.dxf.handle,right_arm=right.dxf.handle,leader=leader.dxf.handle,
                                elevation_text_expected=et.plain_text(),annotation_layer=layer,baseline_layer=baseline.dxf.layer)
                            signature=tuple(spec[k]for k in('floor_text','elevation_text','baseline','left_arm','right_arm','leader'))
                            if signature in signatures:continue
                            signatures.add(signature);candidates.append(dict(apex=apex,spec=spec))
    groups=[]
    for candidate in sorted(candidates,key=lambda c:(c['spec']['annotation_layer'],c['spec']['baseline_layer'],c['apex'][0],c['apex'][1])):
        matching=[g for g in groups if g['annotation_layer']==candidate['spec']['annotation_layer']and g['baseline_layer']==candidate['spec']['baseline_layer']and abs(g['apex_x']-candidate['apex'][0])<=TOL]
        if len(matching)>1:raise ValueError('overlapping datum stack discovery ranges')
        if matching:g=matching[0]
        else:
            g=dict(apex_x=candidate['apex'][0],annotation_layer=candidate['spec']['annotation_layer'],baseline_layer=candidate['spec']['baseline_layer'],candidates=[]);groups.append(g)
        g['candidates'].append(candidate['spec'])
    accepted=[];pending=[];used=set()
    for group in groups:
        specs=group['candidates'];policy=dict(source_sha256=source_hash,markers=sorted(specs,key=lambda r:r['floor_number']))
        if len({s['floor_number']for s in specs})!=len(specs):reason='multiple_native_policies_claim_the_same_floor_in_one_stack'
        else:
            try:proof=verify(doc,policy,source_hash)
            except ValueError as exc:reason=str(exc)
            else:
                accepted.append(dict(status='existing_native_level_verifier_replayed',policy=policy,verification=proof,
                    stack_apex_x=group['apex_x'],pipe_lengths_assigned=0,graph_mutated=False,human_accepted=False))
                used.update(s['floor_text']for s in specs);continue
        pending.append(dict(reason=reason,stack_apex_x=group['apex_x'],candidates=specs))
    shared=collections.Counter(h for group in accepted for spec in group['policy']['markers']for h in(spec[k]for k in('floor_text','elevation_text','baseline','left_arm','right_arm','leader')))
    conflicted=[g for g in accepted if any(shared[s[k]]>1 for s in g['policy']['markers']for k in('floor_text','elevation_text','baseline','left_arm','right_arm','leader'))]
    for group in conflicted:
        accepted.remove(group);pending.append(dict(reason='competing_native_stacks_share_source_symbols',stack_apex_x=group['stack_apex_x'],candidates=group['policy']['markers']))
    used={s['floor_text']for g in accepted for s in g['policy']['markers']}
    unresolved=[dict(handle=e.dxf.handle,text=e.plain_text(),reason='unsupported_rotation_or_OCS'if not plain_supported(e)else'no_unambiguous_native_symbol_stack')for e in floors if e.dxf.handle not in used]
    return dict(mode=MODE,source_sha256=source_hash,groups=accepted,pending_stacks=pending,unresolved_floor_texts=unresolved,
        candidate_marker_count=len(candidates),original_verifier='native_level_evidence.verify',physical_lengths_assigned=0,
        pipe_floors_assigned=0,graph_mutated=False,human_accepted=False,hil_ready=False)

def implementation_hashes():
    import native_level_evidence,source_readability
    return dict(entry=sha(__file__),original_verifier=sha(native_level_evidence.__file__),readability=sha(source_readability.__file__))

def compute(source):
    doc,preflight=read_source(source);digest=preflight['source_sha256']
    if sha(source)!=digest:raise ValueError('source changed after strict native decoding')
    result=discover(doc,digest)
    if sha(source)!=digest:raise ValueError('source changed during marker discovery')
    result['source_preflight']=preflight;return result

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'native-level-discovery-receipt.json');target=directory/'native-level-discovery.json'
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('level discovery implementation changed')
    source=Path(receipt['source']['path'])
    if sha(source)!=receipt['source']['sha256']or sha(target)!=receipt['output_sha256']:raise ValueError('level discovery source/output changed')
    result=compute(source)
    if result!=load(target):raise ValueError('independent native level discovery differs')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);p.add_argument('--verify-output',type=Path);args=p.parse_args()
    if args.verify_output:
        if args.source or args.output:p.error('verification cannot replace source/output')
        result=verify_output(args.verify_output)
    else:
        if not args.source or not args.output:p.error('fixed native source and new output directory required')
        if args.output.exists():raise FileExistsError(args.output)
        result=compute(args.source);args.output.mkdir(parents=True);target=args.output/'native-level-discovery.json';target.write_bytes(encode(result))
        (args.output/'native-level-discovery-receipt.json').write_bytes(encode(dict(mode=MODE,source=dict(path=str(args.source.resolve()),sha256=sha(args.source)),implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(stacks=len(result['groups']),markers=sum(len(g['policy']['markers'])for g in result['groups']),unresolved=len(result['unresolved_floor_texts']),physical_lengths_assigned=0),flush=True)

if __name__=='__main__':main()
