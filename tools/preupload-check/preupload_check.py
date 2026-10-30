#!/usr/bin/env python3
"""Offline, exact-file pre-upload screen for a staged public text export.

This is a bounded review aid. It never grants publication approval.
"""

import hashlib
import ipaddress
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import posixpath
import re
import stat
import sys
from urllib.parse import unquote

MAX_INPUT = 65_536
MAX_FILES = 128
MAX_ENTRIES = 256
MAX_FILE = 2_000_000
MAX_TOTAL = 8_000_000
SEGMENT = re.compile(r"[A-Za-z0-9._-]+\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
SAFE_EMAIL_DOMAINS = {"example.com", "example.org", "example.invalid"}
EXAMPLE_IP_RANGES = tuple(ipaddress.ip_network(block) for block in
                          ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24"))
FORBIDDEN_SUFFIXES = {".key", ".pem", ".db", ".sqlite", ".sqlite3", ".p12", ".pfx"}
FORBIDDEN_SEGMENTS = {".secrets", "secrets", ".git", "__pycache__"}
PATTERNS = {
    "PRIVATE_PATH": re.compile(r"/(?:home|srv)/[A-Za-z0-9_-]+"),
    "TAILNET_NAME": re.compile(r"\btail[a-f0-9]{6}\.ts\.net\b"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GITHUB_TOKEN": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"),
    "CLOUD_KEY": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}
MARKDOWN_LINK = re.compile(r"\]\(([^)]+)\)")
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


class GateError(Exception):
    """Fixed error code; never carry input text into the CLI."""


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise GateError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(_value):
    raise GateError("JSON_CONSTANT")


def valid_path(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 240:
        raise GateError("PATH")
    parts = value.split("/")
    if any(part in {"", ".", ".."} or not SEGMENT.fullmatch(part) for part in parts):
        raise GateError("PATH")
    return value


def read_json(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_INPUT:
        raise GateError("INPUT_TYPE_OR_SIZE")
    fd = os.open(path, FILE_FLAGS)
    try:
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino, current.st_size) != (info.st_dev, info.st_ino, info.st_size):
            raise GateError("INPUT_CHANGED")
        data = os.read(fd, MAX_INPUT + 1)
        if len(data) != info.st_size or os.fstat(fd).st_size != info.st_size:
            raise GateError("INPUT_CHANGED")
    finally:
        os.close(fd)
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_pairs,
                      parse_constant=reject_constant)


def read_manifest(path):
    doc = read_json(path)
    if (type(doc) is not dict or set(doc) != {"schema_version", "repository", "base_commit", "files"}
            or type(doc["schema_version"]) is not int or doc["schema_version"] != 1
            or not isinstance(doc["repository"], str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", doc["repository"])
            or not isinstance(doc["base_commit"], str)
            or not re.fullmatch(r"[a-f0-9]{40}", doc["base_commit"])):
        raise GateError("MANIFEST_SHAPE")
    rows = doc["files"]
    if type(rows) is not list or not 1 <= len(rows) <= MAX_FILES:
        raise GateError("FILE_COUNT")
    names = []
    for row in rows:
        if (type(row) is not dict or set(row) != {"path", "sha256", "synthetic_fixture"}
                or not isinstance(row["sha256"], str) or not SHA256.fullmatch(row["sha256"])
                or type(row["synthetic_fixture"]) is not bool):
            raise GateError("MANIFEST_FILE")
        names.append(valid_path(row["path"]))
    if names != sorted(set(names)):
        raise GateError("MANIFEST_ORDER_OR_DUPLICATE")
    return doc


def read_base_paths(path):
    doc = read_json(path)
    if (type(doc) is not dict or set(doc) != {"schema_version", "base_commit", "paths"}
            or type(doc["schema_version"]) is not int or doc["schema_version"] != 1
            or not isinstance(doc["base_commit"], str)
            or type(doc["paths"]) is not list or len(doc["paths"]) > 1000):
        raise GateError("BASE_PATHS_SHAPE")
    names = [valid_path(value) for value in doc["paths"]]
    if names != sorted(set(names)):
        raise GateError("BASE_PATHS_ORDER_OR_DUPLICATE")
    return doc


def read_private_terms(path):
    info = path.lstat()
    if info.st_uid != os.getuid() or (info.st_mode & 0o077):
        raise GateError("PRIVATE_TERMS_PERMISSIONS")
    doc = read_json(path)
    if (type(doc) is not dict or set(doc) != {"schema_version", "terms"}
            or type(doc["schema_version"]) is not int or doc["schema_version"] != 1
            or type(doc["terms"]) is not list or not 1 <= len(doc["terms"]) <= 64):
        raise GateError("PRIVATE_TERMS_SHAPE")
    terms = doc["terms"]
    if (any(not isinstance(value, str) or not 4 <= len(value) <= 128
            or any(ord(char) < 32 for char in value) for value in terms)
            or len({value.casefold() for value in terms}) != len(terms)):
        raise GateError("PRIVATE_TERMS_SHAPE")
    return [value.casefold() for value in terms]


def scan_stage(root):
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode):
        raise GateError("STAGE_TYPE")
    found = {}
    entries_seen = 0
    total = 0

    def visit(dir_fd, prefix):
        nonlocal entries_seen, total
        with os.scandir(dir_fd) as entries:
            for entry in entries:
                entries_seen += 1
                if entries_seen > MAX_ENTRIES:
                    raise GateError("ENTRY_LIMIT")
                name = f"{prefix}/{entry.name}" if prefix else entry.name
                valid_path(name)
                item = os.stat(entry.name, dir_fd=dir_fd, follow_symlinks=False)
                if stat.S_ISDIR(item.st_mode):
                    child = os.open(entry.name, DIR_FLAGS, dir_fd=dir_fd)
                    try:
                        current = os.fstat(child)
                        if (current.st_dev, current.st_ino) != (item.st_dev, item.st_ino):
                            raise GateError("STAGE_CHANGED")
                        visit(child, name)
                    finally:
                        os.close(child)
                    continue
                if not stat.S_ISREG(item.st_mode) or item.st_nlink != 1:
                    raise GateError("LINK_OR_SPECIAL_FILE")
                if len(found) >= MAX_FILES or item.st_size > MAX_FILE or total + item.st_size > MAX_TOTAL:
                    raise GateError("SIZE_OR_COUNT_LIMIT")
                fd = os.open(entry.name, FILE_FLAGS, dir_fd=dir_fd)
                try:
                    current = os.fstat(fd)
                    if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
                            or (current.st_dev, current.st_ino, current.st_size)
                            != (item.st_dev, item.st_ino, item.st_size)):
                        raise GateError("STAGE_CHANGED")
                    data = bytearray()
                    while len(data) <= item.st_size:
                        chunk = os.read(fd, min(65_536, item.st_size + 1 - len(data)))
                        if not chunk:
                            break
                        data.extend(chunk)
                    if len(data) != item.st_size or os.fstat(fd).st_size != item.st_size:
                        raise GateError("STAGE_CHANGED")
                finally:
                    os.close(fd)
                found[name] = bytes(data)
                total += len(data)

    fd = os.open(root, DIR_FLAGS)
    try:
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
            raise GateError("STAGE_CHANGED")
        visit(fd, "")
    finally:
        os.close(fd)
    return found


def check_link(origin, target, known):
    destination = target.split("#", 1)[0].split("?", 1)[0]
    if not destination:
        return None
    if destination.startswith(("https://", "http://", "mailto:")):
        return None
    if ":" in destination or destination.startswith(("/", "\\")):
        return "UNSAFE_LINK"
    decoded = unquote(destination)
    if "\\" in decoded or decoded.startswith("/"):
        return "UNSAFE_LINK"
    normalized = posixpath.normpath(posixpath.join(posixpath.dirname(origin), decoded))
    if normalized == ".." or normalized.startswith("../"):
        return "UNSAFE_LINK"
    if normalized not in known:
        return "MISSING_LINK_TARGET"
    return None


def evaluate(manifest, base_paths, found, private_terms):
    expected = {row["path"]: row for row in manifest["files"]}
    findings = []
    if manifest["base_commit"] != base_paths["base_commit"]:
        findings.append({"check": "BASE_COMMIT_MISMATCH"})
    for path in sorted(set(found) - set(expected)):
        findings.append({"path": path, "check": "EXTRA_FILE"})
    for path in sorted(set(expected) - set(found)):
        findings.append({"path": path, "check": "MISSING_FILE"})
    known = set(base_paths["paths"]) | set(expected)
    rows = []
    for path in sorted(set(expected) & set(found)):
        data = found[path]
        digest = hashlib.sha256(data).hexdigest()
        rows.append({"path": path, "bytes": len(data), "sha256": digest,
                     "synthetic_fixture": expected[path]["synthetic_fixture"]})
        if digest != expected[path]["sha256"]:
            findings.append({"path": path, "check": "HASH_CHANGED"})
        parts = path.split("/")
        if (set(parts) & FORBIDDEN_SEGMENTS or Path(path).suffix.lower() in FORBIDDEN_SUFFIXES
                or (parts[-1].startswith(".env") and parts[-1] != ".env.example")):
            findings.append({"path": path, "check": "PRIVATE_FILE_TYPE"})
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append({"path": path, "check": "BINARY_REQUIRES_SEPARATE_REVIEW"})
            continue
        if "\x00" in text:
            findings.append({"path": path, "check": "BINARY_REQUIRES_SEPARATE_REVIEW"})
            continue
        if any(term in path.casefold() or term in text.casefold() for term in private_terms):
            findings.append({"path": path, "check": "PRIVATE_TERM"})
        for check, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append({"path": path, "check": check})
        for raw in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text):
            try:
                address = ipaddress.ip_address(raw)
            except ValueError:
                continue
            if (not address.is_global and not address.is_loopback
                    and not any(address in block for block in EXAMPLE_IP_RANGES)):
                findings.append({"path": path, "check": "PRIVATE_NETWORK_ADDRESS"})
                break
        for domain in re.findall(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text):
            if domain.lower() not in SAFE_EMAIL_DOMAINS:
                findings.append({"path": path, "check": "NONEXAMPLE_EMAIL"})
                break
        if path.endswith(".md"):
            for raw in MARKDOWN_LINK.findall(text):
                target = raw.strip().split(" ", 1)[0].strip("<>")
                check = check_link(path, target, known)
                if check:
                    findings.append({"path": path, "check": check})
    return rows, findings


