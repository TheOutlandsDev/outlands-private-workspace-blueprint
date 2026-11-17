import http.client
import json
from pathlib import Path
import re
import select
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import run
from identity import make_server
from state_store import StateStore, restore

LAUNCHER = Path(__file__).with_name('run.py')


class PersistentProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.directory = self.parent / 'state'
        self.processes = []
        self.addCleanup(self.stop_all)
        initialized = subprocess.run([sys.executable, '-I', '-B', str(LAUNCHER), 'state', 'init',
                                      '--directory', str(self.directory)], capture_output=True, text=True, timeout=10)
        self.assertEqual(initialized.returncode, 0)
        self.assertEqual(json.loads(initialized.stdout)['generation'], 1)

    def start(self, directory=None):
        process = subprocess.Popen([sys.executable, '-I', '-B', str(LAUNCHER), 'workspace', '--serve',
                                    '--state-dir', str(directory or self.directory)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.processes.append(process)
        self.assertTrue(select.select([process.stdout], [], [], 10)[0], 'launcher readiness')
        line = process.stdout.readline().strip()
        match = re.fullmatch(r'Synthetic workspace: http://127\.0\.0\.1:([0-9]+)/', line)
        self.assertIsNotNone(match, 'fixed startup contract')
        return process, int(match.group(1))

    def stop(self, process, crash=False):
        if process.poll() is None:
            if crash:process.kill()
            else:process.send_signal(signal.SIGINT)
        _stdout, stderr = process.communicate(timeout=10)
        if not crash:
            self.assertEqual(process.returncode, 0)
            self.assertEqual(stderr, '')
        self.processes.remove(process)

    def stop_all(self):
        for process in list(self.processes):
            if process.poll() is None:process.kill()
            process.communicate(timeout=10)

    def request(self, port, method, path, fields=None, cookie=None):
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
        headers = {'Origin': f'http://127.0.0.1:{port}'}
        if cookie:headers['Cookie'] = cookie
        body = None
        if fields is not None:
            body = urlencode(fields)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode()
        finally:
            connection.close()

    def login(self, port, role='owner'):
        status, headers, _body = self.request(port, 'POST', '/login',
                                             {'username': 'fictional-' + role, 'password': 'synthetic-only'})
        self.assertEqual(status, 303)
        cookie = headers['Set-Cookie'].split(';', 1)[0]
        csrf = json.loads(self.request(port, 'GET', '/session', cookie=cookie)[2])['logout_csrf']
        return cookie, csrf

    def mutate(self, port, cookie, csrf, scenario):
        self.assertEqual(self.request(port, 'POST', '/admin/delete',
                                      {'source_id': 'fictional-owner-note', 'csrf': csrf}, cookie)[0], 303)
        self.assertEqual(self.request(port, 'POST', '/admin/scenario',
                                      {'scenario': scenario, 'csrf': csrf}, cookie)[0], 303)

    def test_real_restart_keeps_deletion_state_and_rejects_old_sessions(self):
        first, port = self.start()
        old_cookie, csrf = self.login(port)
        reader, reader_csrf = self.login(port, 'reader')
        self.assertEqual(self.request(port, 'POST', '/admin/delete',
                                      {'source_id': 'fictional-owner-note', 'csrf': reader_csrf}, reader)[0], 403)
        self.mutate(port, old_cookie, csrf, 'stale')
        self.stop(first)
        for file in self.directory.iterdir():
            self.assertNotIn(old_cookie.encode(), file.read_bytes())
            self.assertNotIn(csrf.encode(), file.read_bytes())
        second, port = self.start()
        self.assertEqual(self.request(port, 'GET', '/api/summary', cookie=old_cookie)[0], 401)
        cookie, _csrf = self.login(port)
        summary = json.loads(self.request(port, 'GET', '/api/summary', cookie=cookie)[2])
        self.assertEqual(summary['inventory']['state'], 'STALE')
        self.assertEqual(summary['storage'], 'PRIVATE_PERSISTENT')
        self.assertEqual(summary['retrieval']['visible_documents'], 2)
        self.assertEqual(json.loads(self.request(port, 'GET', '/api/search?q=recovery', cookie=cookie)[2])['results'], [])
        self.assertNotIn('fictional-owner-note', self.request(port, 'GET', '/api/documents', cookie=cookie)[2])
        locked = subprocess.run([sys.executable, '-I', '-B', str(LAUNCHER), 'state', 'backup',
                                 '--directory', str(self.directory), '--output', str(self.parent / 'locked.json')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(locked.returncode, 1)
        self.assertEqual(json.loads(locked.stdout)['result'], 'REVIEW')
        self.assertFalse((self.parent / 'locked.json').exists())
        self.stop(second)

    def test_abrupt_process_exit_and_fresh_directory_restore_keep_committed_state(self):
        first, port = self.start()
        old_cookie, csrf = self.login(port)
        self.mutate(port, old_cookie, csrf, 'unavailable')
        self.stop(first, crash=True)
        snapshot = self.parent / 'snapshot.json'
        with StateStore(self.directory) as store:store.backup(snapshot)
        restored = self.parent / 'restored'
        with restore(snapshot, restored):pass
        second, port = self.start(restored)
        self.assertEqual(self.request(port, 'GET', '/api/summary', cookie=old_cookie)[0], 401)
        cookie, _csrf = self.login(port)
        summary = json.loads(self.request(port, 'GET', '/api/summary', cookie=cookie)[2])
        self.assertEqual(summary['inventory']['state'], 'UNAVAILABLE')
        self.assertNotIn('data', summary['inventory'])
        self.assertNotIn('data', summary['advisories'])
        self.assertEqual(summary['retrieval']['visible_documents'], 2)
        self.assertEqual(json.loads(self.request(port, 'GET', '/api/search?q=recovery', cookie=cookie)[2])['results'], [])
        self.stop(second)

    def test_failed_commit_returns_503_without_changing_memory_or_leaking_paths(self):
        workspace = run.workspace_persistent(self.directory)
        server = make_server(workspace.index, workspace=workspace)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        try:
            cookie, csrf = self.login(server.server_port)
            with patch('state_store.os.replace', side_effect=OSError('fictional-private-failure-marker')):
                status, _headers, body = self.request(server.server_port, 'POST', '/admin/delete',
                                                       {'source_id': 'fictional-owner-note', 'csrf': csrf}, cookie)
            self.assertEqual(status, 503)
            self.assertNotIn('fictional-private-failure-marker', body)
            self.assertNotIn(str(self.directory), body)
            self.assertIn('fictional-owner-note', workspace.index.documents)
            self.assertEqual(self.request(server.server_port, 'GET', '/api/search?q=recovery', cookie=cookie)[0], 503)
            self.assertEqual(self.request(server.server_port, 'GET', '/', cookie=cookie)[0], 503)
            self.assertEqual(self.request(server.server_port, 'POST', '/logout', {'csrf': csrf}, cookie)[0], 303)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            workspace.close()

    def test_missing_or_corrupt_state_never_initializes_silently(self):
        for directory in [self.parent / 'missing', self.directory]:
            if directory == self.directory:(directory / 'current.json').write_text('corrupt fictional head')
            result = subprocess.run([sys.executable, '-I', '-B', str(LAUNCHER), 'workspace', '--serve',
                                     '--state-dir', str(directory)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['result'], 'REVIEW')
            self.assertNotIn(str(directory), result.stdout + result.stderr)
        self.assertFalse((self.parent / 'missing').exists())
