# OUTLANDS · App walkthrough library

[Repository home](../README.md) · [Dockhand walkthrough](06-dockhand-cyberpunk.md) · [Local demo tour](../examples/app-tour/README.md)

Build one layer at a time. Start with Homepage, add private access, then choose the guide for the next app. These beginner walkthroughs explain the setup path, a fictional config or data contract, the OUTLANDS design, verification and rollback.

## Choose an app

| Walkthrough | What you learn |
| --- | --- |
| [Workspace catalog](08-homepage.md) | One page for opening apps. A tile is a bookmark, not an authorization rule. |
| [AI Workbench](09-ai-workbench.md) | A branded place to talk to a model. This mockup has no chat engine and sends nothing. |
| [Operations dashboard](10-grafana.md) | Panels summarize measurements. Empty or stale data must remain visibly different from zero. |
| [Owner access boundary](11-identity.md) | An identity check decides who may enter. A theme does not change that decision. |
| [Example customer workspace](12-portals.md) | A clean demo should explain the service without revealing the real operator or infrastructure. |
| [Fleet inventory](13-fleet.md) | Presence, health and freshness are separate signals. A missing metric is never a healthy zero. |
| [Metrics explorer](14-prometheus.md) | A scrape target supplies measurements. A successful scrape alone does not prove every service is healthy. |
| [Alert overview](15-alertmanager.md) | Grouping and routing organize alerts. A read-only observer must not create silences. |
| [Container resource view](16-cadvisor.md) | Container telemetry can reveal workloads and labels. Show only what the owner needs. |
| [Repository overview](17-git-manager.md) | Project status and safe shortcuts in one view. This example never reads a checkout or runs Git. |
| [Learning explorer](18-learning.md) | A useful learning map explains relationships without exposing internal implementation details. |
| [Game connection guide](19-game-connections.md) | Connection instructions and monitoring belong apart from server controls. |
| [Local developer tools](20-local-tools.md) | API documentation helps developers understand a service. An interactive console can also mutate it. |
| [Dockhand](06-dockhand-cyberpunk.md) | Container observer boundaries and a staged theme adapter. |

## How the catalog fits together

A catalog can have many dashboard tiles without having that many different applications. Daily cockpit, node/mobile command, incident triage, hosted systems, fleet/capacity/storage, engineering/project/workload and game monitoring views all use the Grafana guide. Keep stable dashboard UIDs and separate native Grafana login.

Account Portal and Identity Administration use the Authentik guide, with different privileges. Client demonstrations and custom service portals use the original portal example. Fleet Inventory is distinct from a Grafana fleet dashboard. A learning map and local API documentation use their own original examples. Game connection instructions are covered; Pelican/Game Server Control is intentionally out of scope.

The custom-app examples teach a design and data contract. They do not distribute an operator's private source, infrastructure inventory or complete deployment. Every URL, subject, timestamp and metric in the new fixtures is fictional. Upstream apps retain their licenses and branding requirements.

## First exercise: inspect the design safely

On the repository page, choose **Code → Download ZIP**, extract the archive, and open a terminal in the extracted repository folder. Install Python 3.9+ from its official source if needed. Check `python3 --version` before starting. On Windows, use `py -3` in place of `python3` if that is how Python is installed. No app installation is needed for the static tour.

```sh
# From this repository root, with Python 3.9+
python3 -I -B examples/app-tour/serve_demo.py --port 8766
```

Open `http://127.0.0.1:8766/`. Each page has a visible **ILLUSTRATIVE MOCKUP** label and navigation to the other examples. Stop with Ctrl+C. There is no live backend, no login, no network collector and no automated native installer.

## Suggested build order

1. Homepage and the local fixtures: learn links, layout and asset paths.
2. Private network and explicit owner authorization: follow [access and QA](03-access-and-qa.md).
3. One app with native login: confirm a real owner session before theming.
4. Metrics and truthful fleet status: distinguish missing, stale, unavailable and healthy.
5. Additional tools: review their API and data boundaries individually.
6. Customer demo: use fictional content and prove usability on a real phone before sharing it.

Use the checked upstream references in each guide for your chosen release. The static screenshot is a design target, not proof of native theme support. Reader deployment and access checks start **NOT RUN**; [VALIDATION.md](../VALIDATION.md) records only checks performed on this repository.
