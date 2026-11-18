import copy,unittest
from reviewed_fragment_detail_index import apply_classifications,preserve_current
from fragment_component_index import AUDIT


class ReviewedFragmentTests(unittest.TestCase):
    def fixture(self):
        bindings=[];classes=[dict(source_handle='UNREVIEWED',status='native_hold',adopted=False)];components=[];records=[];edges=[]
        for system,eid,handle,oldhandle,plan in [('supply','S','HS','OS','PS'),('return','R','HR','OR','PR')]:
            bindings.append(dict(system=system,axis_edge_id=eid,source_handle=handle,existing_source_handle=oldhandle,plan_edges=[plan],floor=1))
            classes.append(dict(source_handle=handle,axis_edge_id=eid,status='source_detail_profile_difference',adopted=False,
                domain='separate_named_external_port',plan_edges=[plan],floor=1,new_correspondence_assigned=False,mapping_id='M'+eid,
                plan_profile=[dict(ball_valve=1,flexible_joint=1)],axis_profile=[dict(ball_valve=2,flexible_joint=1)]))
            components.extend([dict(source_top_handle=handle,edge_id=eid,system_hint=system,equipment_type='球阀'),dict(source_top_handle=oldhandle,edge_id=eid,equipment_type='球阀')])
            records.append(dict(source_handle=oldhandle,status='existing_owner_independently_agrees',native_candidates=[dict(system=system)]));edges.append(dict(edge_id=eid,system=system))
        inventory=dict(added_components=[r for r in components if r['source_top_handle']in('HS','HR')],components=components,records=records)
        reply=dict(question_id='Q',source_evidence=dict(source_handles=['HS','OS','HR','OR']),explicit_answer=dict(decision='两组均为平面省略，实物按11各两阀'))
        return classes,inventory,dict(edges=edges),bindings,reply,dict(path='receipt',sha256='a'*64)

    def test_explicit_answer_preserves_real_profiles_old_classifications_and_other_holds(self):
        args=self.fixture();before=copy.deepcopy(args);rows=apply_classifications(*args)
        self.assertEqual(args,before);self.assertEqual(rows[0],args[0][0])
        for row in rows[1:]:
            self.assertTrue(row['adopted']);self.assertEqual(row['plan_profile'][0]['ball_valve'],1);self.assertEqual(row['axis_profile'][0]['ball_valve'],2)
            proof=row['received_detail_expression'];self.assertFalse(proof['profiles_claimed_equal']);self.assertIsNone(proof['missing_plan_symbol_position'])
            self.assertEqual(row['original_classification']['status'],'source_detail_profile_difference')

    def test_unconfirmed_scope_service_owner_or_other_profile_difference_stays_blocked(self):
        for kind in('negative','partial','wrong-service','wrong-plan','other-difference','count','old-owner','reply-handles','duplicate'):
            with self.subTest(kind=kind):
                c,i,g,b,r,p=copy.deepcopy(self.fixture())
                if kind=='negative':r['explicit_answer']['decision']='原图信息不足，暂不能判断'
                if kind=='partial':b.pop()
                if kind=='wrong-service':g['edges'][0]['system']='return'
                if kind=='wrong-plan':b[0]['plan_edges']=['OTHER']
                if kind=='other-difference':c[1]['axis_profile'][0]['gauge']=1
                if kind=='count':c[1]['axis_profile'][0]['ball_valve']=3
                if kind=='old-owner':i['records'][0]['status']='unresolved'
                if kind=='reply-handles':r['source_evidence']['source_handles'].remove('HS')
                if kind=='duplicate':b[1]['source_handle']='HS'
                with self.assertRaises(ValueError):apply_classifications(c,i,g,b,r,p)

    def graphs(self):
        base=dict(nodes=[dict(node_id='N')],edges=[dict(edge_id='E',equipment_inventory=[]),dict(edge_id='OTHER',equipment_inventory=[])],instances=[dict(id='ORIGINAL',source_top_handle='O')])
        def add(rows):
            g=copy.deepcopy(base);g['instances'].extend(rows);g['edges'][0]['equipment_inventory']=[dict(count=len(rows))]
            g[AUDIT]=dict(added_instances=[dict(id=r['id'])for r in rows],added_count=len(rows),previous_edge_inventories={'E':[]})
            return g
        a=dict(id='OLD-RECOVERED',source_top_handle='H1',edge_id='E');b=dict(id='NEW-REVIEWED',source_top_handle='H2',edge_id='E')
        return add([a]),add([a,b])

    def test_replace_overlay_keeps_all_old_instances_and_restores_same_full_parent(self):
        old,new=self.graphs();result=preserve_current(old,new,['H2']);self.assertEqual(result['old_instances_preserved'],2);self.assertEqual(result['new_instances'],1)
        for kind in('old-instance','pipe','unreviewed-inventory','wrong-source','extra'):
            bad=copy.deepcopy(new)
            if kind=='old-instance':bad['instances'][0]['source_top_handle']='changed'
            if kind=='pipe':bad['nodes'][0]['node_id']='WRONG'
            if kind=='unreviewed-inventory':bad['edges'][1]['equipment_inventory']=[dict(count=1)]
            if kind=='wrong-source':bad['instances'][-1]['source_top_handle']='H3'
            if kind=='extra':bad['instances'].append(dict(id='EXTRA'))
            with self.subTest(kind=kind),self.assertRaises(ValueError):preserve_current(old,bad,['H2'])


if __name__=='__main__':unittest.main()
