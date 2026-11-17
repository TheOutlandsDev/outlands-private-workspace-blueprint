import contextlib
import http.client
import io
import json
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import run
from identity import COOKIE, make_server


class HttpIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(run.index_fixture())
        cls.origin = f'http://127.0.0.1:{cls.server.server_port}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

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
            payload = response.read().decode()
            return response.status, dict(response.getheaders()), payload
        finally:
            connection.close()

    def login(self, user):
        status, headers, _body = self.request('POST', '/login',
                                             {'username': user, 'password': 'synthetic-only'})
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/')
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        return headers['Set-Cookie'].split(';', 1)[0]

    def test_signed_out_forged_and_forwarded_identity_are_denied(self):
        for cookie in [None, COOKIE + '=forged']:
            status, headers, _body = self.request('GET', '/private', cookie=cookie,
                                                 extra={'X-Forwarded-User': 'fictional-owner'})
            self.assertEqual(status, 401)
            self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_owner_reader_retrieval_and_logout_end_to_end(self):
        owner = self.login('fictional-owner')
        reader = self.login('fictional-reader')
        self.assertEqual(self.request('GET', '/private', cookie=owner)[0], 200)
        self.assertEqual(self.request('GET', '/private', cookie=reader)[0], 403)
        owner_hits = json.loads(self.request('GET', '/search?q=recovery', cookie=owner)[2])
        reader_hits = json.loads(self.request('GET', '/search?q=recovery', cookie=reader,
                                              extra={'X-Role': 'owner'})[2])
        self.assertEqual(len(owner_hits['results']), 1)
        self.assertEqual(reader_hits['results'], [])
        self.assertNotIn('fictional-owner-note', json.dumps(reader_hits))
        csrf = json.loads(self.request('GET', '/session', cookie=owner)[2])['logout_csrf']
        self.assertEqual(self.request('POST', '/logout', {'csrf': 'wrong'}, cookie=owner)[0], 403)
        self.assertEqual(self.request('POST', '/logout', {'csrf': csrf}, cookie=owner)[0], 303)
        self.assertEqual(self.request('GET', '/private', cookie=owner)[0], 401)

    def test_foreign_origin_host_duplicate_fields_and_large_body(self):
        self.assertEqual(self.request('GET', '/', extra={'Host': 'foreign.example.invalid'})[0], 403)
        self.assertEqual(self.request('POST', '/login', {'username': 'fictional-owner'},
                                      extra={'Origin': 'https://foreign.example.invalid'})[0], 403)
        self.assertEqual(self.request('POST', '/login', [('username', 'a'), ('username', 'b')])[0], 400)
        self.assertEqual(self.request('POST', '/login', {'username': 'x' * 513})[0], 400)

    def test_fixed_routes_not_a_file_server(self):
        owner = self.login('fictional-owner')
        self.assertIn('Sign out', self.request('GET', '/', cookie=owner)[2])
        for path in ['/identity.py', '/fixtures/corpus.example.json', '/../README.md']:
            self.assertEqual(self.request('GET', path, cookie=owner)[0], 404)
        self.assertEqual(self.server.server_address[0], '127.0.0.1')


class OfflineIntegrationTests(unittest.TestCase):
    def test_full_synthetic_workflow_needs_no_network_or_subprocess(self):
        with patch('socket.socket', side_effect=AssertionError('network')), \
             patch('subprocess.run', side_effect=AssertionError('subprocess')):
            report = run.demo()
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(report['identity_to_retrieval'], 'PASS')
        self.assertEqual(report['revocation_and_deletion'], 'PASS')
        self.assertEqual(report['source_inventory']['counts']['code']['files'], 1)
        self.assertFalse(report['real_host_qualified'])

    def test_cli_fixed_error_does_not_echo_private_marker(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(run.main(['fictional-private-marker']), 1)
        self.assertNotIn('fictional-private-marker', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['result'], 'REVIEW')
