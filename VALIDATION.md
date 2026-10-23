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
