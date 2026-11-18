import copy,unittest
from build_visualization import require_same_plan_topology

class PlanLineViewerTopologyTest(unittest.TestCase):
 def test_display_fields_are_allowed_but_topology_and_source_paths_are_not_changed(self):
  graph={'nodes':[{'node_id':'T','node_type':'tee','x':1,'y':2,'system':'supply'},{'node_id':'E','node_type':'equipment','x':3,'y':4}],'edges':[{'edge_id':'A','start_node_id':'T','end_node_id':'E','system':'supply','source_handles':['H'],'attribute_paths':[[[1,2],[3,4]]]}]}
  display=copy.deepcopy(graph);display['nodes'][0]['symbol_key']='visual';display['edges'][0]['equipment_inventory']=[];require_same_plan_topology(graph,display)
  for mutate in (lambda d:d['edges'][0]['attribute_paths'][0][0].__setitem__(0,9),lambda d:d['edges'][0].__setitem__('end_node_id','T'),lambda d:d['nodes'][0].__setitem__('x',9),lambda d:d['edges'].append(copy.deepcopy(d['edges'][0]))):
   changed=copy.deepcopy(display);mutate(changed)
   with self.assertRaisesRegex(ValueError,'differs from canonical topology'):require_same_plan_topology(graph,changed)
if __name__=='__main__':unittest.main()
