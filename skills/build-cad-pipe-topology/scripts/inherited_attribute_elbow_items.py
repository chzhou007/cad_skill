"""Replay the original elbow-overrun rule in a private native attribute view."""
import ast,copy,math,runpy,types
from pathlib import Path
from confirm_crossview_paths import encode,sha
from axis_unbranched_vertical_DN import native_items,source_Z
from native_line_path_evidence import LAYERS,_on
import topology_normalization as original

def collect(doc,graph,historical_audit):
    cfg=copy.deepcopy(historical_audit['config']['elbow_overshoot']);legacy=Path(__file__).with_name('legacy_v17')/'analyze_graph.py';declarations=[n for n in ast.parse(legacy.read_text(encoding='utf8')).body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='POINT_TOLERANCE'for t in n.targets)]
    if len(declarations)!=1:raise ValueError('original normalization tolerance declaration missing')
    tol=ast.literal_eval(declarations[0].value)
    if cfg['maximum_length']>10 or cfg['maximum_ratio']>.1 or not 0<tol<=.2:raise ValueError('original normalization limits cannot be widened')
    raw=native_items(doc,graph);before=encode(graph),encode(raw);path=Path(original.__file__).with_name('pipe_geometry.py');ns=runpy.run_path(str(path));ns['set_tolerance'](tol);geometry=types.SimpleNamespace(**ns);geometry.TOL=tol
    namespace=dict(original.trim_elbow_overshoots.__globals__,pg=geometry);trim=types.FunctionType(original.trim_elbow_overshoots.__code__,namespace,original.trim_elbow_overshoots.__name__,original.trim_elbow_overshoots.__defaults__,original.trim_elbow_overshoots.__closure__)
    rows=[dict(handle=str(i),source_handles=[str(i)],a=x['XYZ'][0][:2],b=x['XYZ'][1][:2],system=x['layer'])for i,x in enumerate(raw)];projected,audit=trim(rows,cfg);private=copy.deepcopy(raw);proof=[]
    for r in audit:
        if len(r['source_handles'])!=1:raise ValueError('unique original native LINE item required')
        index=int(r['source_handles'][0]);item=raw[index];point=r['semantic_endpoint'];tip=r['original_endpoint'];ends=[i for i,p in enumerate(item['XYZ'])if math.dist(tip,p[:2])<=1e-7]
        history=[h for h in historical_audit['elbow_overshoots']if (item['root_handle']or item['child_handle'])in h['source_handles']and math.dist(tip,h['original_endpoint'])<=1e-7 and math.dist(point,h['semantic_endpoint'])<=1e-7]
        if len(history)!=1:raise ValueError('private attribute trim lacks its original graph-normalization history')
        if len(ends)!=1:raise ValueError('original native overrun endpoint differs')
        z=source_Z(item,point);incident=[x for x in raw if x['layer']==item['layer']and _on(point,x['XYZ'][0][:2],x['XYZ'][1][:2],.05)and abs(source_Z(x,point)-z)<=.05]
        if len(incident)!=2 or not any(x is item for x in incident):raise ValueError('elbow overrun lacks exactly two same-Z original source LINEs')
        pi=ends[0];private[index]['XYZ'][pi]=[point[0],point[1],z]
        if sum(sum(math.dist(point,p[:2])>.05 for p in x['XYZ'])for x in [private[index],next(x for x in incident if x is not item)])!=2:raise ValueError('normalized native elbow is not two-arm')
        proof.append(dict(original_rule=copy.deepcopy(r),source_item=copy.deepcopy(item),private_item=copy.deepcopy(private[index]),native_Z=z,original_tip_has_no_other_attachment=True,physical_length_mm=None))
    if before!=(encode(graph),encode(raw)):raise ValueError('source graph or native items mutated')
    return private,dict(original_kernel_sha256=sha(original.__file__),private_geometry_kernel_sha256=sha(path),original_tolerance_kernel_sha256=sha(legacy),original_limits=cfg,point_tolerance=tol,records=proof,source_graphs_changed=False,physical_lengths_assigned=0)
