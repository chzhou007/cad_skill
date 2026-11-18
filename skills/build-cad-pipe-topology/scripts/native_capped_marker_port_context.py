"""Read explicit capped declarations on complete, separate marker ports.

Reuse native caption chains and existing source-port coverage. This sidecar
adds no topology, whole-edge DN, length or human acceptance.
"""
import argparse,math,copy,importlib
from pathlib import Path
from confirm_crossview_paths import load,sha,encode
from source_readability import read_source
from discover_native_capped_annotations import CAPTION,qualifier_matches
from native_named_riser_evidence import underlines,xyz,LAYERS
from native_external_pipe_destination import chain,on_segment
from native_path_coverage_audit import audit as coverage_audit

MODE='native_capped_common_marker_ports_v1'

def discover(doc,graph,source_hash,graph_hash):
    if graph['metadata']['source_sha256']!=source_hash:raise ValueError('source identity differs')
    if len({n['node_id']for n in graph['nodes']})!=len(graph['nodes'])or len({e['edge_id']for e in graph['edges']})!=len(graph['edges']):raise ValueError('duplicate canonical graph identities')
    all_ports=[p['port_id']for n in graph['nodes']for p in n.get('ports',[])]
    if len(set(all_ports))!=len(all_ports):raise ValueError('duplicate canonical port identity')
    captions=[t for t in doc.modelspace().query('TEXT')if CAPTION.fullmatch(t.plain_text().strip())]
    qualifiers=[t for t in doc.modelspace().query('TEXT')if t.plain_text().strip()=='盲板封堵'];records=[];pending=[]
    for caption in captions:
        try:
            qs=[q for q in qualifiers if qualifier_matches(caption,q)]
            if len(qs)!=1:raise ValueError('qualifier missing or competing')
            layers={caption.dxf.layer};us=underlines(doc,caption,layers)
            if len(us)!=1:raise ValueError('underline missing or competing')
            joins=[]
            for line in doc.modelspace().query('LINE'):
                if line is us[0]or line.dxf.layer not in layers:continue
                if any(math.dist(a,b)<=.05 for a in xyz(us[0])for b in xyz(line)):joins.append(line)
            if len(joins)!=1:raise ValueError('common marker caption needs one direct leader')
            spec=dict(text_handle=caption.dxf.handle,expected_text=caption.plain_text(),underline_handle=us[0].dxf.handle,leader_handle=joins[0].dxf.handle)
            caption_proof=chain(doc,spec,layers,layers);tip=caption_proof['target_point'];markers=[]
            for node in graph['nodes']:
                if node.get('node_type')!='virtual_equipment'or node.get('subtype')!='external_system_interface':continue
                marker=doc.entitydb.get(node.get('source_marker_handle'))
                if marker is None or marker not in doc.modelspace()or marker.dxftype()!='LWPOLYLINE'or marker.dxf.layer!='DIM_SYMB':continue
                if marker.closed or marker.has_arc or marker.has_width or tuple(marker.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):continue
                vs=[[float(x),float(y),float(marker.dxf.elevation)]for x,y in marker.get_points('xy')]
                if len(vs)>=3 and any(on_segment(tip,a,b)for a,b in zip(vs,vs[1:])):markers.append((node,marker,vs))
            if len(markers)!=1:raise ValueError('caption marker missing or competing in current graph')
            node,marker,vertices=markers[0];ports=node.get('ports',[])
            if not ports or len({p['port_id']for p in ports})!=len(ports):raise ValueError('complete separate marker ports required')
            members=[];claimed=set();edge_ids=set()
            for port in ports:
                if port.get('node_id',node['node_id'])!=node['node_id']or port.get('source_marker_handle')!=marker.dxf.handle:raise ValueError('port marker or node reference differs')
                incident=[(e,side)for e in graph['edges']for side in ('start','end')if e.get(side+'_node_id')==node['node_id']and e.get(side+'_port_id')==port['port_id']]
                if len(incident)!=1:raise ValueError('marker port has missing or competing edge owner')
                edge,side=incident[0]
                if edge['system']!=port['system']or edge.get('source_insert_handle')!=marker.dxf.handle or edge['edge_id']in edge_ids:raise ValueError('separate port source or service mismatch')
                edge_ids.add(edge['edge_id']);policy=dict(source_sha256=source_hash,graph_sha256=graph_hash,edges=[edge['edge_id']])
                native=coverage_audit(doc,graph,policy,source_hash,graph_hash);segments=native['edges'][0]['segments']
                index=1 if side=='start'else len(segments)-2
                if index<0 or index>=len(segments):raise ValueError('no adjacent physical source segment after marker display span')
                piece=segments[index]
                if piece['status']!='single_source_line_covers'or len(piece['witnesses'])!=1 or piece['witnesses'][0]['scope']!='modelspace':raise ValueError('marker adjacent source LINE not unique')
                line=doc.entitydb.get(piece['witnesses'][0]['source_handle']);ends=xyz(line)
                matches=[p for p in ends if math.dist(p[:2],[port['x'],port['y']])<=.05 and any(on_segment(p,a,b)for a,b in zip(vertices,vertices[1:]))]
                if len(matches)!=1 or line.dxf.layer!=LAYERS[port['system']]or line.dxf.handle in claimed:raise ValueError('native endpoint does not uniquely bind its separate marker port')
                claimed.add(line.dxf.handle)
                members.append(dict(node_id=node['node_id'],port_id=port['port_id'],edge_id=edge['edge_id'],system=port['system'],floor=node.get('floor'),source_line_handle=line.dxf.handle,
                    native_pipe_endpoint=matches[0],native_pipe_XYZ=ends,adjacent_source_piece=piece,physical_port_verified=False,physical_length_mm=None,human_accepted=False))
            incident_ids={e['edge_id']for e in graph['edges']if node['node_id']in(e.get('start_node_id'),e.get('end_node_id'))}
            if incident_ids!=edge_ids:raise ValueError('marker membership incomplete')
            contacts={line.dxf.handle for line in doc.modelspace().query('LINE')if line.dxf.layer in LAYERS.values()and any(on_segment(p,a,b)for p in xyz(line)for a,b in zip(vertices,vertices[1:]))}
            if contacts!=claimed:raise ValueError('marker has extra or missing native pipe endpoint contacts')
            records.append(dict(caption_evidence=caption_proof,qualifier_handle=qs[0].dxf.handle,qualifier_text=qs[0].plain_text(),
                marker_handle=marker.dxf.handle,marker_vertices=vertices,members=members,declared_quantity=int(CAPTION.fullmatch(caption.plain_text().strip())[1]),
                quantity_expanded_into_ports=False,common_marker_creates_pipe_connection=False,graph_mutated=False,human_accepted=False))
        except(ValueError,KeyError,TypeError)as exc:pending.append(dict(caption_handle=caption.dxf.handle,reason=str(exc)))
    by_marker={}
    for record in records:by_marker.setdefault(record['marker_handle'],[]).append(record)
    repeated={r['caption_evidence']['text_handle']for group in by_marker.values()if len(group)>1 for r in group}
    if repeated:
        pending.extend(dict(caption_handle=h,reason='multiple_native_captions_claim_one_marker_scope')for h in sorted(repeated))
        records=[r for r in records if r['caption_evidence']['text_handle']not in repeated]
    return dict(records=records,pending=pending,graph_mutated=False,mappings_created=0,physical_values_assigned=0,human_accepted=False)

