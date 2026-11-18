import copy,json,unittest
from pathlib import Path
from test_source_reviewed_circle_branch_evidence import HistoricalReviewedCircleTests
from source_reviewed_circle_branch_evidence import collect,collect_user,repair_root,historical_control_parent
from confirm_crossview_paths import sha,encode
from crossview_equipment_branch_inventory import native_tee


class HistoricalCircleControlTests(unittest.TestCase):
    def fixture(self):
        helper=HistoricalReviewedCircleTests();self.addCleanup(helper.doCleanups)
        return helper.legacy_fixture()

    def user_fixture(self):
        doc,g,p=self.fixture();node=g['nodes'][0];edge=g['edges'][0];meta=node.pop('source_reviewed_circle')
        confirmation=dict(confirmed_by='user',question='Are these independent same-system circle contacts connected?',answer='yes')
        meta.pop('source_comparison');meta['confirmation']=confirmation;meta['circle_layer']=doc.entitydb[meta['circle_handle']].dxf.layer
        meta.update(circle_z=0,main_z_at_center=0,branch_z_at_rim=0)
        node['user_confirmed_circle']=copy.deepcopy(meta);edge.pop('source_reviewed_circle_connection');edge['source_user_circle_connection']=copy.deepcopy(meta)
        old=g.pop('sourceReviewedCircleJunctionRepair');old.pop('source_comparison');old['confirmation']=copy.deepcopy(confirmation)
        g['userConfirmedCircleJunctionRepair']=dict(records=[],previous_repair=old)
        return doc,g,p

    def test_buried_technical_root_is_replayed_without_mutating_history(self):
        doc,g,p=self.fixture();old=g['sourceReviewedCircleJunctionRepair'];g['sourceReviewedCircleJunctionRepair']=dict(records=[],previous_repair=dict(records=[],previous_repair=old))
        before=copy.deepcopy(g);result=collect(doc,g,'T','S','G');self.assertEqual(g,before);self.assertEqual(result['junctions'][0]['node_id'],'T')
        g['sourceReviewedCircleJunctionRepair']['records']=copy.deepcopy(old['records']);g['sourceReviewedCircleJunctionRepair']['source_comparison']=copy.deepcopy(old['source_comparison'])
        with self.assertRaises(ValueError):collect(doc,g,'T','S','G')

    def test_historical_user_contact_dispatch_preserves_source_colour_and_Z(self):
        doc,g,p=self.user_fixture();node=g['nodes'][0];edge=g['edges'][0];before=copy.deepcopy(g)
        result=native_tee(doc,g,'T','S','G');self.assertEqual(result['status'],'native_user_confirmed_circle_ray_evidence_replayed');self.assertFalse(result['human_accepted']);self.assertEqual(g,before)
        circle=doc.entitydb[node['user_confirmed_circle']['circle_handle']];circle.dxf.layer='OTHER'
        with self.assertRaises(ValueError):collect_user(doc,g,'T','S','G')

    def test_user_confirmation_cannot_suppress_native_Z_or_crossing_guards(self):
        for kind in ('Z','opposite','fourway','fake_answer','radius','nonfinite'):
            doc,g,p=self.user_fixture();edge=g['edges'][0]
            if kind=='Z':doc.entitydb[edge['source_handles'][0]].dxf.start=(0,2,2)
            elif kind=='opposite':doc.modelspace().add_line((0,-10),(0,10),dxfattribs={'layer':'空调冷冻水回水'})
            elif kind=='fourway':g['edges'].append(dict(g['edges'][1],edge_id='EXTRA'))
            elif kind=='fake_answer':g['nodes'][0]['user_confirmed_circle']['confirmation']['confirmed_by']='algorithm'
            elif kind=='nonfinite':doc.entitydb[edge['source_handles'][0]].dxf.end=(0,10,float('nan'))
            else:edge['attribute_paths'][0][0]=[0,0]
            with self.assertRaises(ValueError):collect_user(doc,g,'T','S','G')

    def test_nonzero_user_Z_is_retained_and_must_match_the_original_contact(self):
        doc,g,p=self.user_fixture();meta=g['nodes'][0]['user_confirmed_circle'];circle=doc.entitydb[meta['circle_handle']];line=doc.entitydb[g['edges'][0]['source_handles'][0]]
        circle.dxf.center=(0,0,2);line.dxf.start=(0,2,5);line.dxf.end=(0,10,7)
        meta.update(circle_z=2,branch_z_at_rim=5);g['edges'][0]['source_user_circle_connection']=copy.deepcopy(meta)
        result=collect_user(doc,g,'T','S','G');self.assertEqual(result['native_Z']['circle_z'],2);self.assertEqual(result['native_Z']['branch_z_at_rim'],5)
        line.dxf.start=(0,2,5.1)
        with self.assertRaisesRegex(ValueError,'Z changed'):collect_user(doc,g,'T','S','G')

    def test_reviewed_symbol_wrong_service_colour_never_changes_the_two_pipe_systems(self):
        doc,g,p=self.user_fixture();node=g['nodes'][0];meta=node['user_confirmed_circle'];meta['line_system']='return';node['system']='return'
        for edge in g['edges']:
            edge['system']='return'
            for h in edge['source_handles']:doc.entitydb[h].dxf.layer='空调冷冻水回水'
        g['edges'][0]['source_user_circle_connection']=copy.deepcopy(meta)
        g['userConfirmedCircleJunctionRepair']['previous_repair']['records'][0]['system']='return'
        result=collect_user(doc,g,'T','S','G');self.assertEqual(result['junctions'][0]['system'],'return')
        self.assertEqual(doc.entitydb[meta['circle_handle']].dxf.layer,'空调冷冻水供水')

    def test_3D_parent_uses_real_pinned_retired_terminal_not_current_fake_node(self):
        doc,g,p=self.fixture();node=g['nodes'][0];meta=node['source_reviewed_circle'];root=g['sourceReviewedCircleJunctionRepair'];record=root['records'][0];record['retired_terminal']='UT'
        before=copy.deepcopy(g);before.setdefault('metadata',{})['source_sha256']='S';before['nodes'].append(dict(node_id='UT',subtype='unresolved_source_terminal',floor=1,x=0,y=2));before['edges'][0]['start_node_id']='UT'
        ref=dict(circle_handle='CONTROL');g['nodes'].append(dict(node_id='TC',user_confirmed_circle=ref))
        folder=Path(p['review_manifest']).parent;parent=folder/'parent.json';parent.write_bytes(encode(before));root['input_graph_sha256']=sha(parent);meta['source_graph_sha256']=sha(parent)
        (folder/'manifest.json').write_bytes(encode(dict(graph=str(parent),source_sha256='S',graph_sha256=sha(parent))))
        row=dict(branch_handle=g['edges'][0]['source_handles'][0],confirmed_plan_control=ref)
        recovered,proof=historical_control_parent(g,root,meta,row,'S');self.assertEqual(recovered,before);self.assertEqual(proof['retired_terminal'],'UT');self.assertNotIn('UT',[n['node_id'] for n in g['nodes']])
        parent.write_text('{}',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'parent changed'):historical_control_parent(g,root,meta,row,'S')


if __name__=='__main__':unittest.main()
