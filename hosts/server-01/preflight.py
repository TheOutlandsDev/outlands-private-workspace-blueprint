#!/usr/bin/env python3
"""Read-only local Docker readiness check for a reader-owned test host."""

import json
import os
import shutil
import subprocess
import sys


def check(*, environ=None, which=shutil.which, runner=subprocess.run):
    env = os.environ if environ is None else environ
    checks = {
        "python_3_9_or_newer": sys.version_info >= (3, 9),
        "docker_cli": False,
        "local_unix_context": False,
        "compose_plugin": False,
        "local_daemon_readable": False,
    }
    # An override can redirect an otherwise local-looking context to another host.
    if env.get("DOCKER_HOST") or env.get("DOCKER_CONTEXT"):
        return checks
    cli = which("docker")
    if not cli:
        return checks
    checks["docker_cli"] = True

    def call(*args):
        try:
            return runner([cli, *args], capture_output=True, text=True,
                          timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None

    context = call("context", "inspect", "--format", "{{.Endpoints.docker.Host}}")
    endpoint = context.stdout.strip() if context and context.returncode == 0 else ""
    if not endpoint.startswith("unix:///") or any(char.isspace() for char in endpoint):
        return checks
    checks["local_unix_context"] = True

    compose = call("compose", "version", "--short")
    checks["compose_plugin"] = bool(compose and compose.returncode == 0)
    if checks["compose_plugin"]:
        daemon = call("info", "--format", "{{.ServerVersion}}")
        checks["local_daemon_readable"] = bool(daemon and daemon.returncode == 0)
    return checks


def main():
    checks = check()
    passed = all(checks.values())
    print(json.dumps({"result": "PASS" if passed else "REVIEW", "checks": checks,
                      "services_started": 0}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
