#!/usr/bin/env python3
"""Serve five fixed public demo files on loopback; no API or Docker connection."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {
    '/demo/': ('demo/index.html', 'text/html; charset=utf-8'),
    '/demo/base.css': ('demo/base.css', 'text/css; charset=utf-8'),
    '/theme/netwall.css': ('theme/netwall.css', 'text/css; charset=utf-8'),
    '/theme/assets/netwall.svg': ('theme/assets/netwall.svg', 'image/svg+xml'),
    '/theme/assets/mark.svg': ('theme/assets/mark.svg', 'image/svg+xml'),
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *unused):
        pass
    def respond(self, body=True):
        port = self.server.server_address[1]
        if self.headers.get('Host') not in (f'127.0.0.1:{port}', f'localhost:{port}'):
            self.send_error(400)
            return
        entry = FILES.get(self.path)
        if entry is None:
            self.send_error(404)
            return
        path, mime = entry
        data = (ROOT / path).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        if body:
            self.wfile.write(data)
    def do_GET(self):
        self.respond()
    def do_HEAD(self):
        self.respond(False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    try:
        with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
            print(f'Fictional demo: http://127.0.0.1:{server.server_address[1]}/demo/', flush=True)
            print('Stop with Ctrl+C. No containers, app APIs or remote services are used.', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except OSError:
        raise SystemExit('Local port unavailable. Try another --port value; nothing else was started.')
