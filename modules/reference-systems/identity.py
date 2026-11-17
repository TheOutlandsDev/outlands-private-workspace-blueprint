"""Loopback-only fictional identity gate and retrieval integration; not an IdP."""
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
import time
from urllib.parse import parse_qs, urlsplit

COOKIE = 'outlands_fixture_session'
DEMO_PASSWORD = 'synthetic-only'


class Sessions:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.salt = secrets.token_bytes(16)
        self.digest = self.password_digest(DEMO_PASSWORD)
        self.sessions = {}
        self.failures = 0
        self.locked_until = 0

    def password_digest(self, password):
        return hashlib.pbkdf2_hmac('sha256', password.encode(), self.salt, 600_000)

    def prune(self):
        self.sessions = {token: record for token, record in self.sessions.items()
                         if record['expires'] > self.clock()}

    def login(self, username, password, previous=None):
        self.prune()
        if self.clock() < self.locked_until:
            return None
        if (not isinstance(username, str) or not isinstance(password, str)
                or len(username) > 64 or len(password) > 128):
            return None
        correct = hmac.compare_digest(self.digest, self.password_digest(password))
        role = {'fictional-owner': 'owner', 'fictional-reader': 'reader'}.get(username)
        if not correct or not role:
            self.failures += 1
            if self.failures >= 5:
                self.locked_until = self.clock() + 60
                self.failures = 0
            return None
        self.failures = 0
        if len(self.sessions) >= 32:
            return None
        self.sessions.pop(previous, None)
        token = secrets.token_urlsafe(32)
        self.sessions[token] = {'role': role, 'expires': self.clock() + 900,
                                'csrf': secrets.token_urlsafe(32)}
        return token

    def principal(self, token):
        self.prune()
        if not isinstance(token, str) or len(token) > 128:
            return None
        record = self.sessions.get(token)
        return dict(record) if record else None

    def logout(self, token, csrf):
        record = self.principal(token)
        if not record or not isinstance(csrf, str) or not hmac.compare_digest(record['csrf'], csrf):
            return False
        self.sessions.pop(token, None)
        return True


def make_server(index, port=0):
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('port')
    sessions = Sessions()

    class Handler(BaseHTTPRequestHandler):
        # Deliberately single-threaded fixture; requests and session state serialize.
        def setup(self):
            super().setup()
            self.connection.settimeout(3)

        def log_message(self, *_args):
            pass

        def version_string(self):
            return 'OUTLANDS-fixture'

        def send_error(self, *_args, **_kwargs):
            self.respond(400, {'result': 'DENIED'})

        def respond(self, status, body, cookie=None, html=False, location=None):
            data = body.encode() if html else json.dumps(body, sort_keys=True).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'text/html; charset=utf-8' if html else 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header('Referrer-Policy', 'no-referrer')
            if location is not None:
                self.send_header('Location', location)
            if cookie is not None:
                self.send_header('Set-Cookie', f'{COOKIE}={cookie}; HttpOnly; SameSite=Strict; Path=/; Max-Age={900 if cookie else 0}')
            self.end_headers()
            self.wfile.write(data)

        def trusted_request(self, post=False):
            origin = f'http://127.0.0.1:{self.server.server_port}'
            return (len(self.path) <= 1024
                    and self.headers.get_all('Host', []) == [origin[7:]]
                    and not self.headers.get('Transfer-Encoding')
                    and (self.headers.get_all('Origin', []) == [origin] if post else
                         self.headers.get('Origin', origin) == origin))

        def session_token(self):
            value = self.headers.get('Cookie', '')
            if len(value) > 512 or len(self.headers.get_all('Cookie', [])) > 1:
                return None
            try:
                jar = SimpleCookie()
                jar.load(value)
                return jar[COOKIE].value if COOKIE in jar else None
            except CookieError:
                return None

        def do_GET(self):
            if not self.trusted_request():
                return self.respond(403, {'result': 'DENIED'})
            target = urlsplit(self.path)
            record = sessions.principal(self.session_token())
            if target.path == '/' and not target.query:
                if record:
                    return self.respond(200, '<!doctype html><html lang="en"><title>Fictional workspace</title>'
                                        '<h1>OUTLANDS fictional workspace</h1>'
                                        f'<p>Signed in with the {record["role"]} fixture role.</p>'
                                        '<p><a href="/private">Owner-only workspace</a></p>'
                                        '<p><a href="/search?q=recovery">Search for recovery</a></p>'
                                        '<p><a href="/search?q=lamp">Search for lamp</a></p>'
                                        '<form method="post" action="/logout">'
                                        f'<input type="hidden" name="csrf" value="{record["csrf"]}">'
                                        '<button>Sign out</button></form></html>', html=True)
                return self.respond(200, '<!doctype html><html lang="en"><title>Fictional identity gate</title>'
                                    '<h1>OUTLANDS fictional identity gate</h1>'
                                    '<p>Loopback teaching fixture. Use fictional-owner or fictional-reader; password: synthetic-only.</p>'
                                    '<form method="post" action="/login"><label>User <input name="username" autocomplete="off"></label>'
                                    '<label>Password <input name="password" type="password" autocomplete="off"></label>'
                                    '<button>Sign in</button></form></html>', html=True)
            if not record:
                return self.respond(401, {'result': 'DENIED'})
            if target.path == '/private' and not target.query:
                if record['role'] != 'owner':
                    return self.respond(403, {'result': 'DENIED'})
                return self.respond(200, {'resource': 'fictional-owner-workspace', 'role': record['role'],
                                         'logout_csrf': record['csrf']})
            if target.path == '/session' and not target.query:
                return self.respond(200, {'role': record['role'], 'logout_csrf': record['csrf']})
            if target.path == '/search':
                try:
                    query = parse_qs(target.query, strict_parsing=True, max_num_fields=1)
                    if set(query) != {'q'} or len(query['q']) != 1:
                        raise ValueError('query')
                    return self.respond(200, index.search(query['q'][0], record['role']))
                except ValueError:
                    return self.respond(400, {'result': 'REVIEW'})
            return self.respond(404, {'result': 'NOT_FOUND'})

        def do_POST(self):
            if not self.trusted_request(post=True):
                return self.respond(403, {'result': 'DENIED'})
            try:
                lengths = self.headers.get_all('Content-Length', [])
                if (len(lengths) != 1 or not lengths[0].isdigit() or not 0 < int(lengths[0]) <= 512
                        or self.headers.get('Content-Type') != 'application/x-www-form-urlencoded'):
                    raise ValueError('body bound')
                data = self.rfile.read(int(lengths[0])).decode('utf-8')
                fields = parse_qs(data, strict_parsing=True, max_num_fields=2)
                if any(len(v) != 1 for v in fields.values()):
                    raise ValueError('duplicate field')
                if self.path == '/login' and set(fields) == {'username', 'password'}:
                    token = sessions.login(fields['username'][0], fields['password'][0], self.session_token())
                    if token:
                        return self.respond(303, {'result': 'SIGNED_IN'}, cookie=token, location='/')
                    return self.respond(403, {'result': 'DENIED'})
                if self.path == '/logout' and set(fields) == {'csrf'}:
                    if sessions.logout(self.session_token(), fields['csrf'][0]):
                        return self.respond(303, {'result': 'SIGNED_OUT'}, cookie='', location='/')
                    return self.respond(403, {'result': 'DENIED'})
            except (ValueError, UnicodeError):
                return self.respond(400, {'result': 'REVIEW'})
            return self.respond(400, {'result': 'REVIEW'})

    server = HTTPServer(('127.0.0.1', port), Handler)
    server.fixture_sessions = sessions
    return server
