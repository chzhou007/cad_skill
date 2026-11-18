import copy,unittest,tempfile
from pathlib import Path
from test_native_external_port_destination import fixture as base_fixture
from native_capped_branch_annotations import text_frame
from native_capped_marker_port_context import discover,compute,verify_output,implementation_hashes,MODE
from confirm_crossview_paths import sha,encode

def fixture(angle=0,quantity=4):
    doc,graph,policy,source_hash,graph_hash=base_fixture(angle)
    caption=doc.entitydb[policy['caption']['text_handle']];caption.dxf.text='预留支管接口/共'+str(quantity)+'处'
    p,u,v,h=text_frame(caption);position=[p[0]-1.5*h*v[0],p[1]-1.5*h*v[1],p[2]]
    qualifier=doc.modelspace().add_text('盲板封堵',dxfattribs=dict(insert=position,height=h,rotation=caption.dxf.rotation,layer=caption.dxf.layer))
    for edge in graph['edges']:edge['connection_mode']='standalone_omission_to_first_tee'
    return doc,graph,policy,source_hash,graph_hash,qualifier

class Tests(unittest.TestCase):
    def test_caption_targets_all_existing_separate_ports_under_rotation(self):
        for angle in (0,90,180,270):
            with self.subTest(angle=angle):
                doc,g,p,sh,gh,q=fixture(angle);before=copy.deepcopy(g);data=discover(doc,g,sh,gh)
                self.assertEqual(g,before);self.assertEqual(data['pending'],[]);self.assertEqual(len(data['records']),1)
                row=data['records'][0];self.assertEqual(len(row['members']),4);self.assertFalse(row['common_marker_creates_pipe_connection'])
                self.assertEqual({r['system']for r in row['members']},{'supply','return'})
                self.assertTrue(all(r['physical_length_mm']is None and not r['physical_port_verified']for r in row['members']))
    def test_quantity_does_not_generate_or_remove_any_current_port(self):
        for quantity in (2,99):
            doc,g,p,sh,gh,q=fixture(quantity=quantity);row=discover(doc,g,sh,gh)['records'][0]
            self.assertEqual(row['declared_quantity'],quantity);self.assertEqual(len(row['members']),4);self.assertFalse(row['quantity_expanded_into_ports'])
    def test_source_service_port_marker_display_membership_Z_and_extra_contacts_block(self):
        for mode in ('service','missing_port','extra','display','Z','marker','port_owner','port_marker','equipment','qualifier','duplicate_qualifier'):
            doc,g,p,sh,gh,q=fixture();node=g['nodes'][-1];spec=p['members'][0]
            if mode=='service':doc.entitydb[spec['source_line_handle']].dxf.layer='空调冷冻水回水'
            elif mode=='missing_port':node['ports'].pop()
            elif mode=='extra':doc.modelspace().add_line((80,40),(80,0),dxfattribs=dict(layer='空调冷冻水供水'))
            elif mode=='display':g['edges'][0]['attribute_paths'][0][-1]=[999,0]
            elif mode=='Z':doc.entitydb[spec['source_line_handle']].dxf.end=(10,0,100)
            elif mode=='marker':doc.entitydb[p['marker_handle']].closed=True
            elif mode=='port_owner':node['ports'][0]['node_id']='OTHER'
            elif mode=='port_marker':node['ports'][0]['source_marker_handle']='OTHER'
            elif mode=='equipment':node['node_type']='equipment'
            elif mode=='qualifier':q.dxf.text='无关说明'
            else:doc.modelspace().add_text(q.dxf.text,dxfattribs=dict(insert=q.dxf.insert,height=q.dxf.height,rotation=q.dxf.rotation,layer=q.dxf.layer))
            with self.subTest(mode=mode):
                data=discover(doc,g,sh,gh);self.assertEqual(data['records'],[]);self.assertTrue(data['pending'])
    def test_duplicate_caption_cannot_count_the_same_marker_twice(self):
        doc,g,p,sh,gh,q=fixture();c=doc.entitydb[p['caption']['text_handle']]
        doc.modelspace().add_text(c.dxf.text,dxfattribs=dict(insert=c.dxf.insert,height=c.dxf.height,rotation=c.dxf.rotation,layer=c.dxf.layer))
        data=discover(doc,g,sh,gh);self.assertEqual(data['records'],[]);self.assertEqual(len(data['pending']),2)
    def test_duplicate_graph_and_port_identities_and_source_drift_fail_before_reading(self):
        for mode in ('source','node','edge','port'):
            doc,g,p,sh,gh,q=fixture()
            if mode=='source':g['metadata']['source_sha256']='CHANGED'
            elif mode=='node':g['nodes'].append(copy.deepcopy(g['nodes'][0]))
            elif mode=='edge':g['edges'].append(copy.deepcopy(g['edges'][0]))
            else:g['nodes'][-1]['ports'].append(copy.deepcopy(g['nodes'][-1]['ports'][0]))
            with self.subTest(mode=mode),self.assertRaises(ValueError):discover(doc,g,sh,gh)
    def test_formal_entry_replays_real_DXF_and_rejects_changed_recorded_bytes(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);doc,g,p,sh,gh,q=fixture();source=root/'native.dxf';doc.saveas(source);g['metadata']['source_sha256']=sha(source)
            graph=root/'graph.json';graph.write_bytes(encode(g));paths=dict(source=source,graph=graph);data=compute(paths)
            self.assertEqual(len(data['records'][0]['members']),4);out=root/'out';out.mkdir();target=out/'capped-marker-context.json';target.write_bytes(encode(data))
            receipt=dict(mode=MODE,inputs={k:dict(path=str(v),sha256=sha(v))for k,v in paths.items()},implementation_sha256=implementation_hashes(),output_sha256=sha(target))
            (out/'capped-marker-context-receipt.json').write_bytes(encode(receipt));self.assertEqual(verify_output(out)['records'],data['records'])
            target.write_bytes(encode(dict(data,human_accepted=True)))
            with self.assertRaisesRegex(ValueError,'recorded bytes'):verify_output(out)
    def test_pipeline_entry_preserves_pending_scope_and_propagates_native_failure(self):
        import sys
        from unittest.mock import patch
        folder=Path(__file__).resolve().parents[2]/'orchestrate-cad-drawing-pipeline/scripts'
        if str(folder)not in sys.path:sys.path.insert(0,str(folder))
        from pipeline import validate_capped_marker_context
        with patch('native_capped_marker_port_context.verify_output',return_value=dict(records=[dict(members=[dict(),dict()])],pending=[]))as native:
            result=validate_capped_marker_context('run');native.assert_called_once_with('run')
            self.assertEqual(result['separate_source_checked_ports'],2);self.assertEqual(result['status'],'pending')
            self.assertFalse(result['hil_ready']);self.assertFalse(result['human_accepted'])
        with patch('native_capped_marker_port_context.verify_output',side_effect=ValueError('stale source')):
            with self.assertRaisesRegex(ValueError,'stale source'):validate_capped_marker_context('run')

if __name__=='__main__':unittest.main()
