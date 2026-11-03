"""Local, versioned HIL review storage and portable expert pairs. Standard library only."""
from __future__ import annotations
import base64
import copy
from datetime import datetime, timezone
import hashlib
import html
import io
import json
import math
import os
from pathlib import Path
import re
import threading
import uuid
import zipfile
import xml.etree.ElementTree as ET


def now():
    return datetime.now(timezone.utc).isoformat()


class ReviewError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def identity(manifest):
    hashes = manifest['sourceHashes']
    payload = {'project': manifest['projectId'], 'sources': {
        k: hashes.get(k) for k in ('graph', 'devices', 'ports', 'main_dxf', 'legend_dxf')
    }}
    # Legacy identity is unchanged without explicit semantic content. UI/template
    # hashes are deliberately excluded; new content never inherits confirmation.
    if manifest.get('reviewContentHashes'):
        payload['reviewContentHashes'] = manifest['reviewContentHashes']
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def signature(errors):
    return json.dumps(sorted([
        (e['id'], sorted(e['nodes']), sorted(e['edges']), e['region'], bool(e.get('closed')))
        for e in errors
    ]), sort_keys=True)


def safe_text(value, maximum=20000):
    if not isinstance(value, str) or len(value) > maximum:
        raise ReviewError('Invalid or oversized text')
    return value


