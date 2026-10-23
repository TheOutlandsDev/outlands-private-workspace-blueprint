# Validation boundaries

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
