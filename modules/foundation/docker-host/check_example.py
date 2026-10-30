#!/usr/bin/env python3
"""Offline source boundary checks for the synthetic foundation smoke fixture."""
import json
from pathlib import Path
import sys


def check(root: Path) -> list[str]:
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    env = (root / ".env.example").read_text(encoding="utf-8")
    manifest = json.loads((root / "module.json").read_text(encoding="utf-8"))
    findings: list[str] = []
    expected_manifest = {
        "host_role": "server-01", "public_ports": [], "persistent_volumes": [],
        "smoke_network": "none", "starts_by_default": False,
    }
    for key, expected in expected_manifest.items():
        if manifest.get(key) != expected:
            findings.append("manifest_" + key)
    expected_lines = (
        "image: ${SMOKE_IMAGE:?", "network_mode: none", "read_only: true",
        "cap_drop:", "- ALL", "- no-new-privileges:true",
        'user: "65534:65534"', 'restart: "no"',
    )
    if any(line not in compose for line in expected_lines):
        findings.append("smoke_isolation")
    if any(token in compose for token in ("ports:", "volumes:", "privileged:", "docker.sock", "network_mode: host", "pid: host")):
        findings.append("host_exposure")
    if env.count("SMOKE_IMAGE=\n") != 1:
        findings.append("nonblank_public_image")
    return findings


if __name__ == "__main__":
    issues = check(Path(__file__).resolve().parent)
    print(json.dumps({"result": "PASS" if not issues else "REVIEW", "findings": issues,
                      "services_started": 0, "network_requests": 0}, sort_keys=True))
    sys.exit(0 if not issues else 1)
