# Fictional workspace planner

Turn the [systems blueprint](../../docs/25-systems-blueprint.md) into an ordered
learning plan. This standard-library Python tool reads only its adjacent public
fixture and prints JSON. It discovers no host, reads no environment or operator
configuration, starts no service, and writes no file.

From the repository root, using Python 3.9+:

```sh
python3 -I -B tools/workspace-plan/workspace_plan.py minimal
python3 -I -B tools/workspace-plan/workspace_plan.py workspace
python3 -I -B tools/workspace-plan/workspace_plan.py extended
python3 -I -B -m unittest discover -s tools/workspace-plan -p 'test_*.py'
```

No argument selects `workspace`. `minimal` covers foundation, AI and recovery;
`workspace` adds fictional monitoring and the catalog. `extended` also shows
optional private entry and the design-only identity, source-inventory, retrieval,
and security-review roles. These are dependencies for this learning sequence,
not universal software requirements. For example, a real catalog need not run
an AI service. Every acceptance gate remains `NOT_RUN`, and every plan says
`deployment_authorized=false`.

The fixture admits at most 16 systems, fixed profile names, simple role IDs,
dependency IDs, and coverage labels. Unknown fields, duplicate JSON keys,
missing dependencies, cycles anywhere in the graph, and claimed deployment
states are refused. Errors print a fixed `REVIEW` response without echoing input.
The fixture is limited to 16 KiB. Keep private inventories and completed
worksheets elsewhere; this is not an importer or a deployment manager.

Read the [setup sequence](../../docs/26-workspace-setup.md) and
[engineering methods](../../docs/27-engineering-methods.md) before applying a
plan to an isolated reader-owned environment. Offline ordering and refusal
tests establish only planner behavior, not app compatibility or live readiness.
