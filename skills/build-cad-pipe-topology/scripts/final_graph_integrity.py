"""Structural check of a specific final graph, not source or engineering acceptance."""
import csv, hashlib, json, math
from collections import Counter
from pathlib import Path


def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(graph_path, components_path, source_path):
 graph_path,components_path,source_path=map(Path,(graph_path,components_path,source_path))
 graph=json.loads(graph_path.read_text(encoding="utf-8"))
 with components_path.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
 nodes=graph["nodes"];edges=graph["edges"]
 ids=[n["node_id"] for n in nodes];eids=[e["edge_id"] for e in edges]; known=set(ids); edge_set=set(eids)
 names=[r.get("device_name","") for r in rows]
 anchors=[a["boundary_id"] for a in graph.get("boundary_anchors",[])]; known_anchors=set(anchors)
 def valid_end(edge, side):
  n=edge.get(side+"_node_id");b=edge.get(side+"_boundary_id")
  return (n in known and b is None) or (n is None and b in known_anchors)
 invalid_edges=[e["edge_id"] for e in edges if not valid_end(e,"start") or not valid_end(e,"end")]
 invalid_devices=[r.get("device_name","") for r in rows if r.get("edge_id") not in edge_set]
 bad_geometry=[]
 for e in edges:
  paths=e.get("attribute_paths") or ([e["path"]] if e.get("path") else [])
  try: valid=bool(paths) and all(len(path)>=2 and all(len(p)>=2 and all(math.isfinite(float(v)) for v in p[:2]) for p in path) for path in paths)
  except (TypeError,ValueError): valid=False
  if not valid: bad_geometry.append(e["edge_id"])
 checks={"unique_node_ids":len(ids)==len(known),"unique_edge_ids":len(eids)==len(edge_set),"unique_boundary_ids":len(anchors)==len(known_anchors),"edge_endpoints_exist":not invalid_edges,"finite_edge_paths":not bad_geometry,"unique_nonempty_component_names":all(names) and len(names)==len(set(names)),"assigned_component_edges_exist":not invalid_devices}
 return {"status":"structural_checks_passed_not_source_or_human_acceptance" if all(checks.values()) else "structural_checks_failed", "scope":"final_graph_only", "source_sha256":sha(source_path),"graph_sha256":sha(graph_path),"components_sha256":sha(components_path),"graph_path":str(graph_path),"components_path":str(components_path),"counts":{"nodes":len(nodes),"edges":len(edges),"boundary_anchors":len(anchors),"node_types":dict(Counter(n.get("node_type","unknown") for n in nodes)),"assigned_component_rows":len(rows)},"checks":checks,"failures":{"invalid_endpoint_edges":invalid_edges,"invalid_path_edges":bad_geometry,"components_with_missing_edge":invalid_devices},"source_coverage_recomputed":False,"component_conservation_proven":False,"human_acceptance":False,"hil_ready":False}
