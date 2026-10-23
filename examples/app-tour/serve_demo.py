#!/usr/bin/env python3
"""Serve fixed original fictional app pages on loopback; no API or Docker connection."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {'/': ('homepage.html', 'text/html; charset=utf-8'), '/tour.css': ('tour.css', 'text/css; charset=utf-8'), '/wall.svg': ('wall.svg', 'image/svg+xml'), '/homepage.html': ('homepage.html', 'text/html; charset=utf-8'), '/ai-workbench.html': ('ai-workbench.html', 'text/html; charset=utf-8'), '/grafana.html': ('grafana.html', 'text/html; charset=utf-8'), '/identity.html': ('identity.html', 'text/html; charset=utf-8'), '/portals.html': ('portals.html', 'text/html; charset=utf-8'), '/fleet.html': ('fleet.html', 'text/html; charset=utf-8'), '/prometheus.html': ('prometheus.html', 'text/html; charset=utf-8'), '/alertmanager.html': ('alertmanager.html', 'text/html; charset=utf-8'), '/cadvisor.html': ('cadvisor.html', 'text/html; charset=utf-8'), '/git-manager.html': ('git-manager.html', 'text/html; charset=utf-8'), '/learning.html': ('learning.html', 'text/html; charset=utf-8'), '/game-connections.html': ('game-connections.html', 'text/html; charset=utf-8'), '/local-tools.html': ('local-tools.html', 'text/html; charset=utf-8')}

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
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    try:
        with ThreadingHTTPServer(('127.0.0.1', args.port), Handler) as server:
            print(f'Fictional demo: http://127.0.0.1:{server.server_address[1]}/', flush=True)
            print('Stop with Ctrl+C. No containers, app APIs or remote services are used.', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    except OSError:
        raise SystemExit('Local port unavailable. Try another --port value; nothing else was started.')
