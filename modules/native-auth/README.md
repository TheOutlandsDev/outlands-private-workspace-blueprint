# Synthetic native authentication adapter

This optional adapter signs users into the [integrated workspace](../reference-systems/README.md)
through an invented OIDC issuer. It runs Authorization Code with PKCE S256,
validates a signed ID token through maintained libraries, and creates its own
short-lived session. The public demo password endpoint is disabled in this mode.

Only invented issuers and users are accepted. There is no production provider
configuration, client secret, real account import, hosted route or deployment
command. The existing standard-library demos still work without these optional
dependencies. This is a protocol reference and a finite local rehearsal.

## Setup and run

Use Linux, Python 3.10 or later and a fresh virtual environment outside this
checkout. Installing the exact optional packages contacts official PyPI; tests
then use in-process transports and loopback HTTPS only. The dependency lock
pins all transitive versions and wheel hashes. No source builds or system
Python package changes are needed.

From the repository root:

```sh
auth_env="$(mktemp -d)"
python3 -m venv "$auth_env/venv"
"$auth_env/venv/bin/python" -m pip install \
  --index-url https://pypi.org/simple --require-hashes --only-binary=:all: \
  -r modules/native-auth/requirements.lock
"$auth_env/venv/bin/python" -I -B -m unittest discover \
  -s modules/native-auth -p 'test_*.py'
"$auth_env/venv/bin/python" -I -B modules/native-auth/run_native.py rehearse
```

Expect `OK` from the tests and fixed JSON containing `result: PASS` and
`verified_loopback_tls: true` from the finite rehearsal. Authentication, token,
key and subject values are not printed by the rehearsal. No service remains
running afterward. Keep failure evidence private and inspect a failure before
rerunning. The temporary environment remains available for inspection; removing
that explicitly selected disposable environment is the rollback for installation.

The rehearsal creates a private disposable state directory and temporary TLS
certificate/key, binds both servers to `127.0.0.1` on ephemeral ports, and uses
separate `127.0.0.1` and `localhost` cookie hosts. Its own clients trust that
temporary certificate only. A default-trust client must reject it. No operating
system/browser trust store changes or disabled TLS verification occur. Owned
servers stop and disposable fixture files are removed on exit. The usual
`localhost` loopback resolution is required; no resolver configuration is changed.

## Request and identity method

1. `/auth/login` creates a random server-side transaction, state, nonce, PKCE
   verifier and separate browser binding. The verifier stays on the server.
2. The fake issuer checks the exact client and callback, returns a one-use code
   and requires its S256 verifier at the token endpoint. Codes expire after
   60 seconds and transactions after 300 seconds.
3. `/auth/callback` consumes the transaction before network work. State and
   the browser-binding cookie must match. Authlib exchanges the code; joserfc
   verifies RS256 against a bounded public RSA JWKS from the pinned fixture
   endpoint. Redirects and token-provided key URLs are never followed.
4. The adapter checks exact issuer, single client audience, subject, nonce,
   expiry, issuance time, optional authorized party and not-before. Tokens
   older than 300 seconds, future issuance, missing claims or lifetime over
   300 seconds fail. The only role mapping is the fixed verified
   `(issuer, subject)` pair: `invented-owner` or `invented-reader`. Token role,
   group and email claims confer no permissions.
5. A new random opaque session replaces the previous session. Sessions hold
   role, expiry and CSRF only; they expire after 900 seconds and disappear on
   restart. Provider tokens, subjects, codes and signing keys are never written
   to durable workspace state. The fake issuer's ephemeral key exists in memory.

The flow cookie uses `__Host-`, Secure, HttpOnly, Path `/`, SameSite Lax for
the top-level GET callback. The session cookie uses the same host-only flags
with SameSite Strict. Callback/auth responses suppress referrers; regular forms
retain same-origin referrers so their Origin can be validated. Logout revokes
the local session. Provider logout/revocation and refresh tokens are outside this
fixture; there is no stored provider token to refresh or revoke.

## Permission and persistence method

All workspace endpoints perform local authorization. Readers receive filtered
retrieval and inventory/summary access; advisory details, document administration
and source-state changes require the owner role. Mutations require the exact
HTTPS Origin and session CSRF token. Forwarded identity/protocol headers do not
establish identity or HTTPS. Host and scheme are checked directly.

One asynchronous lock serializes authentication, session and workspace requests.
The finite launcher uses one worker and the existing exclusive state lease.
Successful mutations commit durable state before acknowledging success; failed
commits return a fixed 503 response. Logout remains possible when state is
unavailable. No multiworker/state-sharing model is supplied.

Flows, sessions and codes are capped at 32 each. Request fields, body, cookies,
headers, provider responses and JWKS have explicit bounds. Provider calls have
three-second timeouts; a dispatch has a ten-second deadline. Access logging is
disabled by the finite launcher. This is a small serialized teaching fixture,
not an internet-facing availability design.

## Acceptance and remaining gates

Tests cover owner/reader access, invented subject allowlisting, ignored privilege
claims, expiry, PKCE, callback/code replay, wrong-browser binding, invalid token
signatures/claims/keys, provider outage, no password fallback, origin/CSRF/host
denial, session rotation/logout, serialized durable mutations, restart state and
failure without false success. A real loopback TLS rehearsal checks certificate
verification, owner mutation, reader denial and logout over actual sockets.

These results do not qualify a real identity provider, deployed TLS, shared
device access, physical-device UI, host resources, backup destination or recovery.
Real staging remains `NOT QUALIFIED`. Its future private implementation needs
provider-specific discovery/registration and key rotation, real issuer/subject
approval, account lifecycle/revocation, trusted HTTPS termination, log review,
operator recovery, target acceptance and browser/device checks. None of those
values or private staging records belong in this repository.

Dependencies and license metadata are listed in [DEPENDENCIES.md](DEPENDENCIES.md).
The protocol follows [OIDC Core](https://openid.net/specs/openid-connect-core-1_0.html)
and [PKCE](https://www.rfc-editor.org/rfc/rfc7636). Library references:
[Authlib OAuth client](https://docs.authlib.org/en/1.7.1/oauth2/client/http/),
[joserfc JWT](https://jose.authlib.org/en/guide/jwt/),
[Starlette](https://starlette.dev/applications/),
[Uvicorn](https://uvicorn.dev/settings/).
