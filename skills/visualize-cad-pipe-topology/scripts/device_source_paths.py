"""Recover a graph-linked device-side source LINE from its real INSERT chain."""
import math
LAYERS={'supply':'空调冷冻水供水','return':'空调冷冻水回水'}

def exploded_device_source_paths(doc,edge,source_hash):
 r=edge.get('source_exploded_device_chain')
 if r is None:return []
 if not isinstance(r,dict) or r.get('status')!='native_chain_geometry_unreviewed' or r.get('source_sha256')!=source_hash or r.get('physical_port_verified') is not False or r.get('physical_length')!='unknown' or r.get('additional_line_length_not_added') is not True or edge.get('path_length_complete') is not False or edge.get('physical_length')!='unknown':raise ValueError('invalid exploded device source evidence')
 handles=[r.get(k) for k in ('inner_line_handle','outer_line_handle','joint_handle','circle_handle')]
 if any(not isinstance(h,str) or not h for h in handles) or len(set(handles))!=4:raise ValueError('invalid exploded source handles')
 inner,outer,joint,circle=[doc.entitydb.get(h) for h in handles]
 if not all(e is not None and e in doc.modelspace() for e in (inner,outer,joint,circle)) or inner.dxftype()!='LINE' or outer.dxftype()!='LINE' or joint.dxftype()!='INSERT' or circle.dxftype()!='CIRCLE':raise ValueError('exploded source entity mismatch')
 if inner.dxf.layer!=LAYERS.get(edge.get('system')) or outer.dxf.layer!=LAYERS.get(edge.get('system')):raise ValueError('exploded device source system mismatch')
 if tuple(circle.dxf.get('extrusion',(0,0,1)))!=(0.,0.,1.):raise ValueError('unsupported exploded source circle OCS')
 actual=[list(inner.dxf.start),list(inner.dxf.end)];saved=r.get('inner_line_endpoints')
 if not isinstance(saved,list) or len(saved)!=2 or any(not isinstance(x,list) or len(x)!=3 for x in saved) or any(math.dist(a,b)>1e-5 for a,b in zip(actual,saved)):raise ValueError('exploded source line coordinates changed')
 parts=list(joint.virtual_entities());bars=[x for x in parts if x.dxftype()=='LINE']
 if len(parts)!=6 or len(bars)!=2 or sum(x.dxftype()=='ARC' for x in parts)!=4:raise ValueError('unsupported exploded source joint')
 mids=[(v.dxf.start+v.dxf.end)/2 for v in bars]
 near=lambda a,b:math.dist(tuple(a),tuple(b))<=.05
 matches=[(i,j) for i in range(2) for j in range(2) if i!=j and any(near(mids[i],p) for p in (inner.dxf.start,inner.dxf.end)) and any(near(mids[j],p) for p in (outer.dxf.start,outer.dxf.end))]
 if len(matches)!=1 or not any(near(circle.dxf.center,p) for p in (inner.dxf.start,inner.dxf.end)):raise ValueError('exploded device source contact mismatch')
 return [[[inner.dxf.start.x,inner.dxf.start.y],[inner.dxf.end.x,inner.dxf.end.y]]]

def device_source_paths(doc,edge,source_hash):
 record=edge.get('source_device_extension')
 if record is not None and edge.get('source_exploded_device_chain') is not None:raise ValueError('multiple device source path types')
 if record is None:return exploded_device_source_paths(doc,edge,source_hash)
 if not isinstance(record,dict) or record.get('status')!='source_drawn_line_with_joint_evidence_unreviewed' or record.get('source_sha256')!=source_hash or record.get('changes_topology') is not False or record.get('physical_port_verified') is not False or record.get('physical_length')!='unknown':raise ValueError('invalid device source evidence')
 if edge.get('physical_length')!='unknown' or edge.get('path_length_complete') is not False:raise ValueError('device source path requires incomplete physical length')
 chains=[record.get(k) for k in ('source_line_chain','source_circle_chain','source_joint_chain','source_outer_line_chain')]
 if any(not isinstance(c,list) or len(c)!=2 or not all(isinstance(h,str) and h for h in c) for c in chains):raise ValueError('invalid device source chains')
 if any(c[0]!=edge.get('source_insert_handle') for c in chains):raise ValueError('device source root mismatch')
 root=doc.entitydb.get(chains[0][0])
 if not root or root.dxftype()!='INSERT' or root not in doc.modelspace():raise ValueError('invalid device source root')
 owner=doc.blocks[root.dxf.name].block_record_handle
 for c,kind in zip(chains,('LINE','CIRCLE','INSERT','LINE')):
  entity=doc.entitydb.get(c[1])
  if not entity or entity.dxftype()!=kind or entity.dxf.owner!=owner:raise ValueError('device source child mismatch')
 line=doc.entitydb[chains[0][1]]
 if line.dxf.layer!=LAYERS.get(edge.get('system')):raise ValueError('device source system mismatch')
 found=[x for x in root.virtual_entities() if x.dxftype()=='LINE' and getattr(x,'source_of_copy',None) is not None and x.source_of_copy.dxf.handle==chains[0][1]]
 if len(found)!=1:raise ValueError('device source transform is ambiguous')
 p,q=found[0].dxf.start,found[0].dxf.end
 return [[[p.x,p.y],[q.x,q.y]]]
