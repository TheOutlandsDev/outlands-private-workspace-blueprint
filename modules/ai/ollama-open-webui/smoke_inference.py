#!/usr/bin/env python3
"""Opt-in Ollama smoke check; prechecks a local model and hides model output."""

import argparse
from pathlib import Path
import subprocess
import sys


PROMPT = "Describe a fictional red paper kite in one sentence."


def check(model: str, root: Path, gpu: bool = False, runner=subprocess.run) -> str:
    if not model or model != model.strip() or any(ch.isspace() for ch in model):
        raise ValueError("Enter one installed model reference without whitespace")
    if model.startswith("-") or len(model) > 256 or any(ord(ch) < 33 for ch in model):
        raise ValueError("Invalid model reference")
    env_file = root / ".env"
    if not env_file.is_file() or env_file.is_symlink() or env_file.stat().st_mode & 0o077:
        raise ValueError("Prepare a private, mode-0600-or-stricter .env in the module directory")

    command = ["docker", "compose", "--env-file", ".env", "-f", "compose.yaml"]
    if gpu:
        command += ["-f", "compose.nvidia.yaml"]

    # Resolve the existing project, then require an exact local inventory match.
    # This deliberately has no pull or create action.
    runner(command + ["config", "--quiet"], cwd=root, check=True,
           capture_output=True, text=True, timeout=30)
    listed = runner(command + ["exec", "-T", "ollama", "ollama", "ls"],
                    cwd=root, check=True, capture_output=True, text=True, timeout=30)
    installed = {line.split()[0] for line in listed.stdout.splitlines()[1:] if line.split()}
    if model not in installed:
        raise ValueError("Selected model is absent from this project's local inventory")

    generated = runner(command + ["exec", "-T", "ollama", "ollama", "run", model, PROMPT],
                       cwd=root, check=True, capture_output=True, text=True, timeout=300)
    if not generated.stdout.strip():
        raise ValueError("Ollama returned an empty response")
    return "PASS: installed model returned a nonempty response to the fictional prompt"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", action="store_true", help="Use the optional NVIDIA Compose overlay")
    options = parser.parse_args()
    if not sys.stdin.isatty():
        print("REVIEW: run interactively in a private terminal", file=sys.stderr)
        return 2
    try:
        model = input("Installed model reference (private terminal): ")
        print(check(model, Path(__file__).resolve().parent, options.gpu))
    except (ValueError, OSError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        # Do not print subprocess stderr: Compose and model errors can contain private inputs.
        print(f"REVIEW: {type(exc).__name__}; inspect privately", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
