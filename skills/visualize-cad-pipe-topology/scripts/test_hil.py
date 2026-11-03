"""Regression tests for local HIL persistence, review semantics and portable pairs."""
import base64
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid
import zipfile
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'assets/viewer'))
from hil_server import ReviewStore, ReviewError, identity, HilHandlerMixin


class HilTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        data=self.root/'public/data';data.mkdir(parents=True)
        self.manifest={'projectId':'OTHER-CENTER','bundleId':'ui-v1','sourceHashes':{
            'graph':'graph-hash','devices':'instances-hash','ports':'ports-hash',
            'main_dxf':'source-hash','legend_dxf':'legend-hash'}}
        graph={'nodes':[{'node_id':'N1'},{'node_id':'N2'}],
               'edges':[{'edge_id':'E1','start_node_id':'N1','end_node_id':'N2'}],
               'instances':[], 'transform':{'originX':100,'originY':200,'scale':2}}
        (data/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf8')
        (data/'graph.json').write_text(json.dumps(graph),encoding='utf8')
        self.store=ReviewStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def issue(self):
        return {'id':str(uuid.uuid4()),'nodes':['N1'],'edges':['E1'], 'region':[1,2,3,4],
                'note':'\u7f3a\u5c11 T \u8282\u70b9 <script> & "quote"','author':'engineer'}

    def save(self,doc,**kw):
        return self.store.save({'baseRevision':doc['revision'],'document':doc,**kw})

    def initial(self):
        d=self.store.read();d['errors']=[self.issue()];return self.save(d)

    def test_comparison_blocks_confirmation_but_preserves_notes(self):
        self.store.graph['metadata']={'hil_ready':False}
        d=self.initial()
        with self.assertRaises(ReviewError):self.save(d,confirm=True,reviewer='expert')
        self.assertIsNone(self.store.read()['confirmation'])
        self.assertEqual(len(self.store.read()['errors']),1)

    def test_template_change_keeps_dataset_identity(self):
        other=copy.deepcopy(self.manifest);other['bundleId']='new-ui';other['sourceHashes']['config']='new-display'
        self.assertEqual(identity(other),identity(self.manifest))
        other['sourceHashes']['graph']='new-topology'
        self.assertNotEqual(identity(other),identity(self.manifest))

    def test_unicode_restart_source_coordinates_and_history(self):
        d=self.initial();e=d['errors'][0]
        self.assertEqual(e['sourceBounds'],[102,188,6,8])
        self.assertEqual(ReviewStore(self.root).read(),d)
        self.assertTrue((self.store.folder/'history/00000001.json').is_file())
        self.assertIn('<script>',e['note'])

    def test_confirmation_global_note_survives_structural_change_invalidates(self):
        d=self.initial();d=self.save(d,confirm=True,reviewer='Reviewer')
        self.assertEqual(d['confirmation']['scope'],'entire_dataset')
        d['errors'][0]['note']='New annotation'
        d=self.save(d);self.assertIsNotNone(d['confirmation'])
        d['errors'][0]['region'][0]+=1
        d=self.save(d);self.assertIsNone(d['confirmation'])
        d=self.save(d,confirm=True,reviewer='Reviewer')
        d['errors']=[];d=self.save(d);self.assertIsNone(d['confirmation'])

    def test_revision_conflict_cannot_overwrite(self):
        old=self.store.read();self.initial()
        with self.assertRaises(ReviewError) as error:self.save(old)
        self.assertEqual(error.exception.status,409)
        self.assertEqual(len(self.store.read()['errors']),1)

    def test_unknown_object_bad_bounds_and_close_without_conclusion_rejected(self):
        for field,value in [('nodes',['missing']),('region',[0,0,float('nan'),1]),('closed',True)]:
            with self.subTest(field=field):
                d=self.store.read();e=self.issue();e[field]=value;d['errors']=[e]
                with self.assertRaises(ReviewError):self.save(d)
                self.assertEqual(self.store.read()['revision'],0)

    def test_io_failure_does_not_claim_saved(self):
        d=self.initial();d['errors'][0]['note']='Not committed'
        with patch('hil_server.os.replace',side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):self.save(d)
        self.assertNotEqual(self.store.read()['errors'][0]['note'],'Not committed')

    def response(self,d):
        e=d['errors'][0]
        return {'responseId':str(uuid.uuid4()),'datasetId':d['datasetId'],'issueId':e['id'],
                'issueRevision':e['issueRevision'],'expertName':'Expert','verdict':'agree',
                'reason':'Source has three branches','expectedConnection':'Add junction',
                'suggestion':'Rebuild edges'}

    def test_expert_import_idempotence_preserves_annotation_and_confirmation(self):
        d=self.save(self.initial(),confirm=True,reviewer='Reviewer');note=d['errors'][0]['note'];r=self.response(d)
        result=self.store.import_expert({'baseRevision':d['revision'],'response':r})
        self.assertEqual(result['imported'],1);d=result['document']
        self.assertEqual(d['errors'][0]['note'],note);self.assertIsNotNone(d['confirmation'])
        result=self.store.import_expert({'baseRevision':d['revision'],'response':r})
        self.assertEqual(result['duplicates'],1);self.assertEqual(len(result['document']['errors'][0]['expertResponses']),1)

    def test_wrong_dataset_or_issue_revision_is_historical(self):
        d=self.initial();r=self.response(d);r['datasetId']='another-source'
        result=self.store.import_expert({'baseRevision':d['revision'],'response':r});d=result['document']
        self.assertEqual(result['historical'],1);self.assertEqual(d['errors'][0]['expertResponses'],[])
        r=self.response(d);r['issueRevision']+=1
        result=self.store.import_expert({'baseRevision':d['revision'],'response':r})
        self.assertEqual(result['historical'],1)

    def test_remove_undo_retains_expert_evidence(self):
        d=self.initial();r=self.response(d)
        d=self.store.import_expert({'baseRevision':d['revision'],'response':r})['document']
        previous=copy.deepcopy(d['errors']);d['errors']=[];d=self.save(d)
        self.assertTrue(d['retiredIssues'])
        d['errors']=previous;d=self.save(d)
        self.assertEqual(d['errors'][0]['expertResponses'][0]['responseId'],r['responseId'])

    def test_changed_annotation_archives_old_explanation(self):
        d=self.initial();r=self.response(d)
        d=self.store.import_expert({'baseRevision':d['revision'],'response':r})['document']
        d['errors'][0]['note']='A different interpretation';d=self.save(d)
        self.assertEqual(d['errors'][0]['expertResponses'],[])
        self.assertEqual(d['historicalResponses'][0]['responseId'],r['responseId'])

    def test_backup_can_explicitly_clear_confirmation(self):
        d=self.save(self.initial(),confirm=True,reviewer='Reviewer')
        d=self.save(d,invalidateConfirmation=True)
        self.assertIsNone(d['confirmation'])

    def test_pair_complete_escaped_offline_and_version_checked(self):
        d=self.initial();e=d['errors'][0]
        building={'source_sha256':'source-hash','transform':self.store.graph['transform'],'records':[
            {'id':'ROOM1','category':'annotation','source_chain':['AB'],'source_text':'走廊','label':'Corridor','display_position':[3,4]},
            {'id':'DISTANT','category':'wall','source_chain':['CD'],'paths':[{'display_points':[[500,500],[600,600]]}]}]}
        building_file=self.root/'public/data/architecture.json';building_file.write_text(json.dumps(building),encoding='utf8')
        svg='<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><path d="M0,0L1,1"/></svg>'
        png=base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode()
        assets={f'{p}-{s}.{ext}':svg if ext=='svg' else png for p in ('cad','topology')
                for s in ('original','annotated') for ext in ('svg','png')}
        payload={'baseRevision':d['revision'],'pairs':[{'issueId':e['id'],
            'issueRevision':e['issueRevision'],'viewBox':[0,0,10,10],'assets':assets}]}
        binary=self.store.pair_zip(payload)
        with zipfile.ZipFile(io.BytesIO(binary)) as z:
            self.assertIsNone(z.testzip())
            page=z.read(next(n for n in z.namelist() if n.endswith('review.html'))).decode()
            self.assertIn('&lt;script&gt;',page);self.assertNotIn('<script> & "quote"',page)
            self.assertEqual(len([n for n in z.namelist() if n.endswith(('.png','.svg'))]),8)
            self.assertIn('expectedConnection',page)
            context=json.loads(z.read(next(n for n in z.namelist() if n.endswith('context.json'))))['buildingContext']
            self.assertEqual(len(context['records']),1);self.assertEqual(context['records'][0]['source_text'],'走廊')
            self.assertEqual(context['records'][0]['label'],'Corridor');self.assertNotIn('paths',context['records'][0])
        building['source_sha256']='wrong-version';building_file.write_text(json.dumps(building),encoding='utf8')
        with self.assertRaises(ReviewError):self.store.pair_zip(payload)
        payload['pairs'][0]['issueRevision']+=1
        with self.assertRaises(ReviewError):self.store.pair_zip(payload)

    def test_executable_svg_is_rejected(self):
        d=self.initial();e=d['errors'][0]
        assets={f'{p}-{s}.{ext}':'<svg><script>alert(1)</script></svg>' if ext=='svg'
                else base64.b64encode(b'\x89PNG\r\n\x1a\n').decode()
                for p in ('cad','topology') for s in ('original','annotated') for ext in ('svg','png')}
        with self.assertRaises(ReviewError):self.store.pair_zip({'baseRevision':d['revision'],
            'pairs':[{'issueId':e['id'],'issueRevision':e['issueRevision'],'viewBox':[0,0,1,1],'assets':assets}]})

    def test_http_origin_content_type_and_conflict(self):
        store=self.store
        class Handler(HilHandlerMixin,SimpleHTTPRequestHandler):
            review_store=store
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            doc=json.load(urlopen(origin+'/api/review',timeout=3))
            doc['errors']=[self.issue()];body=json.dumps({'baseRevision':0,'document':doc}).encode()
            for headers,status in [({'Origin':'http://untrusted.test','Content-Type':'application/json'},403),
                                   ({'Origin':origin,'Content-Type':'text/plain'},415)]:
                with self.subTest(status=status):
                    with self.assertRaises(HTTPError) as exc:urlopen(Request(origin+'/api/review',data=body,method='PUT',headers=headers),timeout=3)
                    self.assertEqual(exc.exception.code,status)
            request=Request(origin+'/api/review',data=body,method='PUT',headers={'Origin':origin,'Content-Type':'application/json'})
            self.assertEqual(json.load(urlopen(request,timeout=3))['revision'],1)
            with self.assertRaises(HTTPError) as exc:urlopen(request,timeout=3)
            self.assertEqual(exc.exception.code,409)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':unittest.main()
