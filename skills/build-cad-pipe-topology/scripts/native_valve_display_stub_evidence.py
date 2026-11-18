"""Qualify a dangling opposite leg of an already normalized display valve.

This removes no source or graph geometry. Its source-chain evidence can keep
that drawing-only leg out of scalar-DN pipe competition. It never exempts an
entire equipment block, an unknown symbol or an active graph pipe.
"""
import argparse,dataclasses,math,runpy
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from native_line_path_evidence import LAYERS,_on
from ezdxf import bbox


def replay_normalization(doc,system_layers):
    if system_layers!={v:k for k,v in LAYERS.items()}:raise ValueError('display-stub source layers differ from native pipe readers')
    # The legacy module's default layer detector is unsuitable for mixed CAD.
    # A private runpy namespace avoids changing another stage's global detector.
    ns=runpy.run_path(str(Path(__file__).parent/'legacy_v17/analyze_graph.py'))
    ns['collect_pipe_segments'].__globals__['get_system_layers']=lambda current:system_layers
    segments=ns['collect_pipe_segments'](doc);segments,overshoots=ns['trim_short_dangling_overshoots'](segments)
    regions=ns['collect_turn_display_valve_regions'](doc);cleaned,removed=ns['remove_turn_display_valve_stubs'](segments,regions)
    return dict(segments=segments,removals=removed,known_valves=ns['TURN_DISPLAY_VALVE_BLOCK_NAMES'],maximum_length=ns['MAX_VALVE_DISPLAY_STUB_LENGTH'],overshoots=overshoots)


def _points(line):
    if line.dxftype()!='LINE':raise ValueError('display leg is not a native LINE')
    points=[list(line.dxf.start),list(line.dxf.end)]
    if any(not math.isfinite(v) for p in points for v in p) or math.dist(*points)<=.05:raise ValueError('invalid display leg coordinates')
    return points


def _same(a,b):return all(any(math.dist(p[:2],q[:2])<=.05 for q in b) for p in a) and len(a)==len(b)


