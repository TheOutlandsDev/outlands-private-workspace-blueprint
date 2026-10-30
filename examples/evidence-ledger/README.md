# Fictional evidence ledger

This offline example shows how to record test states without turning a plan into a pass. It reads one bounded JSON file, validates its structure, and prints only status counts. It starts no service, makes no network request, and does not verify that an observation actually happened.

From the repository root:

```sh
python3 -I -B examples/evidence-ledger/check_ledger.py examples/evidence-ledger/ledger.example.json
python3 -I -B -m unittest discover -s examples/evidence-ledger -p 'test_*.py'
```

The supplied ledger is **fictional**. Every deployment check begins at `NOT_RUN`. A real operator should keep their own ledger and evidence references private; those records can reveal routes, users, devices, incidents, and backup locations.

Each check has an ID, stage, claim, status, and evidence. Stages are `source`, `browser`, `access`, `restore`, or `physical-device`. Status is `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`. `PASS` and `FAIL` require an evidence object with the corresponding stage kind and a short reference. `BLOCKED` and `NOT_RUN` require `null` evidence. A blocked check can be explained in a separate private note. The validator rejects duplicate IDs, duplicate JSON keys, mismatched evidence kinds, and oversized input. It does not inspect a referenced file, repeat a test, or evaluate whether a claim was worded honestly.

The program prints fixed error codes, not input text, paths, evidence references, or secrets. It is a record-shape check, not a redaction or publication tool. Read the [delivery method](../../docs/21-evidence-driven-delivery.md) before using the ledger to interpret results.
