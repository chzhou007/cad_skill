"""Validate an existing component-instance table against a specific graph.

The binding proves identity and graph ownership consistency, not source coverage,
engineering subtype, physical valve ownership or expert acceptance.
"""
from collections import Counter

def validate(graph,rows,policy,*,graph_sha256,components_sha256,source_sha256):
 if (not graph_sha256 or not components_sha256 or not source_sha256 or
     graph.get('metadata',{}).get('source_sha256')!=source_sha256 or
     policy.get('source_sha256')!=source_sha256 or policy.get('graph_sha256')!=graph_sha256 or
     policy.get('components_sha256')!=components_sha256):raise ValueError('Graph, components or source hash mismatch')
 edges=graph.get('edges',[]);byid={e['edge_id']:e for e in edges}
 if len(byid)!=len(edges):raise ValueError('Duplicate graph edge IDs')
 actual=[];names=[]
 for row in rows:
  eid=row.get('edge_id');typ=row.get('equipment_type');name=row.get('device_name')
  if not eid or eid not in byid or not typ or not name or row.get('assignment_status')!='assigned':
   raise ValueError('Unassigned or invalid component instance')
  actual.append((eid,typ,name));names.append(name)
 if len(names)!=len(set(names)):raise ValueError('Duplicate component identity')
 expected=[]
 for edge in edges:
  for group in edge.get('equipment_inventory',[]):
   typ=group.get('equipment_type');ids=group.get('device_names')
   if not typ or not isinstance(ids,list) or group.get('count')!=len(ids) or any(not x for x in ids):
    raise ValueError('Invalid graph component aggregation')
   expected.extend((edge['edge_id'],typ,n) for n in ids)
 if Counter(actual)!=Counter(expected):raise ValueError('Component instances differ from graph inventory')
 return {'status':'component_identity_and_edge_binding_verified','source_sha256':source_sha256,
         'graph_sha256':graph_sha256,'components_sha256':components_sha256,
         'component_instances':len(actual),'edges_with_components':len({x[0] for x in actual}),
         'source_coverage_verified':False,'valve_ownership_verified':False,'human_review':'unreviewed',
         'scope':'Exact instance name, type and edge match; physical meaning and source completeness remain separate.'}