def qualify(doc,graph,selection,normalization):
    root=doc.entitydb.get(selection['root_handle'])
    if root is None or root not in doc.modelspace() or root.dxftype()!='INSERT':raise ValueError('display-leg root is not a native modelspace INSERT')
    children={}
    for entity in root.virtual_entities():
        original=entity.source_of_copy
        if original is not None:children.setdefault(original.dxf.handle,[]).append(entity)
    def child(key,kind):
        rows=children.get(selection[key],[])
        if len(rows)!=1 or rows[0].dxftype()!=kind:raise ValueError('display-leg source child missing or ambiguous')
        return rows[0]
    valve=child('valve_handle','INSERT');free=child('free_line_handle','LINE');attached=child('attached_line_handle','LINE')
    if valve.dxf.name not in normalization['known_valves'] or valve.dxf.name!=selection['expected_valve_name']:raise ValueError('unsupported turn display valve symbol')
    if free.dxf.layer not in LAYERS.values() or attached.dxf.layer!=free.dxf.layer:raise ValueError('display legs have different or unknown systems')
    system={v:k for k,v in LAYERS.items()}[free.dxf.layer];fp=_points(free);ap=_points(attached)
    if (max(p[2] for p in fp+ap)-min(p[2] for p in fp+ap)>.05
        or any(math.dist(*points)>normalization['maximum_length'] for points in (fp,ap))):raise ValueError('display-leg Z or inherited length bound differs')
    bounds=bbox.extents([valve],fast=True)
    if not bounds.has_data:raise ValueError('turn valve has no native bounds')
    def inside(point):return all(bounds.extmin[i]-.05<=point[i]<=bounds.extmax[i]+.05 for i in range(3))
    def ends(points):
        yes=[p for p in points if inside(p)];no=[p for p in points if not inside(p)]
        if len(yes)!=1 or len(no)!=1:raise ValueError('each display leg must have exactly one valve-side endpoint')
        return yes[0],no[0]
    fport,ftail=ends(fp);aport,junction=ends(ap)
    axis=[junction[i]-aport[i] for i in range(3)];length=math.sqrt(sum(x*x for x in axis));axis=[v/length for v in axis]
    def coordinate(point):return sum((point[i]-aport[i])*axis[i] for i in range(3))
    for point in fp:
        t=coordinate(point);projected=[aport[i]+t*axis[i] for i in range(3)]
        if math.dist(point,projected)>.05:raise ValueError('free leg does not share the removed display stem axis')
    if not coordinate(ftail)<coordinate(fport)<-.05:raise ValueError('free leg is not on the opposite side of the same valve')
    removals=[r for r in normalization['removals'] if r.system==system and r.block_name==valve.dxf.name
        and math.dist(aport[:2],r.valve_port)<=.05 and math.dist(junction[:2],r.junction)<=.05]
    if len(removals)!=1:raise ValueError('attached sibling was not uniquely removed by the inherited turn-display rule')
    candidates=[s for s in normalization['segments'] if s.system==system and _same([list(s.start),list(s.end)],fp)]
    if len(candidates)!=1:raise ValueError('free leg lacks one inherited native segment')
    for segment in normalization['segments']:
        if segment is candidates[0] or segment.system!=system:continue
        if _on(ftail[:2],segment.start,segment.end,.05):raise ValueError('opposite valve leg reaches a real source pipe')
    corners=[];active=[]
    for edge in graph['edges']:
        if edge.get('system')!=system:continue
        for pi,path in enumerate(edge.get('attribute_paths',[])):
            for a,b in zip(path,path[1:]):
                # A selected normalized display leg must not be an active local
                # graph pipe, including a partially retained collinear span.
                vector=[b[i]-a[i] for i in (0,1)];cross=vector[0]*axis[1]-vector[1]*axis[0]
                if abs(cross)<=.05 and (_on(fp[0][:2],a,b,.05) or _on(fp[1][:2],a,b,.05) or _on(a,fp[0][:2],fp[1][:2],.05) or _on(b,fp[0][:2],fp[1][:2],.05)):
                    active.append(dict(edge_id=edge['edge_id'],path_index=pi))
            if edge.get('source_insert_handle')!=root.dxf.handle:continue
            evidence=edge.get('source_native_block_branch',{})
            if evidence.get('source_insert_handle')!=root.dxf.handle or evidence.get('endpoint_snapshot',{}).get('attribute_paths')!=edge.get('attribute_paths'):
                raise ValueError('owning graph path lacks its retained native block evidence')
            for index in range(1,len(path)-1):
                if math.dist(path[index],junction[:2])>.05:continue
                before,after=path[index-1],path[index+1];u=[before[i]-path[index][i] for i in (0,1)];v=[after[i]-path[index][i] for i in (0,1)]
                if abs(u[0]*v[1]-u[1]*v[0])<=.05:raise ValueError('surviving display junction is not a bend')
                for p in (before,after):
                    matches=[line for rows in children.values() for line in rows if line.dxftype()=='LINE' and line.dxf.layer==free.dxf.layer
                        and _on(path[index],list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05) and _on(p,list(line.dxf.start)[:2],list(line.dxf.end)[:2],.05)]
                    if len(matches)!=1:raise ValueError('surviving graph bend lacks unique native block rays')
                corners.append(dict(edge_id=edge['edge_id'],path_index=pi,vertex_index=index))
    if active:raise ValueError('opposite display leg remains an active graph pipe')
    if len(corners)!=1:raise ValueError('removed display sibling lacks one surviving current graph corner')
    return dict(root_handle=root.dxf.handle,source_chain=[root.dxf.handle,selection['free_line_handle']],source_layer=free.dxf.layer,
        native_XYZ=fp,system=system,valve_chain=[root.dxf.handle,selection['valve_handle']],valve_name=valve.dxf.name,
        valve_bounds=[list(bounds.extmin),list(bounds.extmax)],removed_sibling_chain=[root.dxf.handle,selection['attached_line_handle']],
        removed_sibling=dataclasses.asdict(removals[0]),current_graph_corner=corners[0],
        role='dangling_opposite_stem_of_inherited_normalized_turn_display_valve',excluded_only_from_DN_pipe_competition=True,
        graph_mutated=False,physical_length_mm=None,human_accepted=False)


def collect(doc,graph,policy,source_hash,graph_hash):
    if policy.get('source_sha256')!=source_hash or policy.get('graph_sha256')!=graph_hash or graph.get('metadata',{}).get('source_sha256')!=source_hash:raise ValueError('display-stub source/graph binding differs')
    specs=policy.get('selections',[])
    if not specs or len({(s['root_handle'],s['free_line_handle']) for s in specs})!=len(specs):raise ValueError('empty or duplicate display-stub source scope')
    normalization=replay_normalization(doc,policy['system_layers']);records=[qualify(doc,graph,s,normalization) for s in specs]
    return dict(status='native_turn_display_opposite_stem_replayed_for_annotation_competition',source_sha256=source_hash,graph_sha256=graph_hash,records=records,
        inherited_turn_display_removals=len(normalization['removals']),inherited_overshoot_trims=len(normalization['overshoots']),
        source_or_graph_mutated=False,DN_values_assigned=0,physical_values_fused=False,human_accepted=False)


def implementation_hashes():
    names=['native_valve_display_stub_evidence.py','native_line_path_evidence.py','source_readability.py','legacy_v17/analyze_graph.py']
    return {n:sha(Path(__file__).parent/n) for n in names}


def main():
    parser=argparse.ArgumentParser()
    for key in ('source','graph','policy','output'):parser.add_argument('--'+key,type=Path,required=True)
    a=parser.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    doc,preflight=read_source(a.source);result=collect(doc,load(a.graph),load(a.policy),sha(a.source),sha(a.graph))
    result.update(source_preflight=preflight,policy_sha256=sha(a.policy),implementation_sha256=implementation_hashes());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(encode(result))
    print(dict(excluded_source_stems=len(result['records']),DN_values_assigned=0,graph_mutated=False),flush=True)


if __name__=='__main__':main()
