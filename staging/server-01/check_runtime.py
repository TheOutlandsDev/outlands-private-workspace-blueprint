#!/usr/bin/env python3
"""Bounded native checks against disposable fictional Compose projects."""
import base64
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(os.environ["STAGE_ROOT"])
PORTS = {"catalog": 13003, "webui": 13001, "grafana": 13002, "prometheus": 13090}


def require(condition, label):
    if not condition:
        raise RuntimeError(label)
    print("PASS", label, flush=True)


def http(url, method="GET", data=None, headers=None):
    payload = json.dumps(data).encode() if data is not None else None
    all_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        all_headers["Content-Type"] = "application/json"
    request = Request(url, data=payload, headers=all_headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.read(1_000_000)
    except HTTPError as error:
        return error.code, error.read(1_000_000)
    except (URLError, TimeoutError, ConnectionResetError):
        return 0, b""


def wait_for(label, predicate, seconds=300):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            print("PASS", label, flush=True)
            return
        time.sleep(2)
    raise RuntimeError(label + " timed out")


def compose(project, *args):
    path = ROOT / project
    return subprocess.run(
        ["docker", "compose", "--env-file", ".env", "-f", "compose.yaml", *args],
        cwd=path, capture_output=True, text=True, timeout=180,
    )


def bindings(project, service):
    result = compose(project, "ps", "-q", service)
    require(result.returncode == 0 and bool(result.stdout.strip()), "container running: " + service)
    inspected = subprocess.run(
        ["docker", "inspect", "--format", "{{json .HostConfig.PortBindings}}", result.stdout.strip()],
        capture_output=True, text=True, timeout=15,
    )
    if inspected.returncode:
        raise RuntimeError("port inspection failed: " + service)
    data = json.loads(inspected.stdout)
    return [entry for entries in (data or {}).values() for entry in (entries or [])]


def query(expression):
    url = "http://127.0.0.1:13090/api/v1/query?" + urlencode({"query": expression})
    status, body = http(url)
    if status != 200:
        return None
    parsed = json.loads(body)
    if parsed.get("status") != "success":
        return None
    return parsed.get("data", {}).get("result", [])


def sample(expression):
    result = query(expression)
    return float(result[0]["value"][1]) if result and len(result) == 1 else None


def set_mode(old, new):
    env_path = ROOT / "metrics/.env"
    content = env_path.read_text(encoding="utf-8")
    token = "DEMO_MODE=" + old
    if content.count(token) != 1:
        raise RuntimeError("fictional mode fixture changed")
    env_path.write_text(content.replace(token, "DEMO_MODE=" + new), encoding="utf-8")
    result = compose("metrics", "up", "-d", "--no-deps", "--force-recreate", "fixture")
    require(result.returncode == 0, "fixture switched to " + new)


def main():
    expected = {
        ("catalog", "homepage"): 13003,
        ("ai", "open-webui"): 13001,
        ("ai", "ollama"): None,
        ("metrics", "grafana"): 13002,
        ("metrics", "prometheus"): 13090,
        ("metrics", "fixture"): None,
    }
    for (project, service), port in expected.items():
        actual = bindings(project, service)
        require((not actual if port is None else len(actual) == 1 and actual[0]["HostIp"] == "127.0.0.1" and int(actual[0]["HostPort"]) == port),
                "loopback binding: " + service)

    wait_for("Homepage HTTP ready", lambda: http("http://127.0.0.1:13003/")[0] == 200)
    wait_for("Open WebUI health ready", lambda: http("http://127.0.0.1:13001/health")[0] == 200)
    wait_for("Grafana health ready", lambda: http("http://127.0.0.1:13002/api/health")[0] == 200)
    wait_for("fictional Prometheus scrape", lambda: sample('up{job="fictional_fixture"}') == 1.0 and sample('outlands_demo_value{job="fictional_fixture"}') == 7.0)

    listed = compose("ai", "exec", "-T", "ollama", "ollama", "ls")
    require(listed.returncode == 0, "Ollama CLI available with no selected model")
    connected = compose("ai", "exec", "-T", "open-webui", "python3", "-c",
                        "import json,urllib.request; d=json.load(urllib.request.urlopen('http://ollama:11434/api/tags',timeout=10)); assert isinstance(d.get('models'),list)")
    require(connected.returncode == 0, "WebUI container reaches internal Ollama API")

    owner_password = (ROOT / "webui-test-password").read_text().strip()
    status, body = http("http://127.0.0.1:13001/api/v1/auths/signup", "POST",
                        {"name": "Fixture Owner", "email": "owner@example.invalid", "password": owner_password})
    require(status == 200, "fictional WebUI owner signup")
    owner = json.loads(body)
    token = owner.get("token")
    require(owner.get("role") == "admin" and isinstance(token, str) and bool(token), "first owner is admin")
    status, _ = http("http://127.0.0.1:13001/api/v1/auths/signup", "POST",
                     {"name": "Second Fixture", "email": "second@example.invalid", "password": owner_password})
    require(status == 403, "second WebUI signup denied")
    status, _ = http("http://127.0.0.1:13001/api/v1/auths/")
    require(status in (401, 403), "signed-out WebUI session denied")
    status, body = http("http://127.0.0.1:13001/api/v1/auths/", headers={"Authorization": "Bearer " + token})
    require(status == 200 and json.loads(body).get("role") == "admin", "fictional WebUI owner session")

    grafana_password = (ROOT / "metrics/.secrets/grafana-admin-password").read_text().strip()
    basic = base64.b64encode(("admin:" + grafana_password).encode()).decode()
    auth = {"Authorization": "Basic " + basic}
    datasource_url = "http://127.0.0.1:13002/api/datasources/uid/synthetic-prom"
    status, _ = http(datasource_url)
    require(status in (401, 403), "signed-out Grafana datasource denied")
    status, _ = http("http://127.0.0.1:13002/api/user", headers=auth)
    require(status == 200, "Grafana administrator basic auth accepted (HTTP " + str(status) + ")")
    status, body = http(datasource_url, headers=auth)
    require(status == 200 and json.loads(body).get("uid") == "synthetic-prom",
            "fictional Grafana datasource provisioned (HTTP " + str(status) + ")")
    dashboard_url = "http://127.0.0.1:13002/api/dashboards/uid/outlands-synthetic-source"
    wait_for("fictional Grafana dashboard provisioned", lambda: (
        (lambda response: response[0] == 200 and len(json.loads(response[1]).get("dashboard", {}).get("panels", [])) == 3)
        (http(dashboard_url, headers=auth))
    ))

    set_mode("fresh", "stale")
    wait_for("stale observation remains up", lambda: sample('up{job="fictional_fixture"}') == 1.0 and (sample('time() - outlands_demo_observed_at_seconds{job="fictional_fixture"}') or 0) >= 550, 90)
    set_mode("stale", "unavailable")
    wait_for("unavailable source is down", lambda: sample('up{job="fictional_fixture"}') == 0.0 and query('outlands_demo_value{job="fictional_fixture"}') == [], 90)
    set_mode("unavailable", "fresh")
    wait_for("fictional source recovers", lambda: sample('up{job="fictional_fixture"}') == 1.0 and sample('outlands_demo_value{job="fictional_fixture"}') == 7.0, 90)


if __name__ == "__main__":
    main()
