# Access and owner Browser QA

A successful login is one test case. Complete the denial cases and inspect the direct app route before recording access control as tested. This checklist is a proposed acceptance process; every result starts as **NOT RUN**.

## Define the audience before configuring it

Use `owner@example.com` only as a placeholder. In the real private deployment, select the exact owner identity, application, binding, and expected failure behavior. Prefer an explicit assignment over broad membership rules. Document policy evaluation mode and error behavior. An empty Authentik application binding list is not a deny-by-default configuration. [Authentik bindings](https://docs.goauthentik.io/add-secure-apps/bindings-overview/)

For an external identity gate, choose a supported integration for the app. Confirm every upstream path that serves protected data traverses that gate, and that direct network routes cannot bypass it. Avoid assuming that hiding an app in a launcher revokes access. Authentik distinguishes proxy traffic from forward-auth checks and supports separate application policies in single-application mode. [Authentik proxy provider](https://docs.goauthentik.io/add-secure-apps/providers/proxy/)

Keep Grafana native login in place. Use an appropriately limited viewing role for everyday dashboard access and reserve administration for maintenance. Review the actual permission model of the installed Grafana edition; a dashboard Viewer role does not by itself limit every query to a narrow metric set. [Grafana roles and permissions](https://grafana.com/docs/grafana/latest/administration/roles-and-permissions/)

## Browser QA matrix

Use separate browser profiles or clean private sessions so cached cookies do not invalidate denial tests. Use only accounts and devices you are authorized to test. Keep raw screenshots, identities, and logs private.

| Test | Expected observation | Initial result |
| --- | --- | --- |
| Owner on a permitted device | Correct app opens after the intended login; expected limited role is visible | NOT RUN |
| Fresh session with no app login | Sign-in or denial, with no protected data in the page or API response | NOT RUN |
| Signed-in, unassigned test identity | Application denies access even if the identity can reach the private route | NOT RUN |
| Device outside permitted network policy | Private route is unreachable or network-denied; no app data is returned | NOT RUN |
| Direct app URL, without visiting Homepage | Same authorization rule applies | NOT RUN |
| Local backend from another device | Backend is not reachable through an unintended LAN or tailnet route | NOT RUN |
| Logout, then fresh direct navigation | Protected content requires the intended login again | NOT RUN |
| Gate or policy service unavailable in an isolated test | Integration fails closed rather than serving the protected upstream | NOT RUN |
| Real phone over an allowed mobile connection | Login, navigation, wrapping, touch targets, and return links work | NOT RUN |

For a denial case, inspect content as well as the status code. A redirect is not enough if a protected response was already exposed. Run a safe GET or HEAD against a documented read endpoint. Never probe a guessed URL that may start a job, change a setting, or trigger a native control action.

For example, after replacing the reserved placeholder privately:

```sh
curl --head --max-time 10 https://workspace.domain.example/
```

Do not add authorization headers, cookies, token arguments, or response dumps to a public issue. HEAD support varies; use a documented read-only GET in the private test process if required. Avoid automatic redirects until the destination has been checked.

The real phone test must use a physical device. Browser viewport emulation can support layout review but does not prove mobile networking, touch behavior, or an installed shortcut works. A phone with Tailscale disconnected should not gain access to the private route through a public fallback.

## Read-only data boundary

The recommended Fleet adapter is a small server-side projection, kept private. It should have:

- Fixed upstream hosts, schemes, ports, and exact read endpoints.
- An explicit field allowlist, response-size cap, timeout, and cache lifetime.
- An allowlisted set of query templates and bounded time ranges.
- GET/HEAD only for supported read routes, with redirects denied or revalidated.
- Credentials scoped to the minimum upstream read permission, stored outside source control.
- Authentication and authorization at the adapter's own route.

Method filtering alone is insufficient: upstream APIs can implement unsafe actions with GET, and broad query access can expose sensitive labels. Do not offer a caller-supplied URL, arbitrary path, generic query passthrough, native control endpoint, or Docker socket proxy. Prometheus treats metrics and its HTTP access as sensitive operational surfaces; protect the upstream independently. [Prometheus security model](https://prometheus.io/docs/operating/security/)

Validate rejected hosts, paths, methods, and oversized responses against synthetic fixtures or an isolated test service. Do not send mutation requests to a live app to prove that a dashboard is read-only.

## Record a result precisely

For each case, keep UTC time, component version, scenario, expected result, observed result, and a short redacted evidence reference. Use **PASS**, **FAIL**, **NOT RUN**, or **BLOCKED**. A blocked test remains incomplete. Re-run affected cases when identity bindings, routing, app versions, or proxy rules change.
