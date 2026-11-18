"""Inventory source circle-ended device lines omitted from selected graph paths.

Results are source geometry candidates, not hydraulic connections or ports.
"""
import argparse, hashlib, json, math
from pathlib import Path
from ezdxf.disassemble import recursive_decompose
from native_line_path_evidence import _on, LAYERS
from source_readability import read_source


def collect(doc, graph, policy, source_hash, graph_hash, tol=.05):
 if policy.get('source_sha256') != source_hash or policy.get('graph_sha256') != graph_hash:
  raise ValueError('source or graph hash mismatch')
 if not math.isfinite(tol) or tol <= 0:
  raise ValueError('invalid tolerance')
 edges = {e['edge_id']: e for e in graph['edges']}
 selected = policy.get('edges', [])
 if len(edges) != len(graph['edges']) or not selected or len(selected) != len(set(selected)):
  raise ValueError('invalid edge selections')
 output = []
 for eid in selected:
  edge = edges.get(eid)
  if not edge or edge.get('system') not in LAYERS or not edge.get('attribute_paths'):
   raise ValueError('unsupported edge')
  root_handle = edge.get('source_insert_handle')
  root = doc.entitydb.get(root_handle) if root_handle else None
  if root is None or root.dxftype() != 'INSERT' or root not in doc.modelspace():
   raise ValueError('invalid source instance')
  # A leaf handle alone is not an instance identity.  Restrict this first
  # version to direct children, for which [modelspace INSERT, child] is exact.
  owner = doc.blocks[root.dxf.name].block_record_handle
  entities = []
  for entity in recursive_decompose([root]):
   source = getattr(entity, 'source_of_copy', None)
   if source is not None and source.dxf.owner == owner and entity.dxftype() in ('LINE', 'CIRCLE'):
    entities.append((entity, source.dxf.handle))
  circles = [(e, h) for e, h in entities if e.dxftype() == 'CIRCLE']
  lines = [(e, h) for e, h in entities if e.dxftype() == 'LINE' and e.dxf.layer == LAYERS[edge['system']]]
  paths = edge['attribute_paths']
  if any(not isinstance(path, list) or len(path) < 2 or any(len(p) != 2 or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in p) for p in path) for path in paths):
   raise ValueError('invalid path')
  candidates = []
  for line, lh in lines:
   ends = [[line.dxf.start.x, line.dxf.start.y], [line.dxf.end.x, line.dxf.end.y]]
   if math.dist(*ends) <= tol:
    continue
   matches = []
   for circle, ch in circles:
    # CIRCLE centers use OCS; mirrored inserts can flip the extrusion and
    # hence the OCS X coordinate even though LINE endpoints are already WCS.
    center_wcs = circle.ocs().to_wcs(circle.dxf.center)
    centre = [center_wcs.x, center_wcs.y]
    for i in range(2):
     if math.dist(ends[i], centre) <= tol:
      line_z = (line.dxf.start.z, line.dxf.end.z)[i]
      matches.append({'source_chain': [root_handle, ch], 'center': centre, 'center_z': center_wcs.z, 'line_endpoint_z': line_z, 'z_coincident': abs(line_z-center_wcs.z) <= tol, 'radius': circle.dxf.radius, 'layer': circle.dxf.layer, 'line_endpoint_index': i})
   if not matches:
    continue
   covered = any(_on(ends[0], a, b, tol) and _on(ends[1], a, b, tol) for path in paths for a, b in zip(path, path[1:]))
   candidates.append({'source_chain': [root_handle, lh], 'layer': line.dxf.layer, 'start': ends[0], 'end': ends[1], 'circles': matches, 'fully_covered_by_single_graph_segment': covered})
  output.append({'edge_id': eid, 'system': edge['system'], 'device_label': edge.get('device_label'), 'source_insert_handle': root_handle, 'candidates': candidates})
 return {'status': 'source_geometry_candidates_only', 'source_sha256': source_hash, 'graph_sha256': graph_hash, 'edges': output, 'graph_mutated': False, 'hil_ready': False, 'limitations': ['Only direct LINE and CIRCLE children of the selected modelspace INSERT are inventoried; nested descendants and other shapes are excluded.', 'Matching uses XY; Z differences are recorded and are not resolved.', 'Coincident circle centre and same-system line do not prove port identity, component continuity, inter-view mapping or physical length.', 'Coverage only checks whether one graph segment contains the whole source line; partial and multi-segment coverage are not classified.', 'Multiple circle and line candidates are retained; no nearest-candidate choice is made.']}


def main():
 p = argparse.ArgumentParser()
 for key in ('source', 'graph', 'policy', 'output'):
  p.add_argument('--' + key, type=Path, required=True)
 a = p.parse_args()
 doc, proof = read_source(a.source)
 gb = a.graph.read_bytes(); pb = a.policy.read_bytes(); sha = lambda b: hashlib.sha256(b).hexdigest()
 result = collect(doc, json.loads(gb), json.loads(pb), proof['source_sha256'], sha(gb))
 result.update(policy_sha256=sha(pb), script_sha256=sha(Path(__file__).read_bytes()), source_preflight=proof)
 with a.output.open('x', encoding='utf8', newline='\n') as f:
  json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')
 print(json.dumps({'edges': len(result['edges']), 'candidates': sum(len(e['candidates']) for e in result['edges'])}))


if __name__ == '__main__':
 main()
