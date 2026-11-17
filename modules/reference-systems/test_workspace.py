import contextlib
import http.client
import io
import json
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode, quote

import run
from identity import COOKIE, Sessions, make_server
from workspace import home_page, search_page


class WorkspaceHttpTests(unittest.TestCase):
    def setUp(self):
        self.workspace = run.workspace_fixture()
        self.now = 1000
        self.sessions = Sessions(clock=lambda: self.now)
        self.server = make_server(self.workspace.index, workspace=self.workspace, sessions=self.sessions)
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method, path, fields=None, cookie=None, extra=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Origin': self.origin}
        if cookie:headers['Cookie'] = cookie
        body = None
        if fields is not None:
            body = urlencode(fields)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        headers.update(extra or {})
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode()
        finally:
            connection.close()

    def login(self, role='owner'):
        status, headers, _body = self.request('POST', '/login',
                                             {'username': 'fictional-' + role, 'password': 'synthetic-only'})
        self.assertEqual(status, 303)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        csrf = json.loads(self.request('GET', '/session', cookie=cookie)[2])['logout_csrf']
        return cookie, csrf

    def test_anonymous_and_forged_sessions_cannot_read_any_api(self):
        for cookie in [None, COOKIE + '=forged']:
            for endpoint in ['/api/summary', '/api/inventory', '/api/advisories',
                             '/api/documents', '/api/search?q=recovery']:
                self.assertEqual(self.request('GET', endpoint, cookie=cookie)[0], 401)
        self.assertEqual(self.request('GET', '/workspace/advisories')[0], 401)
        self.assertEqual(self.request('POST', '/admin/delete', {'source_id': 'fictional-owner-note'})[0], 401)

    def test_reader_projection_has_no_owner_identifiers_or_controls(self):
        cookie, _csrf = self.login('reader')
        summary = json.loads(self.request('GET', '/api/summary', cookie=cookie)[2])
        self.assertEqual(summary['advisories'], {'state': 'DENIED'})
        self.assertEqual(summary['retrieval']['visible_documents'], 2)
        html = self.request('GET', '/', cookie=cookie)[2]
        for value in ['fictional-owner-note', 'fictional-amber', '/admin/', 'OWNER CONTROLS']:
            self.assertNotIn(value, html)
            self.assertNotIn(value, json.dumps(summary))
        for endpoint in ['/api/advisories', '/api/documents', '/workspace/advisories']:
            self.assertEqual(self.request('GET', endpoint, cookie=cookie)[0], 403)

    def test_direct_reader_mutations_are_denied_even_with_valid_csrf(self):
        cookie, csrf = self.login('reader')
        for endpoint, fields in [('/admin/scenario', {'scenario': 'unavailable', 'csrf': csrf}),
                                 ('/admin/delete', {'source_id': 'fictional-owner-note', 'csrf': csrf}),
                                 ('/admin/delete?role=owner', {'source_id': 'fictional-owner-note', 'csrf': csrf})]:
            self.assertEqual(self.request('POST', endpoint, fields, cookie,
                                          {'X-Role': 'owner', 'X-Forwarded-User': 'fictional-owner'})[0], 403)
        self.assertEqual(self.workspace.scenario, 'fresh')
        self.assertIn('fictional-owner-note', self.workspace.index.documents)

    def test_owner_and_reader_search_use_session_role(self):
        for role in ['owner', 'reader']:
            cookie, _csrf = self.login(role)
            payload = json.loads(self.request('GET', '/api/search?q=recovery', cookie=cookie)[2])
            self.assertEqual(len(payload['results']), 1 if role == 'owner' else 0)
            page = self.request('GET', '/workspace/search?q=recovery', cookie=cookie)[2]
            self.assertIn('RESULTS' if role == 'owner' else 'EMPTY', page)
            if role == 'reader':self.assertNotIn('fictional-owner-note', page)
        cookie, _csrf = self.login()
        self.assertEqual(self.request('GET', '/api/search?q=lamp&role=owner', cookie=cookie)[0], 400)

    def test_stale_unavailable_and_recovered_states_keep_retrieval_independent(self):
        cookie, csrf = self.login()
        for scenario, expected in [('stale', 'STALE'), ('unavailable', 'UNAVAILABLE'), ('fresh', 'FRESH')]:
            self.assertEqual(self.request('POST', '/admin/scenario', {'csrf': csrf, 'scenario': scenario}, cookie)[0], 303)
            payload = json.loads(self.request('GET', '/api/summary', cookie=cookie)[2])
            self.assertEqual(payload['inventory']['state'], expected)
            self.assertEqual(payload['advisories']['state'], expected)
            self.assertEqual(payload['retrieval']['state'], 'READY')
            if expected == 'UNAVAILABLE':
                self.assertNotIn('data', payload['inventory'])
                self.assertNotIn('data', payload['advisories'])
                html = self.request('GET', '/', cookie=cookie)[2]
                self.assertNotIn('review candidate</span>', html)
            else:
                self.assertFalse(payload['advisories']['data']['remediation_authorized'])

    def test_owner_delete_removes_document_and_all_derived_results(self):
        cookie, csrf = self.login()
        fields = {'csrf': csrf, 'source_id': 'fictional-owner-note'}
        self.assertEqual(self.request('POST', '/admin/delete', fields, cookie)[0], 303)
        self.assertEqual(json.loads(self.request('GET', '/api/search?q=recovery', cookie=cookie)[2])['results'], [])
        self.assertNotIn('fictional-owner-note', self.request('GET', '/api/documents', cookie=cookie)[2])
        self.assertEqual(self.request('POST', '/admin/delete', fields, cookie)[1]['Location'], '/?notice=missing')
        self.assertIn('fictional-owner-note', run.workspace_fixture().index.documents)

    def test_csrf_foreign_and_null_origins_are_refused_without_mutation(self):
        cookie, csrf = self.login()
        for origin in ['null', 'https://foreign.example.invalid']:
            self.assertEqual(self.request('POST', '/admin/scenario', {'csrf': csrf, 'scenario': 'stale'}, cookie,
                                          {'Origin': origin})[0], 403)
            self.assertEqual(self.request('POST', '/login', {'username': 'fictional-owner', 'password': 'synthetic-only'},
                                          extra={'Origin': origin})[0], 403)
        for invalid in ['wrong', '\u00e9', 'x' * 129]:
            self.assertEqual(self.request('POST', '/admin/scenario', {'csrf': invalid, 'scenario': 'stale'}, cookie)[0], 403)
        self.assertEqual(self.request('GET', '/admin/scenario?scenario=stale', cookie=cookie)[0], 405)
        self.assertEqual(self.workspace.scenario, 'fresh')

    def test_expiry_and_logout_revoke_all_protected_routes(self):
        cookie, csrf = self.login()
        self.assertEqual(self.request('POST', '/logout', {'csrf': csrf}, cookie)[0], 303)
        self.assertEqual(self.request('GET', '/api/summary', cookie=cookie)[0], 401)
        cookie, csrf = self.login()
        self.now += 900
        self.assertEqual(self.request('GET', '/api/summary', cookie=cookie)[0], 401)
        self.assertEqual(self.request('POST', '/admin/delete', {'csrf': csrf, 'source_id': 'fictional-owner-note'}, cookie)[0], 401)

    def test_query_and_notice_escaping_and_fixed_asset_scope(self):
        cookie, _csrf = self.login()
        query = '<script>alert("fixture")</script>'
        page = self.request('GET', '/workspace/search?q=' + quote(query), cookie=cookie)[2]
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertEqual(self.request('GET', '/?notice=' + quote(query), cookie=cookie)[0], 400)
        for path in ['/workspace.py', '/fixtures/corpus.example.json', '/workspace.css/../identity.py']:
            self.assertEqual(self.request('GET', path, cookie=cookie)[0], 404)
        status, headers, body = self.request('GET', '/workspace.css')
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/css'))
        self.assertIn('@media', body)
        self.assertEqual(headers['Referrer-Policy'], 'same-origin')
        self.assertIn("default-src 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_malformed_admin_fields_do_not_change_state(self):
        cookie, csrf = self.login()
        for fields in [{'csrf': csrf, 'scenario': 'unknown'},
                       [('csrf', csrf), ('scenario', 'fresh'), ('scenario', 'stale')]]:
            self.assertEqual(self.request('POST', '/admin/scenario', fields, cookie)[0], 400)
        self.assertEqual(self.workspace.scenario, 'fresh')


class WorkspaceOfflineTests(unittest.TestCase):
    def test_demo_reads_only_synthetic_fixtures_without_network_or_subprocess(self):
        output = io.StringIO()
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('subprocess')), \
             contextlib.redirect_stdout(output):
            self.assertEqual(run.main(['workspace', '--demo']), 0)
        self.assertTrue(json.loads(output.getvalue())['synthetic_fixture'])

    def test_no_raw_source_html_is_rendered(self):
        workspace = run.workspace_fixture()
        source, chunk, _text, terms = workspace.index.chunks[0]
        workspace.index.chunks[0] = (source, chunk, '<script>fictional</script>', terms)
        html = search_page(workspace, {'role': 'reader', 'csrf': 'fixture'}, 'lamp')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('/admin/', home_page(workspace, {'role': 'reader', 'csrf': 'fixture'}))
