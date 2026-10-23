# Third-party boundaries and upstream references

This blueprint uses original OUTLANDS tutorial text and visual direction. It links to upstream projects so readers can choose and operate their own deployments. A product name identifies an integration or dependency; it does not imply sponsorship, endorsement, or ownership of that product.

## Projects discussed

| Project | Role in the tutorial | Official reference |
| --- | --- | --- |
| Dockhand | Container management discussed in the theme walkthrough | [Dockhand manual](https://dockhand.pro/manual/) · [source](https://github.com/Finsys/dockhand) |
| Nginx | Optional HTML theme overlay | [HTTP sub module](https://nginx.org/en/docs/http/ngx_http_sub_module.html) |
| Homepage | Central application catalog | [Homepage documentation](https://gethomepage.dev/) |
| Docker and Compose | Container runtime and service definitions | [Docker documentation](https://docs.docker.com/) |
| Tailscale | Private connectivity and Serve HTTPS routes | [Tailscale documentation](https://tailscale.com/docs/) |
| Authentik | Staged application identity and policy integration | [Authentik documentation](https://docs.goauthentik.io/) |
| Grafana | Native-login dashboards | [Grafana documentation](https://grafana.com/docs/grafana/latest/) |
| Prometheus and Node Exporter | Host telemetry and queries | [Prometheus documentation](https://prometheus.io/docs/introduction/overview/) |

Upstream documentation was consulted on 2026-10-22; Dockhand appearance and Nginx filter references were checked on 2026-10-23. Interfaces, defaults, license terms, and supported versions can change. Check the documentation for the exact release you deploy.

## Reuse decisions

Do not assume that this repository grants rights to third-party software, trademarks, logos, fonts, screenshots, or artwork. Review each upstream project's current license and any separate asset or trademark policy before reuse or distribution. Container images retain their own terms and dependencies.

Use original symbols and illustrations for the OUTLANDS layer. Do not copy a game's logo, faction mark, character, interface art, soundtrack, or screenshot to establish a cyberpunk mood. An original dark palette and geometric styling can communicate that direction without reproducing protected assets.

This file does not assign a license to this repository or change any upstream license. Any repository license decision must be made explicitly by its owner.

## Additional walkthrough references (checked 2026-10-23)

- [Open WebUI quick start](https://docs.openwebui.com/getting-started/quick-start/): data persistence, native deployment and release-specific license/branding review.
- [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/): lab routing and receiver syntax.
- [cAdvisor Prometheus metrics](https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md): container telemetry.
- [Git status](https://git-scm.com/docs/git-status): read-only inspection concepts; this repository runs no Git collector.
- [MDN HTML learning](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content) and [accessibility](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Accessibility): original portal/learning fixture development.
- [OpenAPI specification](https://spec.openapis.org/oas/latest.html): API contract terminology.

The app-tour screenshots depict original fictional HTML, not vendor interfaces. No upstream executable app code, vendor fonts, screenshots or private portal implementation is bundled by these additions. Open WebUI's current license and branding requirements must be reviewed separately before any customized distribution.
