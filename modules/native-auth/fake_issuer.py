"""One-use PKCE issuer for tests. Invented identities; ephemeral library keys."""
import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode

from joserfc import jwt, jwk
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from native_auth import CLIENT, equal, fields


class FakeIssuer:
    def __init__(self, config, clock=time.monotonic, wall=time.time):
        self.config, self.clock, self.wall = config, clock, wall
        self.key = jwk.RSAKey.generate_key(2048, {'kid': 'invented-signing-key', 'use': 'sig', 'alg': 'RS256'})
        self.subject = 'invented-owner'
        self.fault = None
        self.codes = {}

    async def keys(self, request):
        if self.fault == 'keys-outage':
            return JSONResponse({'result': 'UNAVAILABLE'}, status_code=503)
        return JSONResponse({'keys': [self.key.as_dict(private=False)]})

    async def authorize(self, request):
        try:
            q = fields(request.url.query, 10)
            expected = {'response_type', 'client_id', 'redirect_uri', 'scope', 'state', 'nonce',
                        'code_challenge', 'code_challenge_method'}
            if (set(q) != expected or q['response_type'] != 'code' or q['client_id'] != CLIENT
                    or q['redirect_uri'] != self.config.callback or q['scope'] != 'openid'
                    or q['code_challenge_method'] != 'S256' or len(q['code_challenge']) != 43):
                raise ValueError('authorize')
            self.codes = {k: v for k, v in self.codes.items() if v['expires'] > self.clock()}
            if len(self.codes) >= 32:
                raise ValueError('codes')
            code = secrets.token_urlsafe(32)
            self.codes[code] = dict(q, expires=self.clock() + 60, subject=self.subject)
            return RedirectResponse(self.config.callback + '?' + urlencode({'code': code, 'state': q['state']}), status_code=303)
        except (ValueError, UnicodeError):
            return JSONResponse({'error': 'invalid_request'}, status_code=400)

    async def token(self, request):
        try:
            data = b''
            async for part in request.stream():
                data += part
                if len(data) > 4096:
                    raise ValueError('body bound')
            q = fields(data.decode(), 6)
            if set(q) != {'grant_type', 'code', 'redirect_uri', 'client_id', 'code_verifier'}:
                raise ValueError('token')
            code = self.codes.pop(q['code'], None)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(q['code_verifier'].encode()).digest()).rstrip(b'=').decode()
            if (not code or code['expires'] <= self.clock() or q['client_id'] != CLIENT
                    or q['grant_type'] != 'authorization_code' or q['redirect_uri'] != self.config.callback
                    or not equal(challenge, code['code_challenge'])):
                raise ValueError('code denied')
            if self.fault == 'outage':
                return JSONResponse({'error': 'temporarily_unavailable'}, status_code=503)
            now = int(self.wall())
            claims = {'iss': self.config.issuer, 'sub': code['subject'], 'aud': CLIENT,
                      'iat': now, 'exp': now + 120, 'nonce': code['nonce']}
            overrides = {'issuer': ('iss', 'https://other.example.invalid'), 'audience': ('aud', 'other-client'),
                         'expired': ('exp', now - 1), 'future': ('iat', now + 60),
                         'nonce': ('nonce', 'wrong-nonce'), 'azp': ('azp', 'other-client'),
                         'nbf': ('nbf', now + 60), 'boolean-time': ('iat', True),
                         'long-life': ('exp', now + 3600), 'array-audience': ('aud', [CLIENT, 'other'])}
            if self.fault in overrides:
                k, v = overrides[self.fault]
                claims[k] = v
            if self.fault == 'role-claim':
                claims.update(role='owner', groups=['owner'], email='owner@example.invalid')
            if self.fault and self.fault.startswith('missing-'):
                claims.pop(self.fault[8:], None)
            key = jwk.RSAKey.generate_key(2048) if self.fault == 'signature' else self.key
            header = {'alg': 'RS256', 'kid': 'unknown' if self.fault == 'kid' else 'invented-signing-key', 'typ': 'JWT'}
            if self.fault == 'jku':
                header['jku'] = 'https://other.example.invalid/jwks'
            if self.fault == 'algorithm':
                header['alg'] = 'RS512'
            encoded = jwt.encode(header, claims, key, algorithms=['RS256', 'RS512'])
            return JSONResponse({'token_type': 'Bearer', 'access_token': secrets.token_urlsafe(24),
                                 'expires_in': 120, 'id_token': encoded})
        except (ValueError, UnicodeError):
            return JSONResponse({'error': 'invalid_grant'}, status_code=400)

    def app(self):
        return Starlette(debug=False, routes=[Route('/authorize', self.authorize),
                                             Route('/token', self.token, methods=['POST']),
                                             Route('/jwks', self.keys)])
