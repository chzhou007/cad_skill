import copy,unittest
from test_native_capped_branch_annotations import Tests as NativeTests
from discover_native_capped_annotations import discover

class Tests(unittest.TestCase):
    def test_all_native_handles_discovered_under_rotation_and_mirror(self):
        for angle in (0,37,90,180,270):
            for mirror in (False,True):
                with self.subTest(angle=angle,mirror=mirror):
                    doc,g,expected=NativeTests().fixture(angle,mirror);before=copy.deepcopy(g)
                    result=discover(doc,g,'S','G');self.assertEqual(result['selections'],[expected]);self.assertEqual(result['pending'],[])
                    self.assertEqual(g,before);self.assertFalse(result['graph_mutated']);self.assertFalse(result['quantity_expanded_into_ports'])
                    record=result['source_inventory']['records'][0];self.assertIsNone(record['physical_length_mm'])
    def test_connected_native_two_segment_leader_reuses_the_strict_collector(self):
        doc,g,c=NativeTests().fixture();line=doc.entitydb[c['leader_handles'][0]];a,b=list(line.dxf.start),list(line.dxf.end)
        middle=[(x+y)/2 for x,y in zip(a,b)];line.dxf.end=middle
        second=doc.modelspace().add_line(middle,b,dxfattribs={'layer':line.dxf.layer})
        result=discover(doc,g,'S','G');self.assertEqual(result['selections'][0]['leader_handles'],[line.dxf.handle,second.dxf.handle])
    def test_missing_qualifier_and_broken_leader_do_not_infer_nearest_leaf(self):
        for mode in ('qualifier','leader'):
            doc,g,c=NativeTests().fixture()
            if mode=='qualifier':doc.entitydb[c['qualifier_handle']].dxf.insert=(3000,4000)
            else:doc.entitydb[c['leader_handles'][0]].dxf.end=(1440,2060,0)
            with self.subTest(mode=mode):
                result=discover(doc,g,'S','G');self.assertEqual(result['selections'],[]);self.assertIsNone(result['source_inventory']);self.assertEqual(len(result['pending']),1)
    def test_competing_frontier_and_duplicate_marker_keep_all_candidates_pending(self):
        for mode in ('frontier','marker'):
            doc,g,c=NativeTests().fixture()
            if mode=='frontier':
                n=copy.deepcopy(g['nodes'][0]);n['node_id']='OTHER';g['nodes'].append(n)
                g['edges'].append(dict(g['edges'][0],edge_id='OTHER_EDGE',end_node_id='OTHER'))
            else:
                bar=doc.entitydb[c['marker_handles'][1]];doc.modelspace().add_line(bar.dxf.start,bar.dxf.end,dxfattribs={'layer':bar.dxf.layer})
            with self.subTest(mode=mode):self.assertEqual(discover(doc,g,'S','G')['selections'],[])
    def test_two_overlapping_native_captions_cannot_claim_one_frontier_twice(self):
        doc,g,c=NativeTests().fixture();caption=doc.entitydb[c['caption_handle']]
        doc.modelspace().add_text('预留支管接口/共4处',dxfattribs=dict(insert=caption.dxf.insert,height=caption.dxf.height,layer=caption.dxf.layer))
        result=discover(doc,g,'S','G');self.assertEqual(result['selections'],[])
        self.assertTrue(any(r['reason']=='caption_claims_compete_for_one_frontier_or_marker'for r in result['pending']))
    def test_existing_typed_external_ports_need_their_original_owner(self):
        doc,g,c=NativeTests().fixture();g['nodes'][0].update(subtype='external_system_interface',ports=[dict(port_id='P')])
        result=discover(doc,g,'S','G');self.assertEqual(result['selections'],[])
        self.assertIn('existing_typed_ports',result['pending'][0]['reason']);self.assertEqual(g['nodes'][0]['ports'],[dict(port_id='P')])
    def test_source_service_or_multiple_incident_edges_cannot_be_relaxed_by_discovery(self):
        for mode in ('source','service','nonleaf'):
            doc,g,c=NativeTests().fixture()
            if mode=='source':
                with self.assertRaisesRegex(ValueError,'identity'):discover(doc,g,'OTHER','G')
                continue
            if mode=='service':g['nodes'][0]['system']='return'
            else:g['edges'].append(dict(g['edges'][0],edge_id='SECOND'))
            with self.subTest(mode=mode):self.assertEqual(discover(doc,g,'S','G')['selections'],[])
    def test_whole_view_entry_replays_native_inputs_and_rejects_tampered_output(self):
        import tempfile,json
        from pathlib import Path
        from confirm_crossview_paths import sha,encode
        import batch_discover_capped_annotations as batch
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);doc,g,c=NativeTests().fixture();source=root/'native.dxf';doc.saveas(source)
            g['metadata']['source_sha256']=sha(source);graph=root/'graph.json';graph.write_bytes(encode(g))
            pin=lambda p:dict(path=str(p),sha256=sha(p))
            manifest=root/'manifest.json';manifest.write_bytes(encode(dict(views=[dict(id='plan',inputs=dict(source=pin(source),graph=pin(graph)))])))
            result=batch.compute(json.loads(manifest.read_text(encoding='utf8')));self.assertEqual(result['counts']['native_direct_annotations'],1)
            out=root/'out';out.mkdir();target=out/'discovery.json';target.write_bytes(encode(result))
            audit=dict(mode=batch.MODE,manifest=pin(manifest),implementation_sha256=batch.implementation_hashes(),output_sha256=sha(target))
            (out/'native-capped-discovery-audit.json').write_bytes(encode(audit));self.assertEqual(batch.verify_output(out)['counts'],result['counts'])
            target.write_bytes(encode(dict(result,human_accepted=True)))
            with self.assertRaisesRegex(ValueError,'recorded bytes'):batch.verify_output(out)

if __name__=='__main__':unittest.main()
