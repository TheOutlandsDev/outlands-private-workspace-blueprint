#!/usr/bin/env python3
"""One-shot CPU inference with a reviewed tiny model on a disposable runner."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


PROJECT = "outlands-ai-restore-example"
MODEL = "smollm2:135m"
# Ollama's public tag page showed this identifier and 271 MB on 2026-10-30.
# A changed tag must stop before generation. The full digest is logged safely.
EXPECTED_DIGEST = "9077fe9d2ae1"
MAX_MODEL_BYTES = 350_000_000

TAGS_SCRIPT = r"""
import json, urllib.request
with urllib.request.urlopen('http://ollama:11434/api/tags', timeout=15) as response:
    data = json.load(response)
models = data.get('models', [])
selected = [item for item in models if item.get('name') == 'smollm2:135m']
item = selected[0] if len(selected) == 1 else {}
print(json.dumps({'count': len(models), 'name': item.get('name'),
                  'digest': item.get('digest'), 'size': item.get('size')}))
"""

GENERATE_SCRIPT = r"""
import json, urllib.request
payload = {'model': 'smollm2:135m',
           'prompt': 'Describe a fictional red paper kite in one sentence.',
           'stream': False, 'keep_alive': 0,
           'options': {'num_predict': 32, 'temperature': 0}}
request = urllib.request.Request('http://ollama:11434/api/generate',
                                 data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(request, timeout=150) as response:
    raw = response.read(65537)
if len(raw) > 65536:
    raise ValueError('bounded response exceeded')
data = json.loads(raw)
print(json.dumps({'done': data.get('done') is True,
                  'nonempty': isinstance(data.get('response'), str)
                              and bool(data['response'].strip())}))
"""


def invoke(command, *, cwd=None, timeout=180, capture=True):
    try:
        result = subprocess.run(command, cwd=cwd, timeout=timeout, check=False,
                                stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, text=True)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("disposable inference operation unavailable") from None
    if result.returncode:
        raise RuntimeError("disposable inference operation failed")
    return result.stdout if capture else ""


def validate_model(data):
    digest = data.get("digest") if isinstance(data, dict) else None
    if (not isinstance(data, dict) or data.get("count") != 1
            or data.get("name") != MODEL or not isinstance(digest, str)
            or not re.fullmatch(r"[a-f0-9]{64}", digest)
            or not digest.startswith(EXPECTED_DIGEST)
            or type(data.get("size")) is not int
            or not 50_000_000 <= data["size"] <= MAX_MODEL_BYTES):
        raise RuntimeError("reviewed model identity or size changed")
    return digest


def validate_generation(data):
    if (not isinstance(data, dict) or data.get("done") is not True
            or data.get("nonempty") is not True):
        raise RuntimeError("fictional inference response incomplete")


def check(root: Path, call=invoke):
    if not (root / "ai-restored/.env").is_file():
        raise RuntimeError("disposable restored project required")
    folder = root / "ai-restored"
    compose = ["docker", "compose", "-p", PROJECT, "--env-file", ".env",
               "-f", "compose.yaml"]
    configured = json.loads(call(compose + ["config", "--format", "json"], cwd=folder, timeout=30))
    if configured.get("name") != PROJECT:
        raise RuntimeError("expected isolated inference project")
    container = call(compose + ["ps", "-q", "ollama"], cwd=folder, timeout=30).strip()
    if not re.fullmatch(r"[a-f0-9]{12,64}", container):
        raise RuntimeError("expected disposable Ollama container")
    devices = json.loads(call(["docker", "inspect", "--format",
                               "{{json .HostConfig.DeviceRequests}}", container], timeout=30))
    if devices not in (None, []):
        raise RuntimeError("CPU-only Docker device boundary")
    print("PASS disposable CPU-only Ollama container", flush=True)

    call(compose + ["exec", "-T", "ollama", "ollama", "pull", MODEL],
         cwd=folder, timeout=480, capture=False)
    print("PASS disposable reviewed model pull", flush=True)
    tags = call(compose + ["exec", "-T", "open-webui", "python3", "-I", "-B",
                           "-c", TAGS_SCRIPT], cwd=folder, timeout=45)
    digest = validate_model(json.loads(tags))
    print("RESOLVED disposable model digest sha256:" + digest, flush=True)

    generated = call(compose + ["exec", "-T", "open-webui", "python3", "-I", "-B",
                                "-c", GENERATE_SCRIPT], cwd=folder, timeout=180)
    validate_generation(json.loads(generated))
    print("PASS disposable CPU inference: nonempty fictional response", flush=True)


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        print("REVIEW: disposable GitHub Actions runner required", file=sys.stderr)
        return 2
    stage_root = os.environ.get("STAGE_ROOT", "")
    if not stage_root or not Path(stage_root).is_absolute():
        print("REVIEW: disposable staging directory required", file=sys.stderr)
        return 2
    root = Path(stage_root)
    try:
        check(root)
    except (RuntimeError, ValueError, TypeError, AttributeError) as error:
        # Errors are fixed labels; subprocess output and model text are never printed.
        print("REVIEW: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
