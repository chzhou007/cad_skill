import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'build-cad-pipe-topology/scripts'))
import test_lower_floor_plan_viewer_evidence as inherited
from adopt_wave_rebased_plan_scopes import ROOT
from build_visualization import verified_source_attribute_ancestor
from wave_plan_scope_viewer_evidence import verify,dependency_paths


def fixture(root):
    target,graph,lower=inherited.Tests().fixture(root);ph=lower['output_graph_sha256'];rows=[]
    for i in range(2):
        eid='NEW'+str(i);item=dict(edge_id=eid,added_attribute=True)
        c=dict(current_plan_scope_evidence=copy.deepcopy(item),mapping_id=eid,mapping_kind='equipment_branch',system='supply',plan_edges=['P'+eid],iso_edges=[eid],
            horizontal_projection=dict(value_mm=500),diameter=dict(status='source_checked_plan_DN_axis_extent_partial',plan_drawn_nominal_mm=150))
        graph['edges'].append(dict(edge_id=eid,cross_view_attributes=c));rows.append(item)
    stage=dict(records=rows,prior_topology_components_and_other_attributes_preserved=True,whole_DN_or_lengths_added=0,related_HIL_confirmation_inherited=False)
    graph[ROOT]=copy.deepcopy(stage);target.write_text(json.dumps(graph),'utf8');gh=hashlib.sha256(target.read_bytes()).hexdigest()
    lower['inputs']=dict(parent_graph=dict(path=str(root/'upper/graph_with_edges.json')));upper=lower['verified_upper_parent'];upper['inputs']=dict(parent_graph=dict(path=str(root/'named/graph_with_edges.json')))
    upper['verified_named_parent']['parent_graph']['path']=str(root/'axis/graph_with_edges.json')
    audit=dict(output_graph_sha256=gh,proof=stage,verified_lower_parent=lower,parent_graph=dict(path=str(root/'lower/graph_with_edges.json'),sha256=ph),human_accepted=False,hil_ready=False,
        mapping_path=str(root/'mapping/mapping.json'),attribute_scope_path=str(root/'attributes/wave-plan-attributes.json'),inputs=dict(comparison=dict(path=str(root/'comparison/DN-comparison.json'))))
    return target,graph,audit


class Tests(unittest.TestCase):
    def test_native_adoption_reuses_only_its_fresh_parent_and_extends_proof_for_new_scopes(self):
        with tempfile.TemporaryDirectory() as temp:
            target,graph,audit=fixture(Path(temp));proof=dict(records=[dict(legacy=True)],plan_DN_scope_fusion=[])
            with patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=audit) as replay,patch('attach_axis_riser_segment_attributes.viewer_ancestry',return_value=(Path('BASE'),proof)),patch('attach_lower_floor_plan_attributes.verify_output') as redundant:
                ancestor,result=verify(target,graph)
            replay.assert_called_once_with(target.parent);redundant.assert_not_called();self.assertEqual(ancestor,Path('BASE'));self.assertEqual(len(result['records']),4)
            self.assertEqual(len(result['plan_DN_scope_fusion']),3);self.assertEqual(result['wave_plan_scope_adoption_audit'],audit);self.assertFalse(result['hil_ready'])
            paths=dependency_paths(result,target)
            self.assertEqual(paths['lower_floor_plan_attribute_audit'].parent,target.parent/'lower')
            self.assertEqual(paths['upper_floor_plan_attribute_audit'].parent,target.parent/'upper')
            self.assertEqual(paths['named_riser_plan_attribute_audit'].parent,target.parent/'named')

    def test_new_dispatch_runs_before_retained_lower_and_requires_its_root(self):
        graph={ROOT:dict(new=True),'sourceLowerFloorPlanSegmentAttributes':dict(old=True)};expected=(Path('BASE'),dict(native=True))
        with patch('wave_plan_scope_viewer_evidence.verify',return_value=expected) as current,patch('lower_floor_plan_viewer_evidence.verify') as old:
            self.assertEqual(verified_source_attribute_ancestor(Path('graph.json'),graph),expected)
        current.assert_called_once();old.assert_not_called()
        with self.assertRaisesRegex(ValueError,'verified adoption stage'):
            verified_source_attribute_ancestor(None,dict(edges=[dict(cross_view_attributes=dict(current_plan_scope_evidence={}))]))

    def test_stale_root_edge_evidence_or_lost_upper_lower_scope_is_rejected(self):
        for case in ('sha','root','edge','segment','parent','HIL'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                target,graph,audit=fixture(Path(temp))
                if case=='sha':audit['output_graph_sha256']='wrong'
                elif case=='root':graph[ROOT]['whole_DN_or_lengths_added']=1
                elif case=='edge':graph['edges'][-1]['cross_view_attributes']['current_plan_scope_evidence']['edge_id']='other'
                elif case=='segment':graph['edges'][0]['plan_segment_attributes']=[]
                elif case=='parent':audit['verified_lower_parent']['output_graph_sha256']='other'
                else:audit['human_accepted']=True
                target.write_text(json.dumps(graph),'utf8')
                if case!='sha':audit['output_graph_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
                with patch('adopt_wave_rebased_plan_scopes.verify_output',return_value=audit),self.assertRaises(ValueError):verify(target,graph)


if __name__=='__main__':unittest.main()
