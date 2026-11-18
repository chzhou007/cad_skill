import copy,math,unittest
from test_normalize_plan_circle_paths import CirclePathTests
from normalize_plan_circle_paths import apply
from source_reviewed_circle_branch_evidence import collect,branch_coverage
from crossview_equipment_branch_inventory import inspect_branch


class HistoricalReviewedCircleTests(CirclePathTests):
    def legacy_fixture(self,angle=0,mirror=1):
        doc,g,p=self.fixture(angle,mirror);g,_=apply(doc,g,p,'S')
        branch=g['edges'][0];old=branch['source_circle_connection'];node=next(n for n in g['nodes'] if n['node_id']=='T')
        comparison={k:old['source_comparison'][k] for k in ('review_kind','review_manifest','review_sha256','human_accepted')}
        meta=dict(source_comparison=comparison,circle_handle=old['circle_handle'],center=old['center'],source_rim=old['branch_rim'],line_system='supply',graphic_radius_is_physical_length=False,physical_length='unknown',source_graph_sha256='PARENT',screen_sha256='SCREEN')
        node['source_reviewed_circle']=copy.deepcopy(meta);branch['source_reviewed_circle_connection']=copy.deepcopy(meta)
        g['sourceReviewedCircleJunctionRepair']=dict(source_sha256='S',source_comparison=comparison,input_graph_sha256='PARENT',screen_sha256='SCREEN',supply_return_independent=True,physical_length='unknown',records=[dict(circle_handle=old['circle_handle'],tee='T',branch_edge='B',system='supply',main_child_edges=['M1','M2'])])
        return doc,g,p

    def crossover_fixture(self):
        doc,g,p=self.legacy_fixture();g.setdefault('metadata',{})['source_sha256']='S';edge=g['edges'][0]
        original=doc.entitydb[edge['source_handles'][0]];original.dxf.end=(0,5,0)
        far=doc.modelspace().add_line((0,7),(0,10),dxfattribs={'layer':'空调冷冻水供水'})
        doc.layers.new('空调冷冻水回水');cross=doc.modelspace().add_line((-5,6),(5,6),dxfattribs={'layer':'空调冷冻水回水'})
        edge['source_handles'].append(far.dxf.handle);edge['attribute_paths']=[[[0,2],[0,5]],[[0,7],[0,10]]]
        edge['path_length']=6;edge['physical_length']='unknown';edge['path_length_complete']=False
        edge.pop('source_circle_path_normalization');g.pop('sourceCirclePathNormalization')
        record=edge['source_layout_equipment_interface'];record['endpoint_snapshot']['attribute_paths']=copy.deepcopy(edge['attribute_paths'])
        g['sourceLayoutEquipmentOwnership']['records']=[copy.deepcopy(record)]
        edge['source_normalized_crossovers']=[dict(source_gap_id='G1',source_handles=[original.dxf.handle,far.dxf.handle],source_sha256='S',a=[0,5],b=[0,7],crossings=[dict(crossing=[0,6],crossed_handle=cross.dxf.handle,crossed_source_system='return')],crossing_connectivity='independent_pipes_no_junction',physical_length='unknown')]
        return doc,g,p

    def test_legacy_schema_rotations_mirrors_keep_graph_and_unknowns(self):
        for angle,mirror in [(0,1),(90,1),(180,-1),(270,-1)]:
            doc,g,p=self.legacy_fixture(angle,mirror);before=copy.deepcopy(g)
            result=inspect_branch(doc,g,'EQ','supply',dict(source_sha256='S',graph_sha256='G',inventory_sha256='I'),'plan',[])
            self.assertTrue(result['ready_for_mapping_comparison'],result)
            self.assertEqual(g,before);self.assertFalse(result['physical_ports_verified'])
            self.assertEqual(result['junction_evidence']['junctions'][0]['source_rays'][0]['scope'],'historical_source_reviewed_circle_rim')

    def test_crossover_replayed_as_same_service_chain_not_a_junction_or_length(self):
        doc,g,p=self.crossover_fixture();before=copy.deepcopy(g)
        result=inspect_branch(doc,g,'EQ','supply',dict(source_sha256='S',graph_sha256='G',inventory_sha256='I'),'plan',[])
        self.assertTrue(result['ready_for_mapping_comparison'],result)
        evidence=result['reviewed_circle_path_evidence'];self.assertEqual(len(evidence['paths']),2)
        self.assertEqual(len(evidence['crossovers']),1);self.assertIsNone(evidence['physical_length_mm']);self.assertEqual(g,before)

    def test_stale_pair_root_wrong_branch_and_radius_added_fail(self):
        for mode in ('pair','root','branch','radius','mixed','duplicate'):
            doc,g,p=self.legacy_fixture()
            if mode=='pair':__import__('pathlib').Path(p['review_manifest']).write_text('{}',encoding='utf8')
            elif mode=='root':g['sourceReviewedCircleJunctionRepair']['source_sha256']='BAD'
            elif mode=='branch':g['sourceReviewedCircleJunctionRepair']['records'][0]['branch_edge']='M1'
            elif mode=='radius':g['edges'][0]['attribute_paths'][0][0]=[0,0]
            elif mode=='mixed':g['edges'][1]['system']='return'
            else:
                line=doc.entitydb[g['edges'][1]['source_handles'][0]];doc.modelspace().add_line(line.dxf.start,line.dxf.end,dxfattribs={'layer':line.dxf.layer})
            with self.assertRaises(ValueError):collect(doc,g,'T','S','G')

    def test_missing_gap_wrong_crossed_system_and_unexplained_piece_fail(self):
        for mode in ('missing','same_system','moved','extra'):
            doc,g,p=self.crossover_fixture();edge=g['edges'][0]
            if mode=='missing':edge['source_normalized_crossovers']=[]
            elif mode=='same_system':edge['source_normalized_crossovers'][0]['crossings'][0]['crossed_source_system']='supply'
            elif mode=='moved':edge['attribute_paths'][1][0]=[0,8]
            else:edge['attribute_paths'].append([[0,8],[0,9]])
            with self.assertRaises(ValueError):branch_coverage(doc,g,edge,'S','G')


if __name__=='__main__':unittest.main()
