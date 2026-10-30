#!/usr/bin/env python3
"""Check the public assembly worksheet without Docker, network, or host reads."""
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
MODULES = {
    "foundation": ("modules/foundation/docker-host/README.md", True),
    "ai": ("modules/ai/ollama-open-webui/README.md", False),
    "observability": ("modules/observability/synthetic-metrics/README.md", False),
    "private-entry": ("modules/access/private-entry/README.md", False),
}
TOP_KEYS = {
    "schema_version", "scope", "host_role", "shared_compose_project",
    "shared_service_network", "real_targets_included",
    "backup_destination_included", "modules", "optional_route",
}


def check(root: Path) -> list[str]:
    try:
        data = json.loads((root / "hosts/server-01/assembly.example.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["worksheet_unreadable"]
    if not isinstance(data, dict):
        return ["worksheet_shape"]
    findings = []
    if set(data) != TOP_KEYS or data.get("schema_version") != 1 or data.get("scope") != "fictional-assembly" or data.get("host_role") != "server-01":
        findings.append("fictional_scope")
    for key in ("shared_compose_project", "shared_service_network", "real_targets_included", "backup_destination_included"):
        if data.get(key) is not False:
            findings.append("independent_private_boundary")
    modules = data.get("modules")
    seen = set()
    if not isinstance(modules, list) or len(modules) != len(MODULES):
        findings.append("module_set")
    else:
        for module in modules:
            if not isinstance(module, dict) or set(module) != {"id", "path", "required", "status"}:
                findings.append("module_shape")
                continue
            identifier = module.get("id")
            if not isinstance(identifier, str) or identifier not in MODULES or identifier in seen:
                findings.append("module_set")
                continue
            seen.add(identifier)
            expected_path, required = MODULES[identifier]
            if module.get("path") != expected_path or module.get("required") is not required:
                findings.append("module_contract")
            if module.get("status") != "NOT_RUN":
                findings.append("unearned_result")
            if not (root / expected_path).is_file():
                findings.append("missing_module_guide")
        if seen != set(MODULES):
            findings.append("module_set")
    route = data.get("optional_route")
    if (not isinstance(route, dict) or set(route) != {"target_module", "example_backend", "status"}
            or route.get("target_module") != "ai"
            or route.get("example_backend") != "http://127.0.0.1:3001/"):
        findings.append("fictional_route_boundary")
    elif route.get("status") != "NOT_RUN":
        findings.append("unearned_result")
    return sorted(set(findings))


if __name__ == "__main__":
    issues = check(ROOT)
    print(json.dumps({"result": "PASS" if not issues else "REVIEW", "findings": issues,
                      "network_requests": 0, "services_started": 0}, sort_keys=True))
    sys.exit(0 if not issues else 1)
