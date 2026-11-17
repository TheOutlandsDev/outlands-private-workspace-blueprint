import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import httpx2 as httpx
from native_auth import Adapter, Config, SESSION, FLOW, CLIENT
from fake_issuer import FakeIssuer
from run import workspace_fixture, workspace_persistent, seed_state
from state_store import StateStore, StateError
from run_native import rehearsal


class AuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = [100.0]
        self.config = Config()
        self.issuer = FakeIssuer(self.config, clock=lambda: self.now[0])
        self.adapter = Adapter(self.config, workspace_fixture(),
                               httpx.ASGITransport(app=self.issuer.app()), clock=lambda: self.now[0])
        self.browser = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.adapter.app()),
                                        base_url=self.config.origin, trust_env=False)
        self.idp = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.issuer.app()), trust_env=False)
        self.addAsyncCleanup(self.browser.aclose)
        self.addAsyncCleanup(self.idp.aclose)

    async def pending(self):
        response = await self.browser.get('/auth/login')
        self.assertEqual(response.status_code, 303)
        params = parse_qs(urlsplit(response.headers['location']).query)
        self.assertEqual(params['code_challenge_method'], ['S256'])
        self.assertNotIn('code_verifier', params)
        response = await self.idp.get(response.headers['location'])
        self.assertEqual(response.status_code, 303)
        return response.headers['location']

    async def sign_in(self, role='owner'):
        self.issuer.subject = 'invented-' + role
        response = await self.browser.get(await self.pending())
        self.assertEqual(response.status_code, 303)
        return response

    async def session(self):
        return (await self.browser.get('/session')).json()

    async def post(self, path, data, origin=True):
        return await self.browser.post(path, data=data,
            headers={'origin': self.config.origin} if origin else {})

    async def test_owner_code_flow_and_cookie_attributes(self):
        response = await self.sign_in()
        self.assertEqual((await self.session())['role'], 'owner')
        cookie = response.headers.get_list('set-cookie')[0]
        for flag in ['Secure', 'HttpOnly', 'SameSite=strict', 'Path=/']:
            self.assertIn(flag, cookie)
        self.assertNotIn('Domain=', cookie)
        self.assertEqual((await self.browser.get('/api/advisories')).status_code, 200)
        self.assertEqual((await self.browser.get('/api/search?q=recovery')).json()['results'][0]['source_id'], 'fictional-owner-note')

    async def test_reader_endpoint_matrix_and_filtering(self):
        await self.sign_in('reader')
        for path in ['/api/advisories', '/api/documents', '/workspace/advisories', '/private']:
            self.assertEqual((await self.browser.get(path)).status_code, 403, path)
        for path in ['/api/summary', '/api/inventory', '/', '/workspace/search?q=lamp']:
            self.assertEqual((await self.browser.get(path)).status_code, 200, path)
        self.assertEqual((await self.browser.get('/api/search?q=recovery')).json()['results'], [])
        for path in ['/admin/delete', '/admin/scenario']:
            self.assertEqual((await self.post(path, {'csrf': (await self.session())['logout_csrf']})).status_code, 403)

    async def test_password_login_disabled_and_no_fallback(self):
        response = await self.post('/login', {'username': 'fictional-owner', 'password': 'synthetic-only'})
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('password', (await self.browser.get('/')).text.lower())
        self.assertEqual((await self.browser.get('/api/summary')).status_code, 401)

    async def test_unknown_subject_never_grants_access(self):
        self.issuer.subject = 'not-allowed'
        self.assertEqual((await self.browser.get(await self.pending())).status_code, 403)
        self.assertFalse(self.adapter.sessions)

    async def test_untrusted_role_group_email_claims_cannot_escalate(self):
        self.issuer.fault = 'role-claim'
        await self.sign_in('reader')
        self.assertEqual((await self.session())['role'], 'reader')
        self.assertEqual((await self.browser.get('/api/advisories')).status_code, 403)

    async def test_code_expires_before_flow(self):
        url = await self.pending()
        self.now[0] += 61
        self.assertEqual((await self.browser.get(url)).status_code, 403)
        self.assertFalse(self.adapter.sessions)

    async def test_invalid_tokens_and_provider_failures_denied(self):
        faults = ['issuer', 'audience', 'expired', 'future', 'nonce', 'azp', 'nbf', 'boolean-time',
                  'long-life', 'array-audience', 'signature', 'kid', 'jku', 'algorithm',
                  'missing-iss', 'missing-sub', 'missing-aud', 'missing-exp', 'missing-iat',
                  'missing-nonce', 'outage', 'keys-outage']
        for fault in faults:
            with self.subTest(fault=fault):
                self.issuer.fault = fault
                response = await self.browser.get(await self.pending())
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {'result': 'AUTH_DENIED'})
                self.assertFalse(self.adapter.sessions)

    async def test_callback_replay_fails(self):
        url = await self.pending()
        self.assertEqual((await self.browser.get(url)).status_code, 303)
        self.assertEqual((await self.browser.get(url)).status_code, 403)
        self.assertEqual(len(self.adapter.sessions), 1)

    async def test_cross_browser_callback_and_forged_state_fail(self):
        url = await self.pending()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.adapter.app())) as other:
            self.assertEqual((await other.get(url)).status_code, 403)
        self.assertEqual((await self.browser.get(url)).status_code, 403)
        self.assertEqual((await self.browser.get('/auth/callback?state=forged&code=forged')).status_code, 403)

    async def test_expired_flow_and_session_fail(self):
        url = await self.pending()
        self.now[0] += 301
        self.assertEqual((await self.browser.get(url)).status_code, 403)
        await self.sign_in()
        self.now[0] += 901
        self.assertEqual((await self.browser.get('/session')).status_code, 401)

    async def test_pkce_mismatch_consumes_code(self):
        url = await self.pending()
        code = parse_qs(urlsplit(url).query)['code'][0]
        data = {'client_id': CLIENT, 'redirect_uri': self.config.callback, 'grant_type': 'authorization_code',
                'code': code, 'code_verifier': 'incorrect'}
        self.assertEqual((await self.idp.post(self.config.issuer + '/token', data=data)).status_code, 400)
        self.assertEqual((await self.browser.get(url)).status_code, 403)

    async def test_redirect_binding_and_authorize_parameters(self):
        response = await self.browser.get('/auth/login')
        q = parse_qs(urlsplit(response.headers['location']).query)
        for key, value in [('redirect_uri', 'https://other.example.invalid/callback'), ('client_id', 'other'),
                           ('code_challenge_method', 'plain')]:
            data = {k: v[0] for k, v in q.items()}
            data[key] = value
            r = await self.idp.get(self.config.issuer + '/authorize?' + urlencode(data))
            self.assertEqual(r.status_code, 400)
            self.assertNotIn('location', r.headers)

    async def test_origin_csrf_logout_and_rotation(self):
        await self.sign_in()
        first = self.browser.cookies.get(SESSION)
        csrf = (await self.session())['logout_csrf']
        for data, origin in [({'csrf': csrf}, False), ({'csrf': 'wrong'}, True)]:
            self.assertEqual((await self.post('/logout', data, origin)).status_code, 403)
        await self.sign_in()
        self.assertNotIn(first, self.adapter.sessions)
        csrf = (await self.session())['logout_csrf']
        self.assertEqual((await self.post('/logout', {'csrf': csrf})).status_code, 303)
        self.assertEqual((await self.browser.get('/session')).status_code, 401)

    async def test_headers_scheme_forwarded_identity_and_body_bounds(self):
        for kwargs in [{'headers': {'host': 'other.example.invalid'}},
                       {'headers': [('host', 'workspace.example.invalid'), ('host', 'workspace.example.invalid')]},
                       {'headers': {'cookie': 'a=' + 'x' * 513}}]:
            self.assertEqual((await self.browser.get('/', **kwargs)).status_code, 403)
        self.assertEqual((await self.browser.get('http://workspace.example.invalid/',
            headers={'x-forwarded-proto': 'https', 'x-forwarded-user': 'owner'})).status_code, 403)
        self.assertEqual((await self.browser.get('/api/summary', headers={'x-forwarded-user': 'owner'})).status_code, 401)
        await self.sign_in()
        self.assertEqual((await self.post('/logout', {'csrf': 'x' * 600})).status_code, 400)
        self.assertEqual((await self.browser.get('/api/search?q=a&q=b')).status_code, 400)
        self.assertEqual((await self.browser.get('/auth/callback?state=a&state=b&code=c')).status_code, 403)

    async def test_sessions_are_memory_only_and_restart_invalidates(self):
        await self.sign_in()
        record = next(iter(self.adapter.sessions.values()))
        self.assertEqual(set(record), {'role', 'expires', 'csrf'})
        restarted = Adapter(self.config, workspace_fixture(), self.adapter.transport)
        self.assertFalse(restarted.sessions)

    async def test_capacity_is_bounded(self):
        for _ in range(32):
            self.assertEqual((await self.browser.get('/auth/login')).status_code, 303)
        self.assertEqual((await self.browser.get('/auth/login')).status_code, 503)
        self.now[0] += 301
        self.assertEqual((await self.browser.get('/auth/login')).status_code, 303)

    async def test_persistent_mutations_serialize_and_failure_never_acknowledges(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'state'
            with StateStore.create(directory, seed_state()):
                pass
            workspace = workspace_persistent(directory)
            self.adapter.workspace = workspace
            try:
                await self.sign_in()
                csrf = (await self.session())['logout_csrf']
                responses = await asyncio.gather(*(self.post('/admin/delete',
                    {'csrf': csrf, 'source_id': 'fictional-owner-note'}) for _ in range(2)))
                self.assertEqual([r.status_code for r in responses], [303, 303])
                self.assertEqual({r.headers['location'] for r in responses}, {'/?notice=deleted', '/?notice=missing'})
                self.assertEqual(workspace.store.generation, 2)
                with patch.object(workspace.store, 'commit', side_effect=StateError('held')):
                    r = await self.post('/admin/scenario', {'csrf': csrf, 'scenario': 'stale'})
                    self.assertEqual(r.status_code, 503)
                self.assertEqual(workspace.scenario, 'fresh')
                with patch.object(workspace.store, 'ensure_available', side_effect=StateError('held')):
                    self.assertEqual((await self.browser.get('/api/summary')).status_code, 503)
                    self.assertEqual((await self.post('/logout', {'csrf': csrf})).status_code, 303)
            finally:
                workspace.close()
            with workspace_persistent(directory).store as store:
                self.assertNotIn('fictional-owner-note', json.dumps(store.payload))
                self.assertNotIn('csrf', json.dumps(store.payload))

    async def test_security_headers_and_no_callback_referrer(self):
        r = await self.browser.get('/')
        self.assertEqual(r.headers['referrer-policy'], 'same-origin')
        self.assertEqual(r.headers['cache-control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", r.headers['content-security-policy'])
        r = await self.browser.get('/auth/callback?code=x&state=y')
        self.assertEqual(r.headers['referrer-policy'], 'no-referrer')

    async def test_bad_jwks_redirect_and_oversized_token_response(self):
        for kind in ['redirect', 'oversize', 'private-key', 'malformed']:
            async def respond(request):
                if kind == 'redirect':
                    return httpx.Response(302, headers={'location': 'https://other.example.invalid/'})
                if kind == 'oversize':
                    return httpx.Response(200, content=b'x' * 32769)
                if str(request.url).endswith('/jwks'):
                    if kind == 'private-key':
                        return httpx.Response(200, json={'keys': [self.issuer.key.as_dict(private=True)]})
                    return httpx.Response(200, json={'keys': {}})
                return await httpx.ASGITransport(app=self.issuer.app()).handle_async_request(request)
            self.adapter.transport = httpx.MockTransport(respond)
            self.assertEqual((await self.browser.get(await self.pending())).status_code, 403)
            self.assertFalse(self.adapter.sessions)


class ConfigurationTests(unittest.TestCase):
    def test_only_invented_https_origins(self):
        for value in ['http://workspace.example.invalid', 'https://real.invalid', 'https://127.0.0.1/path',
                      'https://user@127.0.0.1', 'https://127.0.0.1?x=y', 'https://127.0.0.1:0']:
            with self.assertRaises(ValueError):
                Config(origin=value)
        with self.assertRaises(ValueError):
            Config(origin='https://127.0.0.1', issuer='https://127.0.0.1')
        with self.assertRaises(ValueError):
            Adapter(Config(), workspace_fixture(), verify=False)


class TlsTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_loopback_tls_rehearsal(self):
        result = await rehearsal()
        self.assertEqual(result['result'], 'PASS')
        self.assertTrue(result['verified_loopback_tls'])
        self.assertFalse(result['real_provider_qualified'])