class ReviewStore:
    def __init__(self, root):
        self.root = Path(root)
        self.manifest = json.loads((self.root/'public/data/manifest.json').read_text(encoding='utf8'))
        self.graph = json.loads((self.root/'public/data/graph.json').read_text(encoding='utf8'))
        self.dataset = identity(self.manifest)
        self.folder = self.root/'annotations'/self.dataset
        self.lock = threading.RLock()
        self.node_ids = {n['node_id'] for n in self.graph['nodes']}
        self.edge_ids = {e['edge_id'] for e in self.graph['edges']}

    def read(self):
        path = self.folder/'review.json'
        if path.exists():
            return json.loads(path.read_text(encoding='utf8'))
        return {'schemaVersion': 1, 'datasetId': self.dataset, 'revision': 0,
                'errors': [], 'confirmation': None, 'historicalResponses': [], 'retiredIssues': {}, 'updatedAt': None}

    def validate(self, doc, current):
        if doc.get('datasetId') != self.dataset:
            raise ReviewError('Dataset differs; import as historical evidence instead', 409)
        errors = doc.get('errors')
        if not isinstance(errors, list) or len(errors) > 10000:
            raise ReviewError('Invalid error list')
        ids = set()
        prior = dict(current.get('retiredIssues', {}))
        prior.update({e['id']: e for e in current['errors']})
        clean = []
        for value in errors:
            e = copy.deepcopy(value)
            key = e.get('id', '')
            if not re.fullmatch(r'[a-zA-Z0-9-]{8,80}', key) or key in ids:
                raise ReviewError('Invalid or duplicate issue ID')
            ids.add(key)
            if not isinstance(e.get('nodes'), list) or not isinstance(e.get('edges'), list):
                raise ReviewError('Choose nodes or edges, or draw a region')
            if set(e['nodes'])-self.node_ids or set(e['edges'])-self.edge_ids:
                raise ReviewError('Issue references objects outside this dataset')
            e['nodes'] = sorted(set(e['nodes']))
            e['edges'] = sorted(set(e['edges']))
            box = e.get('region')
            if not isinstance(box, list) or len(box) != 4 or any(
                not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in box
            ) or box[2] <= 0 or box[3] <= 0:
                raise ReviewError('Invalid issue region')
            e['note'] = safe_text(e.get('note', ''))
            e['author'] = safe_text(e.get('author', ''), 200)
            e['closed'] = bool(e.get('closed'))
            e['closureNote'] = safe_text(e.get('closureNote', ''))
            if e['closed'] and not e['closureNote'].strip():
                raise ReviewError('Closing an issue requires a conclusion')
            old = prior.get(key)
            changed = not old or any(e.get(k) != old.get(k) for k in
                                    ('nodes', 'edges', 'region', 'note', 'closed', 'closureNote'))
            e['issueRevision'] = (old.get('issueRevision', 1) + int(changed)) if old else 1
            e['createdAt'] = old['createdAt'] if old else now()
            e['updatedAt'] = now() if changed else old['updatedAt']
            e['label'] = old['label'] if old else 'ERR-'+key[:6].upper()
            # Expert content can only be added through the checked import API.
            e['expertResponses'] = copy.deepcopy(old.get('expertResponses', [])) if old else []
            t = self.graph['transform']
            x, y, w, h = box
            e['sourceBounds'] = [t['originX']+x*t['scale'], t['originY']-(y+h)*t['scale'],
                                 w*t['scale'], h*t['scale']]
            clean.append(e)
        return clean

    def persist(self, doc):
        self.folder.mkdir(parents=True, exist_ok=True)
        history = self.folder/'history'
        history.mkdir(exist_ok=True)
        content = json.dumps(doc, ensure_ascii=False, indent=2)+'\n'
        # Archive full revisions before swapping current; both writes use atomic rename.
        for dest in (history/f"{doc['revision']:08d}.json", self.folder/'review.json'):
            tmp = dest.with_name(dest.name+'.'+uuid.uuid4().hex+'.tmp')
            with tmp.open('w', encoding='utf8') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, dest)
        return doc

    def save(self, payload):
        with self.lock:
            current = self.read()
            if payload.get('baseRevision') != current['revision']:
                raise ReviewError('Review changed in another window. Export your edits, then reload.', 409)
            result = copy.deepcopy(current)
            result['errors'] = self.validate(payload.get('document', {}), current)
            active_ids = {e['id'] for e in result['errors']}
            result.setdefault('retiredIssues', {}).update({e['id']: e for e in current['errors'] if e['id'] not in active_ids})
            for e in result['errors']:
                for response in e['expertResponses'][:]:
                    if response['issueRevision'] != e['issueRevision']:
                        old_response = copy.deepcopy(response)
                        old_response['historicalReason'] = 'Issue annotation or selection changed after this explanation'
                        result['historicalResponses'].append(old_response)
                        e['expertResponses'].remove(response)
            if signature(result['errors']) != signature(current['errors']) or payload.get('invalidateConfirmation'):
                result['confirmation'] = None
            if payload.get('confirm')and self.graph.get('metadata',{}).get('hil_ready')is False:
                raise ReviewError('Source comparison unresolved; HIL confirmation is blocked',409)
            if payload.get('confirm'):
                author = safe_text(payload.get('reviewer', ''), 200).strip()
                if not author:
                    raise ReviewError('Enter a reviewer name')
                result['confirmation'] = {'reviewer': author, 'confirmedAt': now(),
                    'datasetId': self.dataset, 'scope': 'entire_dataset',
                    'errorIds': [e['id'] for e in result['errors'] if not e['closed']],
                    'statement': 'All items other than the marked errors have been reviewed and confirmed.'}
            result['revision'] = current['revision']+1
            result['updatedAt'] = now()
            return self.persist(result)

    def import_expert(self, payload):
        with self.lock:
            doc = self.read()
            if payload.get('baseRevision') != doc['revision']:
                raise ReviewError('Review changed; reload before importing', 409)
            raw = payload.get('response')
            responses = raw.get('responses', [raw]) if isinstance(raw, dict) else raw
            if not isinstance(responses, list) or len(responses) > 1000:
                raise ReviewError('Invalid expert response format')
            known = {r['responseId'] for e in doc['errors'] for r in e.get('expertResponses', [])}
            known.update(r['responseId'] for r in doc['historicalResponses'])
            known.update(r['responseId'] for e in doc.get('retiredIssues', {}).values() for r in e.get('expertResponses', []))
            added = historical = duplicate = 0
            for raw_response in responses:
                if not isinstance(raw_response, dict):
                    raise ReviewError('Invalid expert response')
                r = {k: safe_text(raw_response.get(k, ''), 20000) for k in
                     ('responseId', 'datasetId', 'issueId', 'expertName', 'verdict', 'reason',
                      'expectedConnection', 'suggestion')}
                if not r['responseId'] or not r['datasetId'] or not r['issueId']:
                    raise ReviewError('Expert response needs responseId, datasetId and issueId')
                r['issueRevision'] = raw_response.get('issueRevision')
                if not isinstance(r['issueRevision'], int):
                    raise ReviewError('Expert response needs issueRevision')
                if r['responseId'] in known:
                    duplicate += 1
                    continue
                known.add(r['responseId'])
                r['importedAt'] = now()
                e = next((x for x in doc['errors'] if x['id'] == r['issueId']), None)
                if r['datasetId'] != self.dataset or not e or e['issueRevision'] != r['issueRevision']:
                    r['historicalReason'] = 'Dataset, issue or issue revision differs; not applied'
                    doc['historicalResponses'].append(r)
                    historical += 1
                else:
                    e.setdefault('expertResponses', []).append(r)
                    added += 1
            if added or historical:
                doc['revision'] += 1
                doc['updatedAt'] = now()
                self.persist(doc)
            return {'document': doc, 'imported': added, 'historical': historical, 'duplicates': duplicate}

    def pair_zip(self, payload):
        with self.lock:
            doc = self.read()
            if payload.get('baseRevision') != doc['revision']:
                raise ReviewError('Review changed; rebuild the pair preview', 409)
            pairs = payload.get('pairs', [])
            if not isinstance(pairs, list) or not pairs:
                raise ReviewError('Choose at least one issue')
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
                for item in pairs:
                    issue = next((e for e in doc['errors'] if e['id'] == item.get('issueId')), None)
                    if not issue or item.get('issueRevision') != issue['issueRevision']:
                        raise ReviewError('Issue revision changed', 409)
                    view = item.get('viewBox')
                    if not isinstance(view, list) or len(view) != 4 or any(
                        not isinstance(x, (float, int)) or not math.isfinite(x) for x in view
                    ) or min(view[2:]) <= 0:
                        raise ReviewError('Invalid pair bounds')
                    prefix = issue['label']+'-'+issue['id'][:8]+'/'
                    assets = item.get('assets', {})
                    expected = {f'{pane}-{state}.{ext}' for pane in ('cad','topology')
                                for state in ('original','annotated') for ext in ('svg','png')}
                    if set(assets) != expected:
                        raise ReviewError('Pair requires original/annotated SVG and PNG for both panes')
                    for name, content in assets.items():
                        if name.endswith('.png'):
                            try:
                                binary = base64.b64decode(content, validate=True)
                            except Exception as exc:
                                raise ReviewError('Invalid PNG encoding') from exc
                            if not binary.startswith(b'\x89PNG\r\n\x1a\n'):
                                raise ReviewError('Invalid PNG file')
                        else:
                            try:
                                element = ET.fromstring(content)
                            except ET.ParseError as exc:
                                raise ReviewError('Invalid pair SVG') from exc
                            for el in element.iter():
                                if el.tag.split('}')[-1] in ('script','foreignObject','image') or any(
                                    k.lower().startswith('on') or (k.endswith('href') and not v.startswith('#'))
                                    for k,v in el.attrib.items()
                                ):
                                    raise ReviewError('External or executable pair SVG content')
                            binary = content.encode('utf8')
                        z.writestr(prefix+name, binary)
                    edge_ids = set(issue['edges'])
                    node_ids = set(issue['nodes'])
                    by_edge = {e['edge_id']:e for e in self.graph['edges']}
                    for key in edge_ids:
                        node_ids.update((by_edge[key]['start_node_id'], by_edge[key]['end_node_id']))
                    context_edges = [e for e in self.graph['edges'] if e['edge_id'] in edge_ids or
                                     e['start_node_id'] in node_ids or e['end_node_id'] in node_ids]
                    context_nodes = node_ids | {key for e in context_edges for key in
                                                (e['start_node_id'],e['end_node_id'])}
                    meta = {'schemaVersion':1, 'datasetId':self.dataset, 'issue':issue,
                        'bundleId':self.manifest['bundleId'], 'sourceHashes':self.manifest['sourceHashes'],
                        'transform':self.graph['transform'], 'viewBox':view,
                        'scope':'local source vector export, not native DXF',
                        'reviewConfirmation':doc['confirmation'], 'exportedAt':now(),
                        'sourceEntities':item.get('sourceEntities', [])}
                    context = {'nodes':[n for n in self.graph['nodes'] if n['node_id'] in context_nodes],
                        'edges':context_edges, 'instances':[d for d in self.graph['instances'] if
                                                        d['edge_id'] in {e['edge_id'] for e in context_edges}]}
                    local_pending=[]
                    for obj in self.graph.get('pendingSourceObjects',[]):
                        points=[p for path in obj.get('sourceGeometry',[])for p in path['points']]
                        if points and min(p[0]for p in points)<=view[0]+view[2] and max(p[0]for p in points)>=view[0] and min(p[1]for p in points)<=view[1]+view[3] and max(p[1]for p in points)>=view[1]:local_pending.append(obj)
                    if local_pending:context['pendingSourceObjects']=local_pending
                    building_file = self.root/'public/data/architecture.json'
                    if building_file.is_file():
                        building = json.loads(building_file.read_text(encoding='utf8'))
                        if building['source_sha256'] != self.manifest['sourceHashes']['main_dxf'] or building['transform'] != self.graph['transform']:
                            raise ReviewError('Building context source version or coordinate transform mismatch')
                        local = []
                        for record in building['records']:
                            points = ([record['display_position']] if record.get('display_position') else
                                      [p for path in record.get('paths',[]) for p in path['display_points']])
                            if record.get('display_text_bounds'):
                                x,y,w,h=record['display_text_bounds'];points=[(x,y),(x+w,y+h)]
                            if not points: continue
                            xs,ys = zip(*points)
                            if min(xs)>view[0]+view[2] or max(xs)<view[0] or min(ys)>view[1]+view[3] or max(ys)<view[1]: continue
                            local.append({k:record[k] for k in ('id','category','source_chain','source_layer','source_text','label','label_status','semantic_type') if k in record})
                        context['buildingContext'] = {'source_sha256':building['source_sha256'],'records':local,
                            'scope':'Local source references and English aliases; no full-building geometry or inferred room polygons'}
                    z.writestr(prefix+'issue.json', json.dumps(meta,ensure_ascii=False,indent=2))
                    z.writestr(prefix+'context.json', json.dumps(context,ensure_ascii=False,indent=2))
                    z.writestr(prefix+'review.html', expert_html(meta))
                    z.writestr(prefix+'expert-response-template.json', json.dumps({
                        'responseId':str(uuid.uuid4()),'datasetId':self.dataset,'issueId':issue['id'],
                        'issueRevision':issue['issueRevision'],'expertName':'','verdict':'',
                        'reason':'','expectedConnection':'','suggestion':''},indent=2))
                z.writestr('README.txt', 'Open each issue folder/review.html offline. Fill the expert form and export JSON.\n'
                    'Original annotations are preserved separately. Import expert JSON in the local HIL viewer.\n'
                    'These are local DXF-derived vectors; building labels use English aliases. No native DXF is included.\n')
            return buffer.getvalue()


