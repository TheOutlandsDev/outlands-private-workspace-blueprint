#!/usr/bin/env python3
"""Validate a small evidence ledger without reading its evidence references."""

import json
from pathlib import Path
import re
import sys

MAX_BYTES = 65536
MAX_CHECKS = 64
STAGE_KIND = {
    "source": "source-check",
    "browser": "browser-observation",
    "access": "access-observation",
    "restore": "restore-observation",
    "physical-device": "device-observation",
}
STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN"}
IDENTIFIER = re.compile(r"[a-z][a-z0-9-]{2,63}\Z")


class LedgerError(Exception):
    """A fixed validation code safe to print without the input."""


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise LedgerError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def exact_keys(value, keys, code):
    if not isinstance(value, dict) or set(value) != keys:
        raise LedgerError(code)


def short_text(value, maximum):
    return (isinstance(value, str) and value == value.strip()
            and 8 <= len(value) <= maximum and "\n" not in value
            and "\r" not in value and all(ord(char) >= 32 for char in value))


def validate(document):
    exact_keys(document, {"schema_version", "project", "checks"}, "LEDGER_SHAPE")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise LedgerError("SCHEMA_VERSION")
    project = document["project"]
    if not isinstance(project, str) or not IDENTIFIER.fullmatch(project):
        raise LedgerError("PROJECT_ID")
    checks = document["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= MAX_CHECKS:
        raise LedgerError("CHECK_COUNT")
    seen = set()
    counts = {status: 0 for status in sorted(STATUSES)}
    for check in checks:
        exact_keys(check, {"id", "stage", "claim", "status", "evidence"}, "CHECK_SHAPE")
        check_id = check["id"]
        if not isinstance(check_id, str) or not IDENTIFIER.fullmatch(check_id):
            raise LedgerError("CHECK_ID")
        if check_id in seen:
            raise LedgerError("DUPLICATE_CHECK_ID")
        seen.add(check_id)
        stage = check["stage"]
        if not isinstance(stage, str) or stage not in STAGE_KIND:
            raise LedgerError("STAGE")
        if not short_text(check["claim"], 160):
            raise LedgerError("CLAIM")
        status = check["status"]
        if not isinstance(status, str) or status not in STATUSES:
            raise LedgerError("STATUS")
        evidence = check["evidence"]
        if status in {"PASS", "FAIL"}:
            exact_keys(evidence, {"kind", "reference"}, "EVIDENCE_SHAPE")
            if evidence["kind"] != STAGE_KIND[stage]:
                raise LedgerError("EVIDENCE_STAGE")
            if not short_text(evidence["reference"], 160):
                raise LedgerError("EVIDENCE_REFERENCE")
        elif evidence is not None:
            raise LedgerError("UNRUN_EVIDENCE")
        counts[status] += 1
    return {"result": "VALID", "checks": len(checks), "statuses": counts,
            "tests_executed": 0, "evidence_verified": False}


def main(argv):
    if len(argv) != 2:
        print("ERROR: USAGE")
        return 2
    path = Path(argv[1])
    try:
        if path.is_symlink() or not path.is_file():
            raise LedgerError("INPUT_TYPE")
        if path.stat().st_size > MAX_BYTES:
            raise LedgerError("INPUT_SIZE")
        document = json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=unique_pairs)
        summary = validate(document)
    except LedgerError as error:
        print(f"ERROR: {error}")
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        print("ERROR: INPUT")
        return 2
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
