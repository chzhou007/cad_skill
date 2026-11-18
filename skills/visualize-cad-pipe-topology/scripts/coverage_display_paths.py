"""Partition scoped source-witnessed and unwitnessed graph segments for display."""
import math

def _partition_base(edge):
    paths=edge['attribute_paths'];coverage=edge.get('source_path_coverage')
    wave=edge.get('source_wave_omission')
    erratum=edge.get('source_drafting_erratum')
    if erratum is not None:
        if (coverage is not None or edge.get('path_length_complete') is not False
            or edge.get('physical_length')!='unknown' or erratum.get('physical_length')!='unknown'
            or erratum.get('rule_scope')!='explicit_project_known_issue_only'
            or not all(isinstance(erratum.get(k),str) and erratum[k] for k in ('project_scope','issue_id','issue_sha256','source_sha256'))):
            raise ValueError('invalid explicit drawing erratum evidence')
        ends=erratum.get('source_endpoints')
        if (not isinstance(ends,list) or len(ends)!=2 or any(not isinstance(p,list) or len(p)!=2
            or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in ends)
            or math.dist(*ends)<=.05):raise ValueError('invalid drawing erratum endpoints')
        hits=[[i for i,path in enumerate(paths) if min(math.dist(p,path[0]),math.dist(p,path[-1]))<=.05] for p in ends]
        if any(len(x)!=1 for x in hits) or hits[0]==hits[1]:raise ValueError('drawing erratum endpoints not on distinct native paths')
        length=sum(math.dist(a,b) for path in paths for a,b in zip(path,path[1:]))
        if not isinstance(edge.get('path_length'),(int,float)) or abs(length-edge['path_length'])>.001:
            raise ValueError('drawing erratum drawing length mismatch')
        return paths,[ends]
    if edge.get('path_length_scope')=='drawing_paths_excluding_source_crossover_gaps_physical_length_unknown' or edge.get('source_normalized_crossovers'):
        gaps=edge.get('source_normalized_crossovers')
        if coverage is not None or edge.get('path_length_complete') is not False or edge.get('physical_length')!='unknown' or not isinstance(gaps,list) or not gaps:raise ValueError('invalid crossover length evidence')
        missing=[]
        for gap in gaps:
            ends=[gap.get('a'),gap.get('b')]
            if (gap.get('crossing_connectivity')!='independent_pipes_no_junction' or gap.get('physical_length')!='unknown' or
                any(not isinstance(p,(list,tuple)) or len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in ends) or math.dist(*ends)<=.05):raise ValueError('invalid crossover endpoints')
            hits=[[i for i,path in enumerate(paths) if min(math.dist(p,path[0]),math.dist(p,path[-1]))<=.05] for p in ends]
            if any(len(x)!=1 for x in hits) or hits[0]==hits[1]:raise ValueError('crossover endpoints are not uniquely attached to separate paths')
            missing.append(ends)
        length=sum(math.dist(a,b) for path in paths for a,b in zip(path,path[1:]))
        if not isinstance(edge.get('path_length'),(int,float)) or isinstance(edge['path_length'],bool) or not math.isfinite(edge['path_length']) or abs(length-edge['path_length'])>.001:raise ValueError('crossover drawing length mismatch')
        return paths,missing
    if edge.get('connection_mode')=='source_calibrated_wave_omission_unreviewed':
        if coverage is not None or not isinstance(wave,dict) or edge.get('path_length_complete') is not False or wave.get('physical_length')!='unknown':raise ValueError('invalid wave omission evidence')
        ends=wave.get('source_endpoints');handles=wave.get('wave_handles')
        if not isinstance(ends,list) or len(ends)!=2 or any(not isinstance(p,(list,tuple)) or len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in ends):raise ValueError('invalid wave omission endpoints')
        if not isinstance(handles,list) or len(handles)!=2 or len(set(handles))!=2 or not all(isinstance(h,str) and h for h in handles):raise ValueError('invalid wave source handles')
        if math.dist(*ends)<=.05 or len(paths)<2:raise ValueError('invalid wave omission span')
        hits=[[i for i,path in enumerate(paths) if min(math.dist(p,path[0]),math.dist(p,path[-1]))<=.05] for p in ends]
        if any(len(x)!=1 for x in hits) or hits[0]==hits[1]:raise ValueError('wave endpoint is not uniquely attached to two source paths')
        return paths,[ends]
    if coverage is None:return paths,[]
    if edge.get('path_length_complete') is not False or len(paths)!=1:raise ValueError('partial coverage requires one incomplete source path')
    path=paths[0];indices=coverage.get('unverified_segment_indices')
    if not isinstance(indices,list) or not indices or any(isinstance(i,bool) or not isinstance(i,int) or i<0 or i>=len(path)-1 for i in indices) or len(indices)!=len(set(indices)):
        raise ValueError('invalid unverified segment indices')
    if not all(isinstance(coverage.get(k),str) and coverage[k] for k in ('source_sha256','coverage_sha256','input_graph_sha256')):raise ValueError('partial coverage lacks source identity')
    actual=sum(math.dist(path[i],path[i+1]) for i in indices)
    length=coverage.get('unverified_drawing_length')
    if isinstance(length,bool) or not isinstance(length,(int,float)) or not math.isfinite(length) or abs(actual-length)>.001:raise ValueError('partial coverage length mismatch')
    uncertain=set(indices);groups=[[],[]]
    for i,(a,b) in enumerate(zip(path,path[1:])):
        slot=int(i in uncertain)
        if groups[slot] and i>0 and ((i-1 in uncertain)==(i in uncertain)):groups[slot][-1].append(b)
        else:groups[slot].append([a,b])
    if not groups[0]:raise ValueError('no witnessed source segments')
    return groups[0],groups[1]


