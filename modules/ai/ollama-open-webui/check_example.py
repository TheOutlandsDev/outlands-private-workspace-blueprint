#!/usr/bin/env python3
"""Offline checks for the published server-01 AI example; no Docker or network."""
import json
from pathlib import Path
import re
import sys


def check(root: Path) -> list[str]:
    compose = (root / "compose.yaml").read_text(encoding="utf-8")
    env = (root / ".env.example").read_text(encoding="utf-8")
    manifest = json.loads((root / "module.json").read_text(encoding="utf-8"))
    findings: list[str] = []
    service = re.search(r"(?ms)^  ollama:\n(.*?)(?=^  open-webui:)", compose)
    ollama = service.group(1) if service else ""
    expected = {
        "host_role": "server-01",
        "public_ports": [],
        "loopback_ports": ["WEBUI_PORT"],
        "persistent_volumes": ["ollama_models", "open_webui_data"],
        "starts_by_default": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            findings.append("manifest_" + key)
    if not service or "ports:" in ollama or "network_mode: host" in ollama:
        findings.append("ollama_host_exposure")
    if '127.0.0.1:${WEBUI_PORT:?Set WEBUI_PORT}:8080' not in compose:
        findings.append("webui_loopback")
    if "OLLAMA_BASE_URL: http://ollama:11434" not in compose:
        findings.append("ollama_internal_url")
    if "docker.sock" in compose or "/root/.ollama" not in compose or "/app/backend/data" not in compose:
        findings.append("state_or_socket_boundary")
    if "${WEBUI_SECRET_KEY:?" not in compose or 'WEBUI_AUTH: "true"' not in compose:
        findings.append("authentication_inputs")
    variables = dict(re.findall(r"(?m)^([A-Z][A-Z_]+)=(.*)$", env))
    for key in ("OLLAMA_IMAGE", "OPEN_WEBUI_IMAGE", "WEBUI_SECRET_KEY"):
        if variables.get(key) != "":
            findings.append("nonblank_public_" + key)
    if variables.get("WEBUI_PORT") != "3001":
        findings.append("example_port")
    return findings


if __name__ == "__main__":
    issues = check(Path(__file__).resolve().parent)
    print(json.dumps({"result": "PASS" if not issues else "REVIEW", "findings": issues,
                      "services_started": 0, "network_requests": 0}, sort_keys=True))
    sys.exit(0 if not issues else 1)
