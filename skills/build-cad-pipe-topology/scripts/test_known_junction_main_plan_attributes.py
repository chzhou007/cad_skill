import copy
import unittest
from contextlib import ExitStack
from unittest.mock import patch

import known_junction_main_plan_attributes as owner


class PlanAttributeTests(unittest.TestCase):
    def setup_read(self):
        g=dict(edges=[dict(edge_id='P',system='supply',attribute_paths=[[[0,0],[10,0]]])])
        texts=[dict(handle='COMP',text='DN300',layer='LABEL',position=[5,20],height=1),
               dict(handle='PIPE',text='DN200',layer='LABEL',position=[5,1],height=1)]
        origin=dict(source_sha256='S',qualified_component_DN=dict(source_sha256='S',graph_sha256='OLD'))
        qualified=dict(consumed_DN_text_handles=['COMP'],consumed_leader_handles=['LEADER'],records=[dict(nominal_mm=300)])
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(owner,'catalog',return_value=(texts,dict(F_text_handles=[]))))
        component=stack.enter_context(patch.object(owner,'component_labels',return_value=qualified))
        guard=stack.enter_context(patch.object(owner,'guard_leader_bridges'))
        assign=stack.enter_context(patch.object(owner,'direct_diameters',return_value=([],[])))
        inherit=stack.enter_context(patch.object(owner,'infer',return_value=dict(records=[])))
        return g,texts,origin,component,guard,assign,inherit

    def test_component_DN_is_excluded_before_pipe_assignment_and_leader_guard(self):
        g,texts,origin,component,guard,assign,inherit=self.setup_read()
        # No pipe value is fabricated for this fixture; it checks the boundary
        # between the independently tested component and pipe source readers.
        texts.pop()  # leave only the component-qualified DN300
        before=copy.deepcopy(origin)
        result,proof=owner.read_diameters(None,g,{'P'},origin,'S','CURRENT',{})
        self.assertEqual(assign.call_args_list[0].args[0],[])
        self.assertEqual(guard.call_args.args[3],['LEADER'])
        self.assertEqual(inherit.call_args.args[1],[])
        self.assertFalse(proof['qualified_component_values_used_as_pipe_seeds'])
        self.assertEqual(origin,before)
        self.assertEqual(component.call_args.args[2]['graph_sha256'],'CURRENT')

    def test_failed_component_qualification_does_not_remove_its_text(self):
        g,_,origin,component,_,assign,_=self.setup_read();component.side_effect=ValueError('native leader differs')
        with self.assertRaisesRegex(ValueError,'native leader'):
            owner.read_diameters(None,g,{'P'},origin,'S','CURRENT',{})
        assign.assert_not_called()

    def test_qualifier_from_different_source_blocks(self):
        g,_,origin,component,_,_,_=self.setup_read();origin['qualified_component_DN']['source_sha256']='OTHER'
        with self.assertRaisesRegex(ValueError,'origin source'):
            owner.read_diameters(None,g,{'P'},origin,'S','CURRENT',{})
        component.assert_not_called()

    def test_ambiguous_pipe_annotation_is_not_resolved_by_nearest_device(self):
        g,_,origin,_,_,assign,_=self.setup_read();assign.return_value=([],[dict(candidate_edge_ids=['P'])])
        with self.assertRaisesRegex(ValueError,'Ambiguous'):
            owner.read_diameters(None,g,{'P'},origin,'S','CURRENT',{})

    def test_unparsed_DN_in_scope_remains_a_blocker(self):
        g,texts,origin,_,_,assign,_=self.setup_read();texts[-1]['text']='DN200/DN150'
        assign.side_effect=[([],[]),([],[dict(candidate_edge_ids=['P'])])]
        with self.assertRaisesRegex(ValueError,'Unparsed'):
            owner.read_diameters(None,g,{'P'},origin,'S','CURRENT',{})

    def test_visible_unattributed_pipe_DN_is_not_silently_dropped(self):
        g,_,origin,_,_,_,_=self.setup_read()
        with self.assertRaisesRegex(ValueError,'Unattributed'):
            owner.read_diameters(None,g,{'P'},origin,'S','CURRENT',{})

    def valid_result(self):
        row=dict(mapping_id='M',plan_edges=['P'],iso_edges=['I'],system='supply',whole_axis_DN_selected=False,
            whole_axis_physical_length_mm=None,physical_ports_verified=False,human_accepted=False,
            diameter=dict(edge_id='P',system='supply',nominal_mm=200,human_accepted=False),
            horizontal_projection=dict(value_mm=1000,status='native_plan_pipe_XY_inline_interiors_unknown',
                installed_whole_edge_length_mm=None,inline_joint_interior_length_mm=None,joint_graphic_spans_added=False))
        return dict(mode=owner.MODE,status='native_direct_main_plan_DN_XY_source_checked_not_fused',records=[row],
                    local_graphs_mutated=False,physical_values_fused=False,human_accepted=False)

    def test_inline_XY_is_retained_with_unknown_joint_interior_and_installed_length(self):
        data=self.valid_result();before=copy.deepcopy(data);result=owner.check_result(data)
        self.assertEqual(result['known_DN_scopes'],1);self.assertEqual(result['inline_interior_length_unknown'],1)
        self.assertEqual(data,before)

    def test_unknown_DN_and_XY_stay_unknown_instead_of_zero(self):
        data=self.valid_result();data['records'][0]['diameter']['nominal_mm']=None
        data['records'][0]['horizontal_projection']['value_mm']=None
        result=owner.check_result(data)
        self.assertEqual((result['known_DN_scopes'],result['measured_plan_XY_scopes']),(0,0))

    def test_zero_negative_boolean_and_nonfinite_values_cannot_pass(self):
        for key,field in [('diameter','nominal_mm'),('horizontal_projection','value_mm')]:
            for value in (0,-1,True,float('nan'),float('inf')):
                data=self.valid_result();data['records'][0][key][field]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):owner.check_result(data)

    def test_changed_DN_edge_or_service_blocks(self):
        for key,value in [('edge_id','OTHER'),('system','return')]:
            data=self.valid_result();data['records'][0]['diameter'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):owner.check_result(data)

    def test_repeated_axis_or_plan_writer_blocks(self):
        data=self.valid_result();row=copy.deepcopy(data['records'][0]);row['mapping_id']='M2';data['records'].append(row)
        with self.assertRaisesRegex(ValueError,'writer'):owner.check_result(data)

    def test_plan_XY_cannot_be_promoted_to_whole_axis_or_physical_port(self):
        for key,value in [('whole_axis_DN_selected',True),('whole_axis_physical_length_mm',1000),('physical_ports_verified',True),('human_accepted',True)]:
            data=self.valid_result();data['records'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):owner.check_result(data)

    def test_installed_length_cannot_be_filled_from_source_XY(self):
        data=self.valid_result();data['records'][0]['horizontal_projection']['installed_whole_edge_length_mm']=1000
        with self.assertRaisesRegex(ValueError,'length scope'):owner.check_result(data)


if __name__=='__main__':unittest.main()
