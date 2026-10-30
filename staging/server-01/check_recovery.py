#!/usr/bin/env python3
"""One-shot fictional AI volume recovery on a disposable GitHub-hosted runner."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(os.environ["STAGE_ROOT"])
SOURCE_NAME = "outlands-ai-example"
RESTORE_NAME = "outlands-ai-restore-example"
VOLUME_KEYS = ("ollama_models", "open_webui_data")
EMAIL = "owner@example.invalid"


def require(condition, label):
    if not condition:
        raise RuntimeError(label)
    print("PASS", label, flush=True)


def run(command, *, cwd=None, timeout=180):
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        safe = result.stderr.strip()
        if command[:2] == ["docker", "run"] and safe in {
            "REVIEW: backup input or output boundary",
            "REVIEW: backup member boundary",
            "REVIEW: backup size boundary",
            "REVIEW: unsupported volume entry",
            "REVIEW: unsafe source symlink",
            "REVIEW: restore input or output boundary",
            "REVIEW: unsafe archive member",
            "REVIEW: unsafe archive symlink",
            "REVIEW: archive path escape",
            "REVIEW: archive file missing",
            "REVIEW: empty archive",
        }:
            raise RuntimeError(safe)
        # Captured Docker output can contain private environment values or app data.
        raise RuntimeError("disposable Docker operation failed")
    return result.stdout


def compose(folder, *args, project=None, timeout=180):
    command = ["docker", "compose"]
    if project:
        command += ["-p", project]
    command += ["--env-file", ".env", "-f", "compose.yaml", *args]
    return run(command, cwd=ROOT / folder, timeout=timeout)


def http(port, path, *, method="GET", data=None, token=None):
    headers = {"Accept": "application/json"}
    payload = None
    if data is not None:
        payload = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = Request(f"http://127.0.0.1:{port}{path}", data=payload,
                      headers=headers, method=method)
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, response.read(1_000_000)
    except HTTPError as error:
        return error.code, error.read(1_000_000)
    except (URLError, TimeoutError, ConnectionResetError):
        return 0, b""


def wait_health(port, label):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if http(port, "/health")[0] == 200:
            require(True, label)
            return
        time.sleep(2)
    raise RuntimeError(label + " timed out")


def volumes(folder, expected_name, *, project=None):
    config = json.loads(compose(folder, "config", "--format", "json", project=project))
    require(config.get("name") == expected_name, "expected isolated Compose project")
    defined = config.get("volumes", {})
    require(set(defined) == set(VOLUME_KEYS), "only two AI volumes defined")
    found = {key: defined[key].get("name") for key in VOLUME_KEYS}
    require(all(found[key] == expected_name + "_" + key for key in VOLUME_KEYS),
            "expected project-scoped volume names")
    return found


def helper(image, volume, archive_dir, action, kind):
    tool = Path(__file__).resolve().with_name("volume_transfer.py")
    volume_mode = ",readonly" if action in ("backup", "verify-marker") else ""
    archive_mode = ",readonly" if action in ("restore", "verify-marker") else ""
    command = [
        "docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only",
        "-e", "OUTLANDS_DISPOSABLE_RESTORE=1",
        "--mount", f"type=volume,source={volume},target=/volume{volume_mode}",
        "--mount", f"type=bind,source={archive_dir},target=/archive{archive_mode}",
        "--mount", f"type=bind,source={tool},target=/tool.py,readonly",
        image, "python3", "-I", "-B", "/tool.py", action, kind,
    ]
    run(command, timeout=180)
    require(True, "disposable " + kind + " volume " + action)


def signin(port, password):
    status, body = http(port, "/api/v1/auths/signin", method="POST",
                        data={"email": EMAIL, "password": password})
    if status != 200:
        return None
    data = json.loads(body)
    return data if data.get("role") == "admin" and data.get("token") else None


def check_auth(port, password, label):
    owner = signin(port, password)
    require(owner is not None, label + " fictional owner login")
    status, _ = http(port, "/api/v1/auths/signup", method="POST",
                     data={"name": "Second Fixture", "email": "second@example.invalid",
                           "password": password})
    require(status == 403, label + " second signup denied")
    status, _ = http(port, "/api/v1/auths/")
    require(status in (401, 403), label + " signed-out session denied")
    return owner["token"]


def assert_stopped(folder):
    for service in ("ollama", "open-webui"):
        container = compose(folder, "ps", "-a", "-q", service).strip()
        require(bool(container), "source container exists: " + service)
        running = run(["docker", "inspect", "--format", "{{.State.Running}}", container]).strip()
        require(running == "false", "source stopped before archive: " + service)


def main():
    require(os.environ.get("GITHUB_ACTIONS") == "true", "GitHub Actions only")
    image = os.environ.get("PYTHON_IMAGE", "")
    require("@sha256:" in image and not any(char.isspace() for char in image),
            "resolved helper image provided")
    require(ROOT.is_dir() and (ROOT / "ai/.env").is_file(), "disposable AI project exists")
    source_volumes = volumes("ai", SOURCE_NAME)
    for name in source_volumes.values():
        inspected = json.loads(run(["docker", "volume", "inspect", name]))
        require(len(inspected) == 1 and inspected[0].get("Name") == name,
                "source volume exists")

    password = (ROOT / "webui-test-password").read_text(encoding="utf-8").strip()
    compose("ai", "restart", "open-webui")
    wait_health(13001, "source WebUI ready after restart")
    token = check_auth(13001, password, "restarted source")

    compose("ai", "stop")
    assert_stopped("ai")
    archive_dir = ROOT / "recovery-archives"
    archive_dir.mkdir(mode=0o700)
    helper(image, source_volumes["ollama_models"], archive_dir, "mark", "ollama")
    for kind, key in (("ollama", "ollama_models"), ("webui", "open_webui_data")):
        helper(image, source_volumes[key], archive_dir, "backup", kind)
        require((archive_dir / (kind + ".tar.gz")).stat().st_size > 0,
                "disposable " + kind + " archive created")

    restored = ROOT / "ai-restored"
    require(not restored.exists(), "fresh restore project directory")
    shutil.copytree(ROOT / "ai", restored)
    env_file = restored / ".env"
    content = env_file.read_text(encoding="utf-8")
    require(content.count("WEBUI_PORT=13001") == 1, "expected fictional source port")
    env_file.write_text(content.replace("WEBUI_PORT=13001", "WEBUI_PORT=13011"),
                        encoding="utf-8")
    env_file.chmod(0o600)
    target_volumes = volumes("ai-restored", RESTORE_NAME, project=RESTORE_NAME)
    require(not set(source_volumes.values()) & set(target_volumes.values()),
            "restore volumes isolated from source")
    for name in target_volumes.values():
        exists = subprocess.run(["docker", "volume", "inspect", name],
                                capture_output=True, text=True, timeout=15)
        require(exists.returncode != 0, "restore volume absent before creation")
        require(run(["docker", "volume", "create", name]).strip() == name,
                "fresh restore volume created")
    for kind, key in (("ollama", "ollama_models"), ("webui", "open_webui_data")):
        helper(image, target_volumes[key], archive_dir, "restore", kind)
    helper(image, target_volumes["ollama_models"], archive_dir, "verify-marker", "ollama")

    compose("ai-restored", "up", "-d", "--no-build", project=RESTORE_NAME)
    wait_health(13011, "restored WebUI ready")
    container = compose("ai-restored", "ps", "-q", "open-webui", project=RESTORE_NAME).strip()
    inspected = json.loads(run(["docker", "inspect", "--format",
                                "{{json .HostConfig.PortBindings}}", container]))
    bindings = [item for entries in (inspected or {}).values() for item in (entries or [])]
    require(len(bindings) == 1 and bindings[0]["HostIp"] == "127.0.0.1"
            and bindings[0]["HostPort"] == "13011", "restored WebUI loopback only")
    ollama_container = compose("ai-restored", "ps", "-q", "ollama", project=RESTORE_NAME).strip()
    ollama_ports = json.loads(run(["docker", "inspect", "--format",
                                   "{{json .HostConfig.PortBindings}}", ollama_container]))
    require(not ollama_ports, "restored Ollama has no host port")

    status, body = http(13011, "/api/v1/auths/", token=token)
    require(status == 200 and json.loads(body).get("role") == "admin",
            "original fictional session accepted after restore")
    check_auth(13011, password, "restored project")
    compose("ai-restored", "exec", "-T", "open-webui", "python3", "-c",
            "import json,urllib.request; d=json.load(urllib.request.urlopen('http://ollama:11434/api/tags',timeout=10)); assert isinstance(d.get('models'),list)",
            project=RESTORE_NAME)
    require(True, "restored WebUI reaches internal Ollama API")
    print("PASS fictional AI recovery; no model, backup provider, or real host tested")


if __name__ == "__main__":
    main()
