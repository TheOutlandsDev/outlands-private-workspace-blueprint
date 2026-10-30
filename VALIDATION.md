# Validation boundaries

## Fictional release walkthrough

The [worked example](docs/24-fictional-release-walkthrough.md) uses only the
checked-in 46-byte fictional export. Its expected `CREATED`, `PASS`, and
`ERROR: EXTRA_FILE` outputs can be reproduced offline. The decision table keeps
privacy, rights and publication at `NOT RUN` or `HOLD`; those reviews were not
performed by the tools.

## Fictional release manifest creator

The creator reads an explicit allowlist and refuses unlisted files and output
overwrite. Its local contract tests cover missing/extra files, links, unsafe
paths, size and entry bounds, output placement, and fixed-code failures. The
generated fictional manifest passes the existing verifier. These are offline
source checks only; they do not clear privacy or publication rights. See the
[release tools guide](examples/release-manifest/README.md) for commands and limits.

## Public source screen capacity

The source screen accepts up to 128 files while retaining its 8 MB total and
2 MB per-file limits. An offline boundary test checks that 128 fictional files
pass, the 129th fails, and a synthetic private-path finding still appears.
The screen reports categories, not matched content; it remains a review aid,
not publication clearance. Run from the repository root:

```sh
python3 -I -B scripts/check_public_source.py
python3 -I -B -m unittest discover -s scripts -p 'test_*.py'
```

## Fictional release manifest example

| Check | Local result | Limit |
| --- | --- | --- |
| Exact-file fixture | PASS | One fictional 46-byte file; no live export reviewed. |
| Contract tests | 7 PASS | Tampering, extra/missing files, links, unsafe paths, duplicate keys, directory fanout and quiet error output were exercised. |
| Public source screen | PASS | 98 files passed bounded source screening in this proposed PR checkout. |
| Hosted PR CI | SEE PR | GitHub reports the current hosted result for each proposed commit. |
| Privacy, rights, deployment | NOT CLEARED | A hash match does not grant publication rights or prove private data absent. |

Commands and manifest format are in the [release manifest example](examples/release-manifest/README.md).
These results describe local source checks; the export should be frozen while it is verified.

## Engineering method and evidence ledger example

| Check | Result | Limit |
| --- | --- | --- |
| Ledger example | PASS | Five fictional checks remain `NOT_RUN`; no deployment evidence is asserted. |
| Ledger contract tests | 4 PASS | Tests reject duplicate keys/IDs, unmatched evidence stages, and evidence on unrun checks. |
| Public source screen | PASS | 92 selected files passed the documented bounded patterns and relative-link checks at this source review. |
| Native deployment, access, physical phone, restore | NOT RUN | This addition is documentation and an offline record-shape example. |

Run from the repository root:

```sh
python3 -I -B examples/evidence-ledger/check_ledger.py examples/evidence-ledger/ledger.example.json
python3 -I -B -m unittest discover -s examples/evidence-ledger -p 'test_*.py'
python3 -I -B scripts/check_public_source.py
```

The validator does not open evidence references or verify that a stated test happened. Re-run these commands for a changed checkout; the counts above describe this reviewed source selection.

Checks recorded for the initial source publication:

| Check | Result | What it means |
|---|---|---|
| Local Markdown links | PASS | Relative targets exist in this source tree. |
| Bounded public-source screening | PASS | Common private paths, tailnet fingerprints, nonexample emails, private addresses and token shapes were not found. |
| Compose model resolution | PASS | `docker compose config --quiet` accepted the example using a synthetic digest fixture and example environment values. No image was fetched or asserted to exist. |
| Original SVG structure | PASS | Included artwork parses as SVG and uses no external assets or scripts. |
| Homepage image pull and boot | NOT RUN | Select and review a real upstream image before a local trial. |
| Private HTTPS and owner policy | NOT RUN | Readers configure and verify their own access boundary. |
| Native app and restricted API compatibility | NOT RUN | App versions and endpoints need individual review. |
| Backup restore / rollback exercise | NOT RUN | A backup file or procedure alone is not restore proof. |
| Real phone and desktop acceptance | NOT RUN | Viewport previews do not replace a physical-device test. |

