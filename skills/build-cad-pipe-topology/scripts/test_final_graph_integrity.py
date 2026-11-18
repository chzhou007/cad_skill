import csv,json,tempfile,unittest
from pathlib import Path
from final_graph_integrity import audit

class FinalGraphIntegrity(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.g={"nodes":[{"node_id":"N1","node_type":"tee"}],"boundary_anchors":[{"boundary_id":"A1"}],"edges":[{"edge_id":"E1","start_node_id":"N1","end_node_id":None,"end_boundary_id":"A1","path":[[0,0],[1,0]]}]}
  self.source=self.root/"source.dxf";self.source.write_bytes(b"source");self.graph=self.root/"graph.json";self.components=self.root/"components.csv"
  self.components.write_text("device_name,edge_id\nD1,E1\n",encoding="utf8")
 def run_audit(self):
  self.graph.write_text(json.dumps(self.g),encoding="utf8");return audit(self.graph,self.components,self.source)
 def test_valid_non_node_boundary_does_not_imply_acceptance(self):
  d=self.run_audit();self.assertTrue(all(d["checks"].values()));self.assertFalse(d["human_acceptance"]);self.assertFalse(d["source_coverage_recomputed"]);self.assertEqual(d["counts"]["boundary_anchors"],1)
 def test_unresolved_boundary_and_duplicate_device_fail(self):
  self.g["boundary_anchors"]=[];self.components.write_text("device_name,edge_id\nD1,E1\nD1,E1\n",encoding="utf8");d=self.run_audit();self.assertFalse(d["checks"]["edge_endpoints_exist"]);self.assertFalse(d["checks"]["unique_nonempty_component_names"])
 def test_node_and_boundary_cannot_both_bind_one_end(self):
  self.g["edges"][0]["end_node_id"]="N1";self.assertFalse(self.run_audit()["checks"]["edge_endpoints_exist"])
 def test_missing_component_edge_and_nonfinite_path_fail(self):
  self.components.write_text("device_name,edge_id\nD1,wrong\n",encoding="utf8");self.g["edges"][0]["path"][1][0]=float("nan");d=self.run_audit();self.assertFalse(d["checks"]["assigned_component_edges_exist"]);self.assertFalse(d["checks"]["finite_edge_paths"])
if __name__=="__main__":unittest.main()
