#!/usr/bin/env python3
"""Offline boundaries for the fictional metrics stack; no Docker or network."""
import json
from pathlib import Path
import re
import sys


QUERIES = {
    'up{job="fictional_fixture"}',
    'time() - outlands_demo_observed_at_seconds{job="fictional_fixture"}',
    'outlands_demo_value{job="fictional_fixture"}',
}


def check(root: Path) -> list[str]:
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    config = (root / "prometheus.yml").read_text(encoding="utf-8")
    env = (root / ".env.example").read_text(encoding="utf-8")
    source = (root / "provisioning/datasources/prometheus.yml").read_text(encoding="utf-8")
    provider = (root / "provisioning/dashboards/dashboards.yml").read_text(encoding="utf-8")
    dashboard = json.loads((root / "dashboards/synthetic-source.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "module.json").read_text(encoding="utf-8"))
    findings: list[str] = []
    expected_manifest = {
        "host_role": "server-01", "public_ports": [],
        "loopback_ports": ["PROMETHEUS_PORT", "GRAFANA_PORT"],
        "persistent_volumes": ["prometheus_data", "grafana_data"],
        "real_targets_included": False, "starts_by_default": False,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            findings.append("manifest_" + key)
    expected_ports = (
        '127.0.0.1:${PROMETHEUS_PORT:?Set PROMETHEUS_PORT}:9090',
        '127.0.0.1:${GRAFANA_PORT:?Set GRAFANA_PORT}:3000',
    )
    if compose.count("    ports:") != 2 or any(port not in compose for port in expected_ports):
        findings.append("loopback_ports")
    if any(token in compose for token in ("docker.sock", "network_mode: host", "privileged: true")):
        findings.append("privileged_or_host_access")
    if ('GF_SECURITY_ADMIN_PASSWORD: "$$__file{/run/secrets/grafana_admin_password}"' not in compose
            or "file: ${GRAFANA_PASSWORD_FILE:?" not in compose
            or 'GF_AUTH_ANONYMOUS_ENABLED: "false"' not in compose):
        findings.append("grafana_auth_boundary")
    if ("targets: [\"fixture:8000\"]" not in config or "job_name: fictional_fixture" not in config
            or "remote_write:" in config or config.count("targets:") != 1):
        findings.append("fictional_scrape_only")
    if "url: http://prometheus:9090" not in source or "uid: synthetic-prom" not in source:
        findings.append("internal_datasource")
    if "path: /etc/grafana/dashboards" not in provider or "allowUiUpdates: false" not in provider:
        findings.append("dashboard_provider")
    panels = dashboard.get("panels", [])
    if (len(panels) != 3 or {target.get("expr") for panel in panels for target in panel.get("targets", [])} != QUERIES
            or any(panel.get("datasource", {}).get("uid") != "synthetic-prom" for panel in panels)):
        findings.append("dashboard_queries")
    variables = dict(re.findall(r"(?m)^([A-Z][A-Z_]+)=(.*)$", env))
    for key in ("PYTHON_IMAGE", "PROMETHEUS_IMAGE", "GRAFANA_IMAGE"):
        if variables.get(key) != "":
            findings.append("nonblank_public_" + key)
    if variables.get("GRAFANA_PASSWORD_FILE") != ".secrets/grafana-admin-password":
        findings.append("private_secret_file")
    if variables.get("DEMO_MODE") != "fresh":
        findings.append("fictional_mode")
    return sorted(set(findings))


if __name__ == "__main__":
    issues = check(Path(__file__).resolve().parent)
    print(json.dumps({"result": "PASS" if not issues else "REVIEW", "findings": issues,
                      "network_requests": 0, "services_started": 0}, sort_keys=True))
    sys.exit(0 if not issues else 1)
