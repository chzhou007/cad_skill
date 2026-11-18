"""Find calibrated native joint instances inside scoped unwitnessed graph gaps."""
import argparse,csv,hashlib,json,math
from pathlib import Path
from repair_native_flexible_joints import fingerprint
from source_readability import read_source


def screen(doc, coverage, graph, inventory, policy, hashes):
    for key in ('source_sha256','graph_sha256','coverage_sha256','inventory_sha256'):
        if hashes[key] != policy[key]: raise ValueError('input hash mismatch: '+key)
    if coverage.get('source_sha256') != hashes['source_sha256'] or coverage.get('graph_sha256') != hashes['graph_sha256']:
        raise ValueError('coverage input binding mismatch')
    block=policy['block_name']
    if block not in doc.blocks or fingerprint(doc.blocks[block]) != policy['block_fingerprint_sha256']:
        raise ValueError('expert calibrated fingerprint mismatch')
    edges={e['edge_id']:e for e in graph['edges']}; existing={r.get('source_top_handle') for r in inventory}
    if len(edges)!=len(graph['edges']):raise ValueError('duplicate edges')
    outputs=[];used=set();tol=.05
    for sel in policy['selections']:
        eid=sel['edge_id']; idx=sel['segment_index']; handle=sel['insert_handle']
        if handle in used or handle in existing:raise ValueError('joint already claimed or selected twice')
        used.add(handle);edge=edges[eid]; matches=[e for e in coverage['edges'] if e['edge_id']==eid]
        if len(matches)!=1 or edge['system']!=matches[0]['system']:raise ValueError('edge coverage mismatch')
        segments=matches[0]['segments']; hits=[s for s in segments if s['index']==idx]
        if len(hits)!=1 or hits[0]['status']!='no_witness_in_scoped_search':raise ValueError('gap not unwitnessed')
        gap=hits[0];a=gap['start'];b=gap['end'];length=math.dist(a,b);center=[(a[i]+b[i])/2 for i in (0,1)]
        entity=doc.entitydb.get(handle)
        if entity is None or entity.dxftype()!='INSERT' or entity.dxf.name!=block or entity.dxf.owner!=doc.modelspace().block_record_handle:raise ValueError('invalid source joint')
        pos=entity.ocs().to_wcs(entity.dxf.insert)
        if math.dist(center,(pos.x,pos.y))>tol or abs(pos.z)>tol:raise ValueError('joint not centred on gap')
        glyph=list(entity.virtual_entities());points=[x.dxf.location for x in glyph if x.dxftype()=='POINT'];bars=[x for x in glyph if x.dxftype()=='LINE']
        if sorted(x.dxftype() for x in glyph)!=['LINE','LINE','POINT','POINT','SPLINE'] or len(points)!=2:raise ValueError('joint glyph differs')
        mids=[(x.dxf.start+x.dxf.end)/2 for x in bars]
        if any(sum(math.dist(p,m)<=tol for m in mids)!=1 for p in points):raise ValueError('joint contact marks differ')
        axis=[(b[i]-a[i])/length for i in (0,1)]
        along=sorted(sum((p[i]-a[i])*axis[i] for i in (0,1)) for p in points)
        if any(abs((p.x-a[0])*axis[1]-(p.y-a[1])*axis[0])>tol or abs(p.z)>tol for p in points) or not (0<along[0]<along[1]<length):raise ValueError('joint axis mismatch')
        neighbours=[]
        for endpoint in (a,b):
            hits=[s for s in segments if s['status']=='single_source_line_covers' and any(math.dist(endpoint,p)<=tol for p in (s['start'],s['end']))]
            if len(hits)!=1:raise ValueError('gap requires unique adjacent source-covered segment')
            neighbours.append({'segment_index':hits[0]['index'],'source_witnesses':hits[0]['witnesses']})
        outputs.append({'edge_id':eid,'system':edge['system'],'insert_handle':handle,'candidate_type':'金属软接',
                        'gap_segment_index':idx,'gap_endpoints':[a,b],'gap_drawing_length':length,
                        'joint_marker_drawing_span':along[1]-along[0],
                        'unwitnessed_end_clearances':[along[0],length-along[1]],
                        'adjacent_source_segments':neighbours,'status':'source_calibrated_joint_unassigned_pending_review',
                        'physical_length':'unknown','human_accepted':False})
    return {'status':'missing_source_joints_candidate_screen','records':outputs,'graph_mutated':False,'hil_ready':False,
            'source_sha256':hashes['source_sha256'],'graph_sha256':hashes['graph_sha256'],
            'coverage_sha256':hashes['coverage_sha256'],'inventory_sha256':hashes['inventory_sha256'],
            'limitations':['Fingerprint identifies a calibrated symbol candidate; unresolved end clearances do not establish contacts or installed length.',
                           'Only explicitly selected gaps and instances were screened; no inventory completeness or component ownership is claimed.']}


def bind_final(screen_result, intermediate, final, final_sha256):
    """Bind selected candidate edges to a later graph without inferring ownership."""
    a={e['edge_id']:e for e in intermediate['edges']};b={e['edge_id']:e for e in final['edges']}
    if len(a)!=len(intermediate['edges']) or len(b)!=len(final['edges']):raise ValueError('duplicate graph edges')
    for record in screen_result['records']:
        eid=record['edge_id'];old=a.get(eid);new=b.get(eid)
        if not old or not new or any(old.get(k)!=new.get(k) for k in ('system','start_node_id','end_node_id','attribute_paths','source_handles')):
            raise ValueError('candidate edge changed before final graph')
    return {'status':'missing_joint_candidates_pending_source_comparison','final_graph_sha256':final_sha256,
            'candidate_count':len(screen_result['records']),'candidate_handles':[r['insert_handle'] for r in screen_result['records']],
            'graph_mutated':False,'human_accepted':False,'hil_ready':False}


def main():
    p=argparse.ArgumentParser()
    for key in ('source','graph','coverage','inventory','policy','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();doc,proof=read_source(a.source)
    with a.inventory.open(encoding='utf-8-sig',newline='') as f:inventory=list(csv.DictReader(f))
    hashes={k+'_sha256':sha(getattr(a,k)) for k in ('source','graph','coverage','inventory')}
    result=screen(doc,json.loads(a.coverage.read_text(encoding='utf8')),json.loads(a.graph.read_text(encoding='utf8')),inventory,json.loads(a.policy.read_text(encoding='utf8')),hashes)
    result.update(source_preflight=proof,policy_sha256=sha(a.policy),script_sha256=sha(Path(__file__)))
    with a.output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'candidates':len(result['records']),'graph_mutated':False}))
if __name__=='__main__':main()
