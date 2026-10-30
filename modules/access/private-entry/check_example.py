#!/usr/bin/env python3
"""Validate only the fictional access-review fixture; never probe a network."""
import json
from pathlib import Path
import sys


EXPECTED = {
    "owner_allowed": "ALLOW_AFTER_APP_LOGIN",
    "signed_out": "DENY_PROTECTED_CONTENT",
    "app_unassigned": "APP_DENY",
    "network_unassigned": "NETWORK_DENY",
    "direct_app_route": "SAME_APP_AUTH",
    "public_internet": "UNREACHABLE",
    "foreground_stop": "ROUTE_REMOVED",
}


def check(root: Path) -> list[str]:
    plan = json.loads((root / "access-review.example.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "module.json").read_text(encoding="utf-8"))
    findings: list[str] = []
    if ({key: plan.get(key) for key in ("schema_version", "scope", "host_role", "example_route", "example_backend")}
            != {"schema_version": 1, "scope": "fictional-example", "host_role": "server-01",
                "example_route": "https://workspace.example.invalid/",
                "example_backend": "http://127.0.0.1:3001/"}):
        findings.append("fictional_route_boundary")
    if (manifest.get("host_role") != "server-01" or manifest.get("public_ports") != []
            or manifest.get("changes_tailnet_policy") is not False
            or manifest.get("starts_by_default") is not False):
        findings.append("manifest_boundary")
    checks = plan.get("checks")
    if not isinstance(checks, list) or len(checks) != len(EXPECTED):
        findings.append("check_set")
    else:
        seen: set[str] = set()
        for item in checks:
            if not isinstance(item, dict) or set(item) != {"id", "expected", "status"}:
                findings.append("check_shape")
                continue
            key = item["id"]
            if not isinstance(key, str):
                findings.append("check_expectation")
                continue
            if key in seen or EXPECTED.get(key) != item["expected"]:
                findings.append("check_expectation")
            seen.add(key)
            if item["status"] != "NOT_RUN":
                findings.append("unearned_result")
        if seen != set(EXPECTED):
            findings.append("check_set")
    return sorted(set(findings))


if __name__ == "__main__":
    issues = check(Path(__file__).resolve().parent)
    print(json.dumps({"result": "PASS" if not issues else "REVIEW", "findings": issues,
                      "checks": len(EXPECTED), "network_requests": 0, "services_started": 0}, sort_keys=True))
    sys.exit(0 if not issues else 1)