def write_receipt(destination, stage, manifest, rows, findings):
    parent = destination.parent.resolve(strict=True)
    mode = parent.stat().st_mode
    if not stat.S_ISDIR(mode) or (mode & 0o077) or parent.stat().st_uid != os.getuid():
        raise GateError("RECEIPT_PARENT_NOT_PRIVATE")
    if destination.resolve(strict=False).is_relative_to(stage.resolve(strict=True)):
        raise GateError("RECEIPT_INSIDE_STAGE")
    destination.mkdir(mode=0o700)
    result = "PASS" if not findings else "REVIEW"
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    report = {"schema_version": 1, "observed_utc": observed, "result": result,
              "publication_authorized": False,
              "repository": manifest["repository"], "base_commit": manifest["base_commit"],
              "files_checked": len(rows), "bytes_checked": sum(row["bytes"] for row in rows),
              "files": rows, "findings": findings,
              "manual_reviews": {"privacy": "PENDING", "synthetic_data": "PENDING",
                                 "provenance_and_rights": "PENDING", "diff": "PENDING",
                                 "destination_and_history": "PENDING"},
              "network_requests": 0, "services_started": 0}
    md = ("# Local pre-upload review receipt\n\n"
          f"Observed UTC: {observed}\n\n"
          f"Result: {result}\n\nRepository: {manifest['repository']}\n\n"
          f"Base commit supplied: `{manifest['base_commit']}` (not verified online by this command).\n\n"
          f"Files checked: {len(rows)}; bytes checked: {report['bytes_checked']}; findings: {len(findings)}.\n\n"
          "This is an offline text and link screen on the selected bytes. Publication authorization: **NO**. "
          "Manual review of privacy, synthetic data, provenance and rights, exact diff, destination and Git history remains pending. "
          "A clean result does not prove these claims. The JSON receipt contains paths, hashes and finding codes; keep it private.\n")
    for name, body in (("report.json", json.dumps(report, indent=2, sort_keys=True) + "\n"),
                       ("REVIEW.md", md), ("REVIEW.txt", md)):
        fd = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(body)
            output.flush()
            os.fsync(output.fileno())
    return result, len(rows), len(findings)


def main(argv):
    if len(argv) != 6:
        print("ERROR: USAGE")
        return 2
    try:
        manifest = read_manifest(Path(argv[1]))
        stage = Path(argv[2])
        base_paths = read_base_paths(Path(argv[3]))
        private_terms = read_private_terms(Path(argv[4]))
        found = scan_stage(stage)
        rows, findings = evaluate(manifest, base_paths, found, private_terms)
        result, count, issues = write_receipt(Path(argv[5]), stage, manifest, rows, findings)
    except GateError as error:
        print(f"ERROR: {error}")
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RuntimeError):
        print("ERROR: INPUT_OR_OUTPUT")
        return 2
    print(f"{result}: files={count} findings={issues} publication_authorized=false")
    return 0 if result == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
