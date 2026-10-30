#!/usr/bin/env python3
"""Check the fictional catalog source without Docker, HTTP, or a browser."""
import hashlib
import json
from pathlib import Path
import re
import sys


def check(root: Path) -> list[str]:
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    env = (root / ".env.example").read_text(encoding="utf-8")
    services = (root / "config/services.yaml").read_text(encoding="utf-8")
    settings = (root / "config/settings.yaml").read_text(encoding="utf-8")
    manifest = json.loads((root / "module.json").read_text(encoding="utf-8"))
    findings: list[str] = []
    expected_manifest = {
        "host_role": "server-01", "public_ports": [],
        "loopback_ports": ["CATALOG_PORT"], "persistent_bind_mounts": ["config"],
        "linked_apps_deployed": False, "native_auth_replaced": False,
        "starts_by_default": False,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            findings.append("manifest_" + key)
    service_names = re.findall(r"(?m)^  ([a-z][a-z-]*):\s*$", compose)
    if service_names != ["homepage"]:
        findings.append("one_catalog_service")
    if (compose.count("    ports:") != 1
            or '127.0.0.1:${CATALOG_PORT:?Set a free local port}:3000' not in compose):
        findings.append("catalog_loopback")
    if ("${HOMEPAGE_IMAGE:?" not in compose
            or "${HOMEPAGE_ALLOWED_HOSTS:?" not in compose
            or "${PUID:?" not in compose or "${PGID:?" not in compose):
        findings.append("required_private_inputs")
    if any(token in compose for token in ("docker.sock", "network_mode: host", "privileged: true", "\nnetworks:")):
        findings.append("host_or_network_access")
    if "./assets:/app/public/outlands:ro" not in compose:
        findings.append("bounded_artwork_mount")
    variables = dict(re.findall(r"(?m)^([A-Z][A-Z_]+)=(.*)$", env))
    for key in ("HOMEPAGE_IMAGE", "PUID", "PGID"):
        if variables.get(key) != "":
            findings.append("nonblank_public_" + key)
    if variables.get("CATALOG_PORT") != "3003" or variables.get("HOMEPAGE_ALLOWED_HOSTS") != "localhost:3003,127.0.0.1:3003":
        findings.append("example_allowed_hosts")
    links = re.findall(r"(?m)^\s*href:\s*(\S+)\s*$", services)
    if links != ["https://webui.example.invalid/", "https://metrics.example.invalid/"]:
        findings.append("fictional_links_only")
    if ("Open WebUI:" not in services or "Grafana:" not in services
            or any(token in services for token in ("widget:", "ping:", "siteMonitor:", "apiKey:", "password:"))):
        findings.append("links_not_integrations")
    if "FICTIONAL CATALOG" not in settings or "disableSearch: true" not in settings:
        findings.append("fictional_settings")
    if "image: /outlands/netwall.svg" not in settings or services.count("icon: /outlands/mark.svg") != 2:
        findings.append("original_artwork_reference")
    assets = {
        "mark.svg": "97ebfb835ba96dc597f288ecd821fa37b8deacecdae3c848849689831aca7ef4",
        "netwall.svg": "712e71ace42b04b036d054a6e2ca9a48985572bc97358dc23c4483946fc6895a",
    }
    for name, expected_hash in assets.items():
        try:
            actual_hash = hashlib.sha256((root / "assets" / name).read_bytes()).hexdigest()
        except OSError:
            actual_hash = ""
        if actual_hash != expected_hash:
            findings.append("reviewed_artwork_changed")
    for name in ("widgets.yaml", "bookmarks.yaml"):
        if (root / "config" / name).read_text(encoding="utf-8").strip() != "[]":
            findings.append("no_widgets_or_bookmarks")
    return sorted(set(findings))


if __name__ == "__main__":
    issues = check(Path(__file__).resolve().parent)
    print(json.dumps({"result": "PASS" if not issues else "REVIEW", "findings": issues,
                      "network_requests": 0, "services_started": 0}, sort_keys=True))
    sys.exit(0 if not issues else 1)
