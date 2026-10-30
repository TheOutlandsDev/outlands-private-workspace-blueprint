#!/usr/bin/env python3
"""Copy only reviewed public runtime fixtures into a new private local directory."""

import argparse
import os
from pathlib import Path
import shutil
import sys

from check_assembly import check as check_assembly


ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "ai": (
        "compose.yaml", "compose.nvidia.yaml", ".env.example", "smoke_inference.py",
    ),
    "metrics": (
        "compose.yaml", ".env.example", "metrics_server.py", "prometheus.yml",
        "dashboards/synthetic-source.json",
        "provisioning/dashboards/dashboards.yml",
        "provisioning/datasources/prometheus.yml",
    ),
    "catalog": (
        "compose.yaml", ".env.example", "assets/mark.svg", "assets/netwall.svg",
        "config/bookmarks.yaml", "config/services.yaml", "config/settings.yaml",
        "config/widgets.yaml",
    ),
}
SOURCES = {
    "ai": "modules/ai/ollama-open-webui",
    "metrics": "modules/observability/synthetic-metrics",
    "catalog": "modules/catalog/homepage",
}
BLANK_INPUTS = {
    "ai": ("OLLAMA_IMAGE", "OPEN_WEBUI_IMAGE", "WEBUI_SECRET_KEY"),
    "metrics": ("PYTHON_IMAGE", "PROMETHEUS_IMAGE", "GRAFANA_IMAGE"),
    "catalog": ("HOMEPAGE_IMAGE", "PUID", "PGID"),
}


def prepare(root: Path, destination: Path) -> list[str]:
    if not destination.is_absolute() or destination.exists() or destination.is_symlink():
        return ["new_absolute_destination_required"]
    try:
        source_root = root.resolve(strict=True)
        parent = destination.parent.resolve(strict=True)
    except OSError:
        return ["source_or_parent_unavailable"]
    target_root = parent / destination.name
    if target_root.is_relative_to(source_root) or source_root.is_relative_to(target_root):
        return ["destination_must_be_outside_checkout"]
    if check_assembly(source_root):
        return ["public_worksheet_not_fictional"]

    for project, names in FILES.items():
        source_dir = source_root / SOURCES[project]
        for name in names:
            item = source_dir / name
            current = source_root
            linked_component = False
            for part in item.relative_to(source_root).parts:
                current = current / part
                linked_component |= current.is_symlink()
            if (linked_component or not item.is_file()
                    or not item.resolve().is_relative_to(source_root)):
                return ["reviewed_fixture_missing_or_linked"]
        template = (source_dir / ".env.example").read_text(encoding="utf-8")
        lines = template.splitlines()
        if any(lines.count(key + "=") != 1 for key in BLANK_INPUTS[project]):
            return ["public_template_must_keep_private_inputs_blank"]

    # All validation precedes creation. A later copy failure leaves the directory
    # visible for the reader to inspect; it is never silently removed or overwritten.
    target_root.mkdir(mode=0o700)
    os.chmod(target_root, 0o700)
    for project, names in FILES.items():
        project_dir = target_root / project
        project_dir.mkdir(mode=0o700)
        source_dir = source_root / SOURCES[project]
        for name in names:
            target = project_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_dir / name, target)
            os.chmod(target, 0o644)
        template = (project_dir / ".env.example").read_text(encoding="utf-8")
        with (project_dir / ".env").open("x", encoding="utf-8") as output:
            output.write(template)
        os.chmod(project_dir / ".env", 0o600)
    (target_root / "metrics/.secrets").mkdir(mode=0o700)
    shutil.copyfile(source_root / "hosts/server-01/assembly.example.json",
                    target_root / "acceptance.json")
    os.chmod(target_root / "acceptance.json", 0o600)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path,
                        help="new absolute local directory outside this checkout")
    args = parser.parse_args()
    try:
        findings = prepare(ROOT, args.destination)
    except (OSError, UnicodeError):
        print("REVIEW: private copy may be partial; inspect before retrying", file=sys.stderr)
        return 1
    if findings:
        print("REVIEW: " + ", ".join(findings), file=sys.stderr)
        return 1
    print("PASS private local copy prepared with blank inputs; no services started")
    return 0


if __name__ == "__main__":
    sys.exit(main())
