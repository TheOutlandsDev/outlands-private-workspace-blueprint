import unittest

from identity import DEMO_PASSWORD, Sessions


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.now = 1000
        self.sessions = Sessions(clock=lambda: self.now)

    def test_owner_reader_unknown_and_wrong_password(self):
        for username, expected in [('fictional-owner', 'owner'), ('fictional-reader', 'reader')]:
            token = self.sessions.login(username, DEMO_PASSWORD)
            self.assertEqual(self.sessions.principal(token)['role'], expected)
            self.assertGreaterEqual(len(token), 40)
        self.assertIsNone(self.sessions.login('unknown', DEMO_PASSWORD))
        self.assertIsNone(self.sessions.login('fictional-owner', 'wrong'))

    def test_logout_revokes_session_and_requires_csrf(self):
        token = self.sessions.login('fictional-owner', DEMO_PASSWORD)
        self.assertFalse(self.sessions.logout(token, 'wrong'))
        self.assertTrue(self.sessions.logout(token, self.sessions.principal(token)['csrf']))
        self.assertIsNone(self.sessions.principal(token))
        self.assertFalse(self.sessions.logout(token, 'wrong'))

    def test_expiry_rotation_and_no_caller_mutation(self):
        old = self.sessions.login('fictional-owner', DEMO_PASSWORD)
        record = self.sessions.principal(old)
        record['role'] = 'reader'
        self.assertEqual(self.sessions.principal(old)['role'], 'owner')
        token = self.sessions.login('fictional-owner', DEMO_PASSWORD, previous=old)
        self.assertNotEqual(token, old)
        self.assertIsNone(self.sessions.principal(old))
        self.now += 900
        self.assertIsNone(self.sessions.principal(token))

    def test_failure_limit_and_session_bound(self):
        for _ in range(5):self.sessions.login('fictional-owner', 'wrong')
        self.assertIsNone(self.sessions.login('fictional-owner', DEMO_PASSWORD))
        self.now += 60
        self.assertIsNotNone(self.sessions.login('fictional-owner', DEMO_PASSWORD))
        self.sessions.sessions = {str(n): {'role': 'reader', 'expires': self.now + 900, 'csrf': 'fixture'}
                                  for n in range(32)}
        self.assertIsNone(self.sessions.login('fictional-owner', DEMO_PASSWORD))

    def test_forged_or_oversized_tokens_are_denied(self):
        for token in [None, 'forged', 'x' * 129, []]:
            self.assertIsNone(self.sessions.principal(token))
