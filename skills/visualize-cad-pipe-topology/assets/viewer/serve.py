"""Serve a generated CAD viewer on loopback; reuse only this exact bundle."""
import argparse
import json
import socket
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.request import urlopen
from hil_server import HilHandlerMixin, ReviewStore

ROOT = Path(__file__).resolve().parent / 'public'

def main():
    manifest = json.loads((ROOT/'data/manifest.json').read_text(encoding='utf8'))
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=manifest['preferredPort'])
    parser.add_argument('--strict-port', action='store_true')
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535')
    marker = f'name="cad-viewer-build" content="{manifest["bundleId"]}"'
    for port in range(args.port, min(65536, args.port + (1 if args.strict_port else 30))):
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=.2):
                pass
        except OSError:
            break
        try:
            existing = urlopen(f'http://127.0.0.1:{port}', timeout=1).read().decode('utf8')
        except Exception:
            existing = ''
        if marker in existing:
            url = f'http://127.0.0.1:{port}'
            print(f'This viewer is already running: {url}', flush=True)
            if args.open:
                webbrowser.open(url)
            return
    else:
        raise SystemExit('Preferred port is occupied. Choose another --port.')
    store = ReviewStore(Path(__file__).resolve().parent)
    class Handler(HilHandlerMixin, SimpleHTTPRequestHandler):
        review_store = store
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT), **kw)
        def end_headers(self):
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            super().end_headers()
    class Server(ThreadingHTTPServer):
        allow_reuse_address = False
        def server_bind(self):
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            super().server_bind()
    server = Server(('127.0.0.1', port), Handler)
    url = f'http://127.0.0.1:{port}'
    print(f'{manifest["projectId"]} Pipe Topology: {url}', flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == '__main__':
    main()