def partition(edge,native_doc=None,source_hash=None):
    known,unknown=_partition_base(edge)
    paired=edge.get('source_confirmed_equipment_pair_circle');user=edge.get('source_user_circle_connection')
    if paired is None and user is None:return known,unknown
    if paired is not None and user is not None:raise ValueError('ambiguous circle connector display evidence')
    proof=paired if paired is not None else user
    if native_doc is None or not isinstance(proof,dict) or proof.get('physical_length')!='unknown' or edge.get('path_length_complete') is not False:
        raise ValueError('confirmed circle connector requires native source and unknown physical length')
    if paired is not None:
        if proof.get('source_sha256')!=source_hash or proof.get('confirmation_basis')!='explicit_equipment_pair_reply':raise ValueError('stale paired circle source')
        center=proof.get('source_circle_center');anchor=proof.get('point');system=proof.get('system');limit=proof.get('maximum_circle_main_offset_drawing_units')
    else:
        confirmation=proof.get('confirmation',{})
        if confirmation.get('confirmed_by')!='user' or not confirmation.get('question') or not confirmation.get('answer'):raise ValueError('missing explicit circle confirmation')
        center=proof.get('center');anchor=center;system=proof.get('line_system');limit=.05
    rim=proof.get('source_rim')
    if any(not isinstance(p,(list,tuple)) or len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in p) for p in (center,anchor,rim)):
        raise ValueError('invalid circle connector coordinates')
    if system!=edge['system'] or system not in ('supply','return'):raise ValueError('circle connector system differs')
    circle=native_doc.entitydb.get(proof.get('circle_handle',''))
    if (not circle or not circle.is_alive or circle.dxftype()!='CIRCLE' or circle not in native_doc.modelspace()
        or tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.)
        or math.dist(center,[circle.dxf.center.x,circle.dxf.center.y])>.05 or abs(math.dist(center,rim)-circle.dxf.radius)>.05):raise ValueError('native circle connector changed')
    if isinstance(limit,bool) or not isinstance(limit,(int,float)) or not math.isfinite(limit) or limit<0 or (paired is not None and limit>circle.dxf.radius*.02) or math.dist(center,anchor)>limit+.00001:
        raise ValueError('circle connector offset outside confirmed scope')
    path=edge.get('path_points') or edge.get('path')
    if not path or min(math.dist(anchor,path[0]),math.dist(anchor,path[-1]))>.05:raise ValueError('confirmed circle anchor is not a current edge endpoint')
    hits=[p for p in edge['attribute_paths'] if min(math.dist(rim,p[0]),math.dist(rim,p[-1]))<=.05]
    if len(hits)!=1:raise ValueError('circle rim is not a unique source path endpoint')
    adjacent=hits[0][1] if math.dist(rim,hits[0][0])<=.05 else hits[0][-2]
    layer='空调冷冻水供水' if system=='supply' else '空调冷冻水回水'
    def on(p,a,b):
        u=[b[i]-a[i] for i in (0,1)];length=math.hypot(*u)
        if length<=.05:return False
        t=sum((p[i]-a[i])*u[i] for i in (0,1))/(length*length)
        q=[a[i]+max(0,min(1,t))*u[i] for i in (0,1)]
        return -.05/length<=t<=1+.05/length and math.dist(p,q)<=.05
    lines=[]
    for h in edge.get('source_handles',[]):
        line=native_doc.entitydb.get(h)
        if not line or not line.is_alive or line.dxftype()!='LINE' or line not in native_doc.modelspace() or line.dxf.layer!=layer:continue
        a,b=([v.x,v.y] for v in (line.dxf.start,line.dxf.end))
        if min(math.dist(rim,a),math.dist(rim,b))<=.05 and on(adjacent,a,b):lines.append(h)
    if len(lines)!=1:raise ValueError('circle branch source line missing or ambiguous')
    if paired is not None:
        main=native_doc.entitydb.get(proof.get('main_handle',''))
        if not main or main.dxftype()!='LINE' or main.dxf.layer!=layer or not on(anchor,[main.dxf.start.x,main.dxf.start.y],[main.dxf.end.x,main.dxf.end.y]):raise ValueError('paired circle main anchor changed')
    native_length=sum(math.dist(a,b) for p in known for a,b in zip(p,p[1:]))
    if abs(native_length-edge['path_length'])>.001:raise ValueError('circle connector was included in native drawing length')
    connector=[rim,list(anchor)]
    if math.dist(*connector)>.05 and not any(len(p)==2 and (all(math.dist(a,b)<=.05 for a,b in zip(p,connector)) or all(math.dist(a,b)<=.05 for a,b in zip(reversed(p),connector))) for p in unknown):
        unknown=unknown+[connector]
    return known,unknown
