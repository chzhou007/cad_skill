import copy,json,math,tempfile,unittest
from pathlib import Path
from ezdxf.math import Matrix44
import test_native_exploded_device_joint_evidence as fixtures
from native_exploded_endpoint_evidence import collect
from native_line_path_evidence import LAYERS
from reconstruct_native_block_branches import source_child
from confirm_crossview_paths import sha
from repair_upstream_joint_systems import RULE


class ExplodedEndpointEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name)
        f=fixtures.ExplodedDeviceJointTests();f.setUp();self.f=f;g=f.g;m=f.doc.modelspace();f.c.dxf.layer='空调平面';g['metadata']=dict(source_sha256=f.h['source_sha256'])
        g['nodes'][0].update(x=-20.,y=0.,floor=1,system='supply');g['nodes'][1].update(x=20.,y=0.,floor=1,system='supply')
        g['edges'][0].update(attribute_paths=[[[-20.,0.],[10.,0.],[20.,0.]]],physical_length='unknown',path_length_complete=False)
        m.add_text('D',dxfattribs=dict(insert=(-20,0)));m.add_line((20,-10),(20,10),dxfattribs=dict(layer=LAYERS['supply']))
        for nid,y in [('L',-10),('R',10)]:
            g['nodes'].append(dict(node_id=nid,node_type='virtual_equipment',floor=1,system='supply',x=20.,y=float(y)))
            g['edges'].append(dict(edge_id=nid,start_node_id='T',end_node_id=nid,system='supply',attribute_paths=[[[20.,0.],[20.,float(y)]]]))
        records=[];changes=[];corrections=[]
        for i in range(4):
            eid='C'+str(i);owner='D'+str(i);x=100.*(i+1);b=f.doc.blocks.new('BODY'+str(i));inner=b.add_line((-10,0),(0,0),dxfattribs=dict(layer=LAYERS['supply']));outer=b.add_line((10,0),(20,0),dxfattribs=dict(layer=LAYERS['supply']));circle=b.add_circle((-9.75,0),2,dxfattribs=dict(layer='空调平面'));joint=b.add_blockref('J',(0,0));ins=m.add_blockref(b.name,(x,0))
            c=dict(source_line_chain=[ins.dxf.handle,inner.dxf.handle],source_circle_chain=[ins.dxf.handle,circle.dxf.handle],line_endpoint=[x-10,0.,0.],circle_center=[x-9.75,0.,0.],radius=2.,offset=.25,endpoint_index=0)
            match=dict(joint_chain=[ins.dxf.handle,joint.dxf.handle],inner_line_chain=c['source_line_chain'],circle_chain=c['source_circle_chain'],inner_contact=[x,0.,0.],outer_contact=[x+10,0.,0.],component_name='JC'+str(i))
            edge=dict(edge_id=eid,start_node_id='TC'+str(i),end_node_id=owner,system='supply',attribute_paths=[[[x+10,0.],[x+20,0.]]],equipment_inventory=[dict(equipment_type='金属软接',count=1,device_names=[match['component_name']])])
            edge['source_native_block_branch']=dict(source_sha256=f.h['source_sha256'],equipment_id=owner,endpoint_snapshot={k:edge[k] for k in ('start_node_id','end_node_id','attribute_paths')})
            g['nodes']+=[dict(node_id=owner,node_type='equipment',x=x-20,y=0.,system='supply',floor=1),dict(node_id='TC'+str(i),node_type='tee',x=x+20,y=0.,system='supply',floor=1)];g['edges'].append(edge)
            f.inv.append(dict(source_top_handle=ins.dxf.handle,assignment_status='assigned',edge_id=eid,owner_equipment=owner,equipment_type='金属软接',device_name=match['component_name']))
            records.append(dict(edge_id=eid,equipment_id=owner,system='supply',source_insert_handle=ins.dxf.handle,offset_contact=dict(contact=c),native_joint_evidence=dict(edges=[dict(matches=[match])])));changes.append(dict(to_edge=eid,offset_circle_evidence=c,joint_evidence=match));corrections.append(dict(to_edge=eid))
        g['sourceNativeBlockBranchReconstruction']=dict(source_sha256=f.h['source_sha256'],human_accepted=False,records=records)
        self.old_policy=root/'offset-policy.json';self.old_audit=root/'offset-audit.json';self.write(self.old_policy,dict(source_sha256=f.h['source_sha256'],joint_block='J',block_fingerprint_sha256=f.p['block_fingerprint_sha256'],max_radius_ratio=.2,corrections=corrections));self.write(self.old_audit,dict(status='source_evidence_repaired_unreviewed',source_sha256=f.h['source_sha256'],policy_sha256=sha(self.old_policy),changes=changes))
        self.policy=dict(f.p,offset_policy=str(self.old_policy),offset_audit=str(self.old_audit),offset_policy_sha256=sha(self.old_policy),offset_audit_sha256=sha(self.old_audit))
        self.reseal()

    def write(self,path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

    def reseal(self,**changes):
        p=json.loads(self.old_policy.read_text(encoding='utf8'));p.update(changes);self.write(self.old_policy,p);a=json.loads(self.old_audit.read_text(encoding='utf8'));a['policy_sha256']=sha(self.old_policy);self.write(self.old_audit,a)
        self.policy.update(offset_policy_sha256=sha(self.old_policy),offset_audit_sha256=sha(self.old_audit))
        for r in self.f.g['sourceNativeBlockBranchReconstruction']['records']:r['offset_contact'].update(control_policy_sha256=sha(self.old_policy),control_audit_sha256=sha(self.old_audit))

    def check(self):return collect(self.f.doc,self.f.g,self.f.inv,self.policy,self.f.h)

    def colour_error(self):
        f=self.f;f.a.dxf.layer=LAYERS['return'];record=dict(joint_handle=f.j.dxf.handle,source_sha256=f.h['source_sha256'],from_edge='OLD',to_edge='E',system='supply',logical_owner_equipment='D',device_name='J1',upstream_tee='T',source_line_handles=[f.b.dxf.handle],status='source_colour_error_resolved_by_confirmed_upstream_rule',physical_port_verified=False,physical_length='unknown',whole_graph_human_accepted=False,
            confirmation=dict(rule=RULE,status='user_confirmed',source_reference='scoped source Pair',statement='Follow the unchanged upstream main'),original_conflict=dict(contacts=[dict(lines=[dict(source_handle=line.dxf.handle,system=system,line_start=list(line.dxf.start),line_end=list(line.dxf.end))]) for line,system in [(f.a,'return'),(f.b,'supply')]]))
        f.g['edges'][0]['source_inline_system_resolutions']=[record];f.g['sourceInlineSystemResolutions']=[record];return record

    def test_exact_chain_and_unknown_anchor_preserve_graph_and_inventory(self):
        before=copy.deepcopy(self.f.g);inv=copy.deepcopy(self.f.inv);r=self.check();self.assertEqual(r['records'][0]['circle_relation'],'exact_native_circle_contact');self.assertEqual(len(r['inherited_controls']),4);self.assertEqual(self.f.g,before);self.assertEqual(self.f.inv,inv);self.assertIsNone(r['records'][0]['physical_length_mm']);self.assertFalse(r['component_owners_changed'])

    def test_offset_uses_all_independent_controls_without_snapping(self):
        self.f.c.dxf.center=(-9.75,0);point=list(self.f.a.dxf.start);r=self.check()['records'][0];self.assertEqual(len(r['matched_inherited_control_edges']),4);self.assertEqual(r['native_inner_line_XYZ'][0],point);self.assertEqual(list(self.f.a.dxf.start),point);self.assertEqual(r['native_circle_offset'],.25)

    def test_offset_profile_is_rotation_invariant(self):
        for angle in (90,180,270):
            with self.subTest(angle=angle):
                self.setUp();f=self.f;f.c.dxf.center=(-9.75,0);matrix=Matrix44.z_rotate(math.radians(angle))
                # Rotate the selected target and its actual source tee, not its
                # independent controls. The inherited profile is local-frame.
                selected=[f.j,f.a,f.b,f.c]+[e for e in f.doc.modelspace().query('LINE') if abs(e.dxf.start.x-20)<.01 and abs(e.dxf.end.x-20)<.01]+list(f.doc.modelspace().query('TEXT'))
                for e in selected:e.transform(matrix)
                for n in f.g['nodes'][:4]:
                    p=matrix.transform((n['x'],n['y'],0));n.update(x=p.x,y=p.y)
                for e in f.g['edges'][:3]:e['attribute_paths']=[[[matrix.transform((*p,0)).x,matrix.transform((*p,0)).y] for p in path] for path in e['attribute_paths']]
                self.assertEqual(len(self.check()['records'][0]['matched_inherited_control_edges']),4)

    def test_wrong_offset_profile_and_expanded_bounds_rejected(self):
        self.f.c.dxf.center=(-9.4,0)
        with self.assertRaises(ValueError):self.check()
        self.f.c.dxf.center=(-9.75,0);self.reseal(max_radius_ratio=.5)
        with self.assertRaises(ValueError):self.check()

    def test_missing_or_duplicated_controls_rejected(self):
        records=self.f.g['sourceNativeBlockBranchReconstruction']['records'];old=records.pop()
        with self.assertRaises(ValueError):self.check()
        records.append(old);records[1]['source_insert_handle']=records[0]['source_insert_handle']
        with self.assertRaises(ValueError):self.check()

    def test_historical_policy_and_current_control_source_drift_rejected(self):
        original=self.old_policy.read_bytes();self.old_policy.write_bytes(original+b' ')
        with self.assertRaises(ValueError):self.check()
        self.old_policy.write_bytes(original);record=self.f.g['sourceNativeBlockBranchReconstruction']['records'][0];root=self.f.doc.entitydb[record['source_insert_handle']];h=record['offset_contact']['contact']['source_line_chain'][1];self.f.doc.entitydb[h].dxf.start=(-11,0)
        with self.assertRaises(ValueError):self.check()

    def test_component_owner_or_unmeasured_length_claim_rejected(self):
        self.f.inv[0]['owner_equipment']='OTHER'
        with self.assertRaises(ValueError):self.check()
        self.f.inv[0]['owner_equipment']='D';self.f.g['edges'][0]['path_length_complete']=True
        with self.assertRaises(ValueError):self.check()

    def test_other_system_contact_duplicate_circle_and_extra_gap_rejected(self):
        duplicate=self.f.doc.modelspace().add_line((0,0),(0,10),dxfattribs=dict(layer=LAYERS['return']))
        with self.assertRaises(ValueError):self.check()
        self.f.doc.modelspace().delete_entity(duplicate);circle=self.f.doc.modelspace().add_circle((-10,0),2)
        with self.assertRaises(ValueError):self.check()
        self.f.doc.modelspace().delete_entity(circle);self.f.g['edges'][0]['attribute_paths']=[[[-20.,0.],[10.,0.],[11.,1.],[20.,0.]]]
        with self.assertRaises(ValueError):self.check()

    def test_unconfirmed_colour_change_is_not_allowed(self):
        self.f.a.dxf.layer=LAYERS['return']
        with self.assertRaises(ValueError):self.check()

    def test_exact_confirmed_colour_and_offset_relations_combine(self):
        self.f.c.dxf.center=(-9.75,0);record=self.colour_error();before=copy.deepcopy(self.f.g);result=self.check()['records'][0];self.assertEqual(result['source_colour_resolution'],record);self.assertEqual(result['matched_inherited_control_edges'],['C0','C1','C2','C3']);self.assertEqual(self.f.g,before);self.assertEqual(self.f.a.dxf.layer,LAYERS['return'])

    def test_other_joint_or_stale_upstream_confirmation_cannot_be_reused(self):
        r=self.colour_error();r['joint_handle']='OTHER'
        with self.assertRaises(ValueError):self.check()
        r['joint_handle']=self.f.j.dxf.handle;r['source_line_handles']=['OTHER']
        with self.assertRaises(ValueError):self.check()

    def test_source_tee_caption_Z_and_fingerprint_are_required(self):
        self.f.doc.modelspace().add_text('D')
        with self.assertRaises(ValueError):self.check()
        texts=list(self.f.doc.modelspace().query('TEXT'));self.f.doc.modelspace().delete_entity(texts[-1]);self.f.a.dxf.start=(-10,0,1)
        with self.assertRaises(ValueError):self.check()
        self.f.a.dxf.start=(-10,0,0);self.policy['block_fingerprint_sha256']='old'
        with self.assertRaises(ValueError):self.check()


if __name__=='__main__':unittest.main()