def expert_html(meta):
    e = meta['issue']
    data = json.dumps({'datasetId':meta['datasetId'],'issueId':e['id'],
                       'issueRevision':e['issueRevision']},ensure_ascii=True).replace('<','\\u003c')
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Expert pair review</title>
<style>body{font:16px system-ui;margin:24px;color:#24344d}section{display:grid;grid-template-columns:1fr 1fr;gap:16px}img{width:100%;border:1px solid #ddd}textarea,input,select{display:block;width:95%;padding:10px;margin:8px 0 18px}textarea{min-height:80px}pre{white-space:pre-wrap}button{padding:12px 24px}small{color:#63778f}</style>
<h1>'''+html.escape(e['label'])+''' · Expert review</h1><h2>Original annotation</h2><pre>'''+html.escape(e['note'] or '(No explanation provided)')+'''</pre>
<small>Local source vectors; English building aliases; originals in context.json. Drawing units; no inferred flow.</small>
<section><div><h2>Topology</h2><img src="topology-annotated.png"><a href="topology-original.svg">Original vectors</a></div><div><h2>CAD</h2><img src="cad-annotated.png"><a href="cad-original.svg">Original vectors</a></div></section>
<h2>Expert explanation</h2><label>Expert name<input id="expertName"></label><label>Judgment<select id="verdict"><option value="">Choose judgment</option><option value="agree">Issue confirmed</option><option value="disagree">Issue not confirmed</option><option value="uncertain">Insufficient evidence</option></select></label>
<label>Cause / explanation<textarea id="reason"></textarea></label><label>Expected connection<textarea id="expectedConnection"></textarea></label><label>Suggested correction<textarea id="suggestion"></textarea></label><button id="save">Download explanation JSON</button><p id="status"></p>
<script>const meta='''+data+''';const fields=['expertName','verdict','reason','expectedConnection','suggestion'];
const key='expert:'+meta.datasetId+':'+meta.issueId+':'+meta.issueRevision;
try{const cached=JSON.parse(localStorage.getItem(key)||'{}');fields.forEach(k=>document.getElementById(k).value=cached[k]||'')}catch{}
fields.forEach(k=>document.getElementById(k).oninput=()=>{try{localStorage.setItem(key,JSON.stringify(Object.fromEntries(fields.map(k=>[k,document.getElementById(k).value]))))}catch{}});
document.getElementById('save').onclick=()=>{const r={...meta,responseId:globalThis.crypto?.randomUUID?.()||('expert-'+Date.now()+'-'+Math.random().toString(16).slice(2)),...Object.fromEntries(fields.map(k=>[k,document.getElementById(k).value]))};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(r,null,2)],{type:'application/json'}));a.download='expert-response-'+meta.issueId+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);document.getElementById('status').textContent='Downloaded. Import this JSON into the HIL viewer. Original annotation was not changed.'};</script></html>'''


class HilHandlerMixin:
    review_store: ReviewStore

    def json_reply(self, status, value):
        body = json.dumps(value,ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/review':
            with self.review_store.lock:
                return self.json_reply(200,self.review_store.read())
        return super().do_GET()

    def mutation(self):
        try:
            host = self.headers.get('Host','')
            if not re.fullmatch(r'(127\.0\.0\.1|localhost):\d+',host) or self.headers.get('Origin') != 'http://'+host:
                raise ReviewError('Local same-origin requests only',403)
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                raise ReviewError('JSON requests only',415)
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 64*1024*1024:
                raise ReviewError('Request is empty or exceeds 64 MiB',413)
            payload = json.loads(self.rfile.read(length))
            if self.path == '/api/review' and self.command == 'PUT':
                return self.json_reply(200,self.review_store.save(payload))
            if self.path == '/api/expert' and self.command == 'POST':
                return self.json_reply(200,self.review_store.import_expert(payload))
            if self.path == '/api/pairs' and self.command == 'POST':
                body = self.review_store.pair_zip(payload)
                self.send_response(200)
                self.send_header('Content-Type','application/zip')
                self.send_header('Content-Disposition','attachment; filename="expert-pairs.zip"')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            raise ReviewError('Unknown API route',404)
        except ReviewError as exc:
            self.json_reply(exc.status,{'error':str(exc)})
        except (ValueError,KeyError,TypeError) as exc:
            self.json_reply(400,{'error':str(exc)})
        except OSError:
            self.json_reply(500,{'error':'Could not save local files. Your edits remain in the browser; export a backup.'})

    do_PUT = mutation
    do_POST = mutation
