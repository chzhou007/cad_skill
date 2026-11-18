import copy,json,tempfile,unittest
from pathlib import Path
from refresh_ambiguous_layout_DN import context_from,delta,NATIVE_MODE,DIRECT,sha


class Tests(unittest.TestCase):
    def fixture(self,root):
        p=Path(root);(p/'public/data').mkdir(parents=True)
        graph=dict(edges=[dict(edge_id='E',system='return',attribute_paths=[[[0,0],[0,10]]])])
        (p/'public/data/graph.json').write_text(json.dumps(graph),encoding='utf-8')
        context=dict(current_rendered_graph_sha256=sha(p/'public/data/graph.json'),axis_rule_vertical_DN=dict(records=[],count=0,
            all_current_vertical_domains=447,source_bindings=dict(native_source='S',native_graph='G')))
        (p/'public/data/manifest.json').write_text(json.dumps(dict(attributeValueContext=context)),encoding='utf-8')
        owner=dict(source_chain=['ROOT','CHILD'],current_edge_id='E',nominal_mm_candidate=80,
            independent_control_roots=['A','B','C','D'],native_binding=dict(Z_coincident=True),source_text=dict(handle='TEXT'))
        r=dict(edge_id='E',path_index=0,segment_index=0,system='return',nominal_mm=80,scope_points=[[0,0],[0,10]],
            observations=[dict(native_evidence=owner)],connection_rule=DIRECT,annotation_guard=dict(other_in_scope_DN_annotations=[],F_crossings=[]),physical_length_mm=None,whole_edge_DN_assigned=False)
        proof=dict(mode=NATIVE_MODE,records=[r],human_accepted=False,graph_mutated=False,components_reassigned=False,
            physical_lengths_assigned=0,horizontal_values_assigned=0,whole_edge_DN_assigned=0,
            original_readers_and_thresholds_unchanged=True,all_target_texts_excluded_from_controls=True,
            inputs=dict(parent_viewer_manifest=dict(sha256=sha(p/'public/data/manifest.json')),axis_source=dict(sha256='S'),axis_graph=dict(sha256='G')),
            counts=dict(previous_known=447,new_known=1,current_known=448,remaining_unknown=49))
        native=p/'proof.json';native.write_text(json.dumps(proof),encoding='utf-8')
        return p,proof,native,context

    def test_old_context_preserved_and_known_attributes_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,proof,path,old=self.fixture(tmp);out=context_from(p,proof,path)
            self.assertEqual(old['axis_rule_vertical_DN']['records'],[])
            self.assertEqual(out['axis_rule_vertical_DN']['all_current_vertical_domains'],448)
            row=out['axis_rule_vertical_DN']['records'][0]
            before=[dict(edge_id='E',values=dict(diameter_nominal_mm=150)),dict(edge_id='X',values=dict(known_length_mm=100))]
            after=copy.deepcopy(before);after[0]['values'].update(axis_rule_vertical_DN_segment_count=1,axis_rule_vertical_DN_segments_json=json.dumps([row]),axis_rule_vertical_DN_source_sha256='S')
            self.assertEqual(delta(before,after,out,[row])['new_vertical_domains'],1)
            after[1]['values']['known_length_mm']=0
            with self.assertRaises(ValueError):delta(before,after,out,[row])

    def test_insufficient_controls_source_and_transition_guards_block(self):
        for variant in ('controls','self','guard','source','length'):
            with self.subTest(variant=variant),tempfile.TemporaryDirectory() as tmp:
                p,proof,path,_=self.fixture(tmp);r=proof['records'][0];o=r['observations'][0]['native_evidence']
                if variant=='controls':o['independent_control_roots']=['A','B','C']
                elif variant=='self':o['independent_control_roots'][0]='ROOT'
                elif variant=='guard':r['annotation_guard']['F_crossings']=['F']
                elif variant=='source':proof['inputs']['axis_source']['sha256']='changed'
                else:r['physical_length_mm']=0
                with self.assertRaises(ValueError):context_from(p,proof,path)


if __name__=='__main__':unittest.main()
