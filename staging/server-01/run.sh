#!/usr/bin/env bash
# Disposable GitHub runner only. No repository, host, or operator data is mounted.
set -euo pipefail
umask 077
if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  printf 'REVIEW: disposable GitHub Actions runner required\n' >&2
  exit 2
fi

stage_root="$(mktemp -d)"
export STAGE_ROOT="$stage_root"

# Version tags come from upstream release lists. Resolve and record the pulled
# registry digests in this one disposable run before using Compose.
pull_digest() {
  local label="$1" tag="$2" digest
  docker pull "$tag" >/dev/null
  digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "$tag")"
  case "$digest" in
    *@sha256:*) ;;
    *) printf 'FAIL image digest resolution: %s\n' "$label" >&2; exit 1 ;;
  esac
  printf 'RESOLVED %s %s\n' "$label" "$digest" >&2
  printf '%s' "$digest"
}

HOMEPAGE_IMAGE="$(pull_digest homepage ghcr.io/gethomepage/homepage:v2.7.0)"
OLLAMA_IMAGE="$(pull_digest ollama ollama/ollama:0.40.13)"
OPEN_WEBUI_IMAGE="$(pull_digest open-webui ghcr.io/open-webui/open-webui:v0.12.5)"
PYTHON_IMAGE="$(pull_digest python python:3.13-slim)"
export PYTHON_IMAGE
PROMETHEUS_IMAGE="$(pull_digest prometheus prom/prometheus:v3.15.1)"
GRAFANA_IMAGE="$(pull_digest grafana grafana/grafana:13.3.0)"
test "$(docker image inspect --format '{{.Config.User}}' "$GRAFANA_IMAGE")" = '472'

cp -a modules/catalog/homepage "$stage_root/catalog"
cp -a modules/ai/ollama-open-webui "$stage_root/ai"
cp -a modules/observability/synthetic-metrics "$stage_root/metrics"
mkdir -m 700 "$stage_root/metrics/.secrets"
openssl rand -hex 32 > "$stage_root/metrics/.secrets/grafana-admin-password"
# The pinned Grafana 13 image runs as UID 472, GID 0. File-backed Compose
# secrets retain host ownership/mode, so grant only its group read access.
sudo chgrp 0 "$stage_root/metrics/.secrets/grafana-admin-password"
chmod 640 "$stage_root/metrics/.secrets/grafana-admin-password"
test "$(stat -c '%g:%a' "$stage_root/metrics/.secrets/grafana-admin-password")" = '0:640'
openssl rand -hex 32 > "$stage_root/webui-test-password"
webui_key="$(openssl rand -hex 32)"

cat > "$stage_root/catalog/.env" <<EOF
HOMEPAGE_IMAGE=$HOMEPAGE_IMAGE
CATALOG_PORT=13003
HOMEPAGE_ALLOWED_HOSTS=localhost:13003,127.0.0.1:13003
PUID=$(id -u)
PGID=$(id -g)
EOF
cat > "$stage_root/ai/.env" <<EOF
OLLAMA_IMAGE=$OLLAMA_IMAGE
OPEN_WEBUI_IMAGE=$OPEN_WEBUI_IMAGE
WEBUI_SECRET_KEY=$webui_key
WEBUI_PORT=13001
EOF
cat > "$stage_root/metrics/.env" <<EOF
PYTHON_IMAGE=$PYTHON_IMAGE
PROMETHEUS_IMAGE=$PROMETHEUS_IMAGE
GRAFANA_IMAGE=$GRAFANA_IMAGE
GRAFANA_PASSWORD_FILE=.secrets/grafana-admin-password
PROMETHEUS_PORT=13090
GRAFANA_PORT=13002
DEMO_MODE=fresh
EOF

for project in catalog ai metrics; do
  (cd "$stage_root/$project" && docker compose --env-file .env -f compose.yaml config --quiet)
  (cd "$stage_root/$project" && docker compose --env-file .env -f compose.yaml up -d --no-build)
  printf 'STARTED synthetic %s project\n' "$project"
done

python3 -I -B staging/server-01/check_runtime.py
node staging/server-01/check_browser.js
python3 -I -B staging/server-01/check_recovery.py

printf 'PASS synthetic native staging and disposable AI recovery; no model inference or private route tested\n'
