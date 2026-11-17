"""Bounded OIDC adapter for invented issuers only; no production configuration."""
import asyncio
from dataclasses import dataclass
import hmac
import json
from pathlib import Path
import secrets
import sys
import time
from types import MappingProxyType
from urllib.parse import parse_qs, urlsplit

from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.base_client.errors import OAuthError
import httpx2 as httpx
from joserfc import jwt, jwk
from joserfc.errors import JoseError
from joserfc.jwt import JWTClaimsRegistry
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, RedirectResponse, HTMLResponse
from starlette.routing import Route

REFERENCE = Path(__file__).resolve().parents[1] / 'reference-systems'
sys.path.insert(0, str(REFERENCE))
from workspace import page, home_page, search_page, advisory_page
from state_store import StateError

SESSION = '__Host-outlands-native'
FLOW = '__Host-outlands-flow'
CLIENT = 'invented-workspace'


class LimitedStream(httpx.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        size = 0
        async for block in self.stream:
            size += len(block)
            if size > 32768:
                raise httpx.ReadError('fixture response bound')
            yield block

    async def aclose(self):
        await self.stream.aclose()


class IssuerTransport(httpx.AsyncBaseTransport):
    def __init__(self, config, inner):
        self.config, self.inner = config, inner

    async def handle_async_request(self, request):
        if str(request.url) not in {self.config.issuer + '/token', self.config.issuer + '/jwks'}:
            raise httpx.RequestError('fixture endpoint denied')
        request.headers['accept-encoding'] = 'identity'
        response = await self.inner.handle_async_request(request)
        if response.headers.get('content-encoding', 'identity') != 'identity':
            await response.aclose()
            raise httpx.ReadError('encoded response denied')
        response.stream = LimitedStream(response.stream)
        return response

    async def aclose(self):
        await self.inner.aclose()


def fixture_origin(value):
    """Prevent this teaching launcher from becoming a real identity integration."""
    u = urlsplit(value)
    if (u.scheme != 'https' or u.username or u.password or u.path or u.query or u.fragment
            or u.hostname not in {'127.0.0.1', 'localhost', 'workspace.example.invalid', 'issuer.example.invalid'}
            or value != f'https://{u.netloc}' or not u.netloc or u.netloc.endswith(':')):
        raise ValueError('invented HTTPS origin required')
    if u.port is not None and not 0 < u.port <= 65535:
        raise ValueError('port')
    return value


@dataclass(frozen=True)
class Config:
    origin: str = 'https://workspace.example.invalid'
    issuer: str = 'https://issuer.example.invalid'

    def __post_init__(self):
        fixture_origin(self.origin)
        fixture_origin(self.issuer)
        if self.origin == self.issuer:
            raise ValueError('separate issuer required')

    @property
    def callback(self):
        return self.origin + '/auth/callback'

    @property
    def roles(self):
        return MappingProxyType({(self.issuer, 'invented-owner'): 'owner',
                                 (self.issuer, 'invented-reader'): 'reader'})


def fields(raw, maximum=4):
    if len(raw) > 4096:
        raise ValueError('field bound')
    values = parse_qs(raw, strict_parsing=True, max_num_fields=maximum,
                      keep_blank_values=True, encoding='utf-8', errors='strict')
    if any(len(v) != 1 or not v[0] or len(v[0]) > 2048 for v in values.values()):
        raise ValueError('field shape')
    return {k: v[0] for k, v in values.items()}


def equal(a, b):
    return (isinstance(a, str) and isinstance(b, str) and a.isascii() and b.isascii()
            and len(a) <= 128 and len(b) <= 128 and hmac.compare_digest(a, b))


class Adapter:
    def __init__(self, config, workspace, transport=None, verify=True,
                 clock=time.monotonic, wall=time.time):
        if verify is False:
            raise ValueError('TLS verification required')
        self.config, self.workspace = config, workspace
        self.transport, self.verify = transport, verify
        self.clock, self.wall = clock, wall
        self.flows, self.sessions = {}, {}
        self.lock = asyncio.Lock()
        self.css = (REFERENCE / 'workspace.css').read_bytes()
        if len(self.css) > 32768:
            raise ValueError('stylesheet bound')

    def client(self):
        return AsyncOAuth2Client(CLIENT, redirect_uri=self.config.callback, scope='openid',
                                 token_endpoint_auth_method='none', code_challenge_method='S256',
                                 transport=IssuerTransport(self.config, self.transport or
                                                           httpx.AsyncHTTPTransport(verify=self.verify)),
                                 verify=self.verify, trust_env=False,
                                 timeout=3, follow_redirects=False)

    def prune(self):
        now = self.clock()
        for collection in (self.flows, self.sessions):
            for key in list(collection):
                if collection[key]['expires'] <= now:
                    del collection[key]

    async def begin(self):
        self.prune()
        if len(self.flows) >= 32:
            return JSONResponse({'result': 'UNAVAILABLE'}, status_code=503)
        state, binding, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(4))
        async with self.client() as client:
            url, _ = client.create_authorization_url(self.config.issuer + '/authorize',
                                                    state=state, nonce=nonce, code_verifier=verifier)
        self.flows[state] = {'binding': binding, 'nonce': nonce, 'verifier': verifier,
                             'expires': self.clock() + 300}
        response = RedirectResponse(url, status_code=303)
        response.set_cookie(FLOW, binding, max_age=300, secure=True, httponly=True,
                            samesite='lax', path='/')
        return response

    async def keyset(self, client):
        # Exact pinned fixture endpoint; no discovery, jku, redirects or user URL.
        async with client.stream('GET', self.config.issuer + '/jwks', withhold_token=True) as response:
            if response.status_code != 200:
                raise ValueError('keys unavailable')
            data = b''
            async for block in response.aiter_bytes():
                data += block
                if len(data) > 16384:
                    raise ValueError('key bound')
        value = json.loads(data)
        if (not isinstance(value, dict) or set(value) != {'keys'}
                or not isinstance(value['keys'], list) or not 1 <= len(value['keys']) <= 4):
            raise ValueError('key set')
        kids = set()
        for key in value['keys']:
            if (not isinstance(key, dict) or key.get('kty') != 'RSA' or key.get('use') != 'sig'
                    or key.get('alg') != 'RS256' or not isinstance(key.get('kid'), str)
                    or not 1 <= len(key['kid']) <= 128 or key['kid'] in kids
                    or set(key) - {'kty', 'use', 'alg', 'kid', 'n', 'e'}):
                raise ValueError('public signing key required')
            kids.add(key['kid'])
        return jwk.KeySet.import_key_set(value)

    async def finish(self, query, binding, previous):
        state = query.get('state', '')
        # Consume before network work, including failed attempts; never retry a code.
        flow = self.flows.pop(state, None)
        if (set(query) != {'state', 'code'} or not flow
                or flow['expires'] <= self.clock() or not equal(binding, flow['binding'])):
            raise ValueError('flow denied')
        async with self.client() as client:
            token = await client.fetch_token(self.config.issuer + '/token',
                                             grant_type='authorization_code', code=query['code'],
                                             code_verifier=flow['verifier'])
            encoded = token.get('id_token')
            if not isinstance(encoded, str) or len(encoded) > 8192:
                raise ValueError('token bound')
            decoded = jwt.decode(encoded, await self.keyset(client), algorithms=['RS256'])
        if set(decoded.header) != {'alg', 'kid', 'typ'} or decoded.header.get('typ') != 'JWT':
            raise ValueError('token header')
        claims = decoded.claims
        now = int(self.wall())
        JWTClaimsRegistry(now=now, leeway=0, iss={'essential': True, 'value': self.config.issuer},
                          aud={'essential': True, 'value': CLIENT},
                          sub={'essential': True}, exp={'essential': True},
                          iat={'essential': True}, nonce={'essential': True}).validate(claims)
        if (claims.get('aud') != CLIENT or ('azp' in claims and claims['azp'] != CLIENT)
                or not equal(claims.get('nonce'), flow['nonce'])
                or any(type(claims.get(k)) is not int for k in ('iat', 'exp'))
                or claims['iat'] > now or now - claims['iat'] > 300
                or not 0 < claims['exp'] - claims['iat'] <= 300
                or ('nbf' in claims and (type(claims['nbf']) is not int or claims['nbf'] > now))
                or not isinstance(claims.get('sub'), str) or len(claims['sub']) > 128):
            raise ValueError('claims denied')
        role = self.config.roles.get((claims['iss'], claims['sub']))
        if role is None or len(self.sessions) >= 32:
            raise ValueError('principal denied')
        self.sessions.pop(previous, None)
        session = secrets.token_urlsafe(32)
        self.sessions[session] = {'role': role, 'csrf': secrets.token_urlsafe(32),
                                  'expires': self.clock() + 900}
        response = RedirectResponse('/', status_code=303)
        response.set_cookie(SESSION, session, max_age=900, secure=True, httponly=True,
                            samesite='strict', path='/')
        return response

    async def body(self, request):
        if request.headers.get('content-type') != 'application/x-www-form-urlencoded':
            raise ValueError('form type')
        data = b''
        async for part in request.stream():
            data += part
            if len(data) > 512:
                raise ValueError('form bound')
        return fields(data.decode('utf-8'), 2)

    async def dispatch(self, request):
        self.prune()
        c = self.config
        raw = request.scope['headers']
        hosts = [v.decode('latin1') for k, v in raw if k == b'host']
        origins = [v.decode('latin1') for k, v in raw if k == b'origin']
        if (request.url.scheme != 'https' or hosts != [urlsplit(c.origin).netloc]
                or sum(len(k) + len(v) for k, v in raw) > 8192
                or len(request.scope.get('query_string', b'')) > 4096
                or len(request.url.path) > 128
                or len([1 for k, _ in raw if k == b'cookie']) > 1
                or len(request.headers.get('cookie', '')) > 512
                or any(k == b'transfer-encoding' for k, _ in raw)):
            return JSONResponse({'result': 'DENIED'}, status_code=403)
        path, method = request.url.path, request.method
        previous = request.cookies.get(SESSION)
        record = self.sessions.get(previous)
        if method == 'GET':
            if path == '/auth/callback':
                try:
                    response = await self.finish(fields(request.url.query), request.cookies.get(FLOW), previous)
                except (ValueError, TypeError, KeyError, UnicodeError, JoseError, OAuthError, httpx.HTTPError):
                    response = JSONResponse({'result': 'AUTH_DENIED'}, status_code=403)
                response.delete_cookie(FLOW, secure=True, httponly=True, samesite='lax', path='/')
                return response
            if origins and origins != [c.origin]:
                return JSONResponse({'result': 'DENIED'}, status_code=403)
            if path == '/auth/login' and not request.url.query:
                return await self.begin()
            if path == '/workspace.css' and not request.url.query:
                return Response(self.css, media_type='text/css')
            if path == '/' and not record:
                return HTMLResponse(page('Synthetic OIDC', '<section class="intro"><h1>Synthetic OIDC workspace</h1>'
                                         '<p>Invented issuer and users. No real identity integration.</p>'
                                         '<a href="/auth/login">Sign in with the fixture issuer</a></section>'))
            if not record:
                return JSONResponse({'result': 'DENIED'}, status_code=401)
            if path == '/session' and not request.url.query:
                return JSONResponse({'role': record['role'], 'logout_csrf': record['csrf']})
            self.workspace.ensure_available()
            if path == '/':
                query = fields(request.url.query, 1) if request.url.query else {}
                if query and (set(query) != {'notice'} or query['notice'] not in {'deleted', 'missing', 'scenario'}):
                    raise ValueError('notice')
                return HTMLResponse(home_page(self.workspace, record, query.get('notice', '')))
            if path in {'/api/summary', '/api/inventory'} and not request.url.query:
                return JSONResponse(self.workspace.summary(record['role']) if path == '/api/summary'
                                    else self.workspace.inventory_view())
            if path in {'/api/advisories', '/api/documents', '/workspace/advisories', '/private'}:
                if record['role'] != 'owner':
                    return JSONResponse({'result': 'DENIED'}, status_code=403)
                if request.url.query:
                    raise ValueError('query')
                if path == '/api/advisories':
                    return JSONResponse(self.workspace.advisory_view('owner'))
                if path == '/api/documents':
                    return JSONResponse({'source_ids': self.workspace.documents('owner')})
                if path == '/workspace/advisories':
                    return HTMLResponse(advisory_page(self.workspace, record))
                return JSONResponse({'role': 'owner', 'resource': 'fictional-owner-workspace'})
            if path in {'/search', '/api/search', '/workspace/search'}:
                query = fields(request.url.query, 1)
                if set(query) != {'q'}:
                    raise ValueError('query')
                if path == '/workspace/search':
                    return HTMLResponse(search_page(self.workspace, record, query['q']))
                return JSONResponse(self.workspace.index.search(query['q'], record['role']))
        elif method == 'POST':
            if origins != [c.origin]:
                return JSONResponse({'result': 'DENIED'}, status_code=403)
            if path == '/login':
                return JSONResponse({'result': 'PASSWORD_LOGIN_DISABLED'}, status_code=404)
            if not record:
                return JSONResponse({'result': 'DENIED'}, status_code=401)
            if path.startswith('/admin/') and record['role'] != 'owner':
                return JSONResponse({'result': 'DENIED'}, status_code=403)
            form = await self.body(request)
            if not equal(record['csrf'], form.get('csrf')):
                return JSONResponse({'result': 'DENIED'}, status_code=403)
            if path == '/logout' and set(form) == {'csrf'}:
                self.sessions.pop(previous, None)
                response = RedirectResponse('/', status_code=303)
                response.delete_cookie(SESSION, secure=True, httponly=True, samesite='strict', path='/')
                return response
            if path == '/admin/scenario' and set(form) == {'csrf', 'scenario'}:
                self.workspace.select_scenario(form['scenario'], record['role'])
                return RedirectResponse('/?notice=scenario', status_code=303)
            if path == '/admin/delete' and set(form) == {'csrf', 'source_id'}:
                existed = self.workspace.delete_document(form['source_id'], record['role'])
                return RedirectResponse('/?notice=' + ('deleted' if existed else 'missing'), status_code=303)
        return JSONResponse({'result': 'NOT_FOUND'}, status_code=404)

    async def handle(self, request: Request):
        async with self.lock:
            try:
                response = await asyncio.wait_for(self.dispatch(request), timeout=10)
            except asyncio.TimeoutError:
                response = JSONResponse({'result': 'UNAVAILABLE'}, status_code=503)
            except (StateError, OSError):
                response = JSONResponse({'result': 'STATE_UNAVAILABLE'}, status_code=503)
            except (ValueError, TypeError, UnicodeError):
                response = JSONResponse({'result': 'REVIEW'}, status_code=400)
            response.headers.update({'cache-control': 'no-store', 'x-content-type-options': 'nosniff',
                                     'content-security-policy': "default-src 'none'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
                                     'referrer-policy': 'no-referrer' if request.url.path.startswith('/auth/') else 'same-origin'})
            return response

    def app(self):
        return Starlette(debug=False, routes=[Route('/{path:path}', self.handle, methods=['GET', 'POST'])])