The privacy checker is a bounded screening aid, not a proof that arbitrary files
are safe to publish. Review the exact release file list and content. It reads
only this checkout, prints finding categories without matching payloads, and
starts no service or network connection. Run it again after editing examples.

The public guide deliberately contains no live host inventory, private deployment
adapters, account bindings, application databases, configuration exports, tokens,
cookies or operator evidence. Its QA matrix remains NOT RUN for a reader's setup.


## Dockhand walkthrough example · 2026-10-23

| Check | Result | Evidence boundary |
|---|---|---|
| Fictional static demo, local Browser rendering | PASS | Six invented services; no app backend, Docker socket or JavaScript. |
| Requested viewport checks | PASS | Desktop 1200×800, portrait 390×844 and landscape 844×390; no document horizontal overflow. Scrollbar space reduces the measured client width. |
| Keyboard table scroll | PASS | ArrowRight moved the portrait table's internal scroll offset from 0 to 40 pixels. |
| Demo console sample | PASS | No errors or warnings in the captured sample. |
| Clean exported screenshots | PASS | Desktop and portrait viewport captures of the original fixture, labeled ILLUSTRATIVE MOCKUP. The exports are native JPEGs, not live app screenshots; no EXIF/comment metadata was retained. |
| Image/source screening | PASS | Reviewed screenshot hashes are pinned in the checker; other binary files remain review findings. Relative links and fictional values were checked. |
| Fixed-file preview policy checks | PASS | Expected files served by the handler; wrong Host, unknown paths and query aliases denied in synthetic tests. No app routes exist. |
| Real Nginx/native Dockhand deployment of this public example | NOT RUN | Included proxy fragments are nondeployable design examples; the owner-check placeholder denies everyone. |
| Physical phone / tailnet owner sign-in / restore exercise | NOT RUN | Demo responsive previews do not prove these outcomes. |

Run both read-only checks from the repository root:

```sh
python3 -I -B scripts/check_public_source.py
python3 -I -B scripts/check_dockhand_demo.py
```

The screenshot hashes refer only to the two reviewed original mockups. Recapture
and review any replacement image before changing those pins. Never whitelist a
live infrastructure screenshot just to make a source check pass.

## 2026-10-23 · Remaining app walkthroughs

Thirteen additional beginner guides, an index and original fictional fixtures were added. Grafana dashboard roles share one guide; identity user/admin destinations share one identity guide; custom portals and local tools use original teaching contracts. Pelican/Game Server Control remains excluded.

| Evidence | Result | Limit |
| --- | --- | --- |
| Read-only source privacy/link screen | PASS | Bounded patterns plus manual review; not a guarantee against every secret format |
| Original fixture checks | PASS | Local resources, no scripts/forms/remote assets, fixed-file handler tested synthetically |
| YAML/JSON fenced examples | Parsed during author review | Syntax only; no native app deployment or schema validation claimed |
| Browser desktop | 13/13 pages passed | Original static fixtures, not vendor interfaces |
| Browser portrait + reload | 13/13 pages passed | Viewport simulation; no physical phone used |
| Browser landscape | 13/13 pages passed | No horizontal document overflow observed |
| Clean public screenshots | 13 reviewed JPEG captures | Fictional original pages; no live infrastructure |
| Real native installations, access enforcement, inference, collectors and recovery | NOT RUN | Must be tested in each reader's own staging environment |

Requested viewports were 1200×800, 390×844 and 844×390 CSS pixels. Browser capture dimensions may differ. The local demo server is a loopback development tool, not an owner authentication gateway. No native application, identity, Tailscale route, secret or shared-sign-in setting was changed while preparing these additions. The new CSS targets only original fixtures and is not advertised as a universal native adapter.

Run the repository checks from its root:

```sh
python3 -I -B scripts/check_public_source.py
python3 -I -B scripts/check_dockhand_demo.py
python3 -I -B scripts/check_app_tour.py
```
