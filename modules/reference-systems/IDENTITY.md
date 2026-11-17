# Identity gate and retrieval session integration

This is a working local teaching gate, not an Authentik deployment or an OIDC/SSO
implementation. It serves fixed routes and invented data. It forwards no traffic,
accepts no identity headers from a proxy, and connects to no native app or account.

For the combined portal, use the [integrated workspace](WORKSPACE.md). It keeps
this session boundary and adds role-filtered views, owner-only mutations and
server-rendered responsive pages. The standalone identity command remains available.

## Start and use the demo

From the repository root:

```sh
python3 -I -B modules/reference-systems/run.py identity --serve
```

The terminal prints a `http://127.0.0.1:` address with an automatically selected
unused port. Open that exact address in a local browser. A fixed local port can
instead be selected with `identity --serve --port 8788`; binding remains
`127.0.0.1`. The server reads no files through an HTTP path and logs no requests.
Stop it with Ctrl+C. It creates no persistent accounts, secrets or configuration.

Both public fictional accounts use password `synthetic-only`:

| Account | Session role | Expected access |
| --- | --- | --- |
| `fictional-owner` | `owner` | `/private`, `/session` and owner-visible retrieval. |
| `fictional-reader` | `reader` | `/session` and reader-visible retrieval; `/private` returns 403. |
| Signed out or forged session | None | Protected routes return 401. |

Submit the login form; it redirects to a local page with search links and a
working Sign out form. Open `/private` or `/search?q=recovery` on the same
origin. The owner sees the invented owner note; the reader receives no
result or note identifier. Sign out before switching
roles. A successful second login rotates and revokes that browser's previous
session. The role comes from server-side session state, never from query fields
or `X-Role`/forwarded-user headers.

## HTTP contract

`POST /login` accepts exactly `username` and `password` as URL-encoded form
fields. It requires the exact local Origin and Host and sets an opaque cookie
with `HttpOnly`, `SameSite=Strict`, `Path=/` and a 900-second lifetime. The cookie
has no Domain attribute. The session expires server-side after 900 seconds;
five failed password checks cause a 60-second demo-wide cooldown. At most 32
sessions can exist at once. Passwords are compared against an ephemeral salted
PBKDF2-HMAC-SHA256 digest; these public fixture credentials provide no secrecy.

`GET /session` returns the authenticated role and a session-bound logout CSRF
value. `POST /logout` requires that value in a `csrf` form field plus the exact
Origin, revokes the server session and expires its cookie. `GET /search?q=lamp`
calls the [retrieval engine](RETRIEVAL.md) with the session role. All routes have
bounded input; responses disable caching, framing, script loading and MIME
sniffing. Invalid authentication errors do not echo a submitted user or password.

The integration tests are an executable client example:

```sh
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_identity.py'
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_integration.py'
```

They exercise signed-out denial, reader denial, owner allowance, forged cookies,
untrusted identity headers, foreign Host/Origin, malformed bodies, expiry,
rotation, CSRF refusal, logout and retrieval filtering over real loopback HTTP.

## Deployment boundary and rollback

The cookie intentionally lacks `Secure` because this isolated demo uses HTTP.
The public password, local HTTP, basic server, demo-wide cooldown and lack of MFA
or durable identity storage make this unsuitable for protecting real data.
[Python documents the production limits of http.server](https://docs.python.org/3/library/http.server.html).
Follow [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
and the [native identity guide](../../docs/11-identity.md) when designing a
separate reviewed provider integration. This fixture must never be promoted by
merely changing the bind address or putting a reverse proxy in front of it.

Stop the process to revoke every session, then restore a known working source
revision if needed. No native login, provider secret, route or recovery key is
created or removed. Real provider login, MFA, token validation, shared app
sign-in, TLS and recovery acceptance remain separate `NOT_RUN` work.