def implementation_hashes():
    names=('discover_native_capped_annotations','native_capped_branch_annotations','native_named_riser_evidence','native_external_pipe_destination','native_path_coverage_audit','native_line_path_evidence','source_readability')
    return dict({n:sha(importlib.import_module(n).__file__)for n in names},entry=sha(__file__))

def compute(paths):
    hashes={k:sha(v)for k,v in paths.items()};doc,preflight=read_source(paths['source']);graph=load(paths['graph']);before=copy.deepcopy(graph)
    result=discover(doc,graph,hashes['source'],hashes['graph'])
    if graph!=before or any(sha(v)!=hashes[k]for k,v in paths.items()):raise ValueError('capped marker context changed current inputs')
    result.update(mode=MODE,source_sha256=hashes['source'],graph_sha256=hashes['graph'],source_preflight=preflight,
        quantity_scope='native caption quantity is retained; only directly targeted marker ports are enumerated',hil_ready=False)
    return result

def verify_output(directory):
    directory=Path(directory);receipt=load(directory/'capped-marker-context-receipt.json')
    if receipt['mode']!=MODE or receipt['implementation_sha256']!=implementation_hashes():raise ValueError('capped marker context implementation changed')
    paths={k:Path(v['path'])for k,v in receipt['inputs'].items()}
    if set(paths)!={'source','graph'}or any(sha(paths[k])!=v['sha256']for k,v in receipt['inputs'].items()):raise ValueError('capped marker context inputs changed')
    target=directory/'capped-marker-context.json'
    if sha(target)!=receipt['output_sha256']:raise ValueError('capped marker context recorded bytes changed')
    result=compute(paths)
    if encode(result)!=target.read_bytes():raise ValueError('capped marker context native independent replay differs')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('source','graph','output','verify_output'):parser.add_argument('--'+key.replace('_','-'),type=Path)
    args=parser.parse_args()
    if args.verify_output:
        if any((args.source,args.graph,args.output)):parser.error('verification cannot override pinned inputs')
        result=verify_output(args.verify_output);print(dict(marker_groups=len(result['records']),separate_ports=sum(len(r['members'])for r in result['records']),pending=result['pending']));return
    if not all((args.source,args.graph,args.output)):parser.error('source, current graph and new output required')
    if args.output.exists():raise FileExistsError(args.output)
    paths=dict(source=args.source.resolve(),graph=args.graph.resolve());result=compute(paths);args.output.mkdir(parents=True)
    target=args.output/'capped-marker-context.json';target.write_bytes(encode(result))
    (args.output/'capped-marker-context-receipt.json').write_bytes(encode(dict(mode=MODE,inputs={k:dict(path=str(p),sha256=sha(p))for k,p in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target),human_accepted=False)))
    print(dict(marker_groups=len(result['records']),separate_ports=sum(len(r['members'])for r in result['records']),pending=result['pending']),flush=True)

if __name__=='__main__':main()
