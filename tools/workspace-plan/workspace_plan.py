#!/usr/bin/env python3
"""Render a fictional dependency plan. No discovery, deployment, or network."""
import json
from pathlib import Path
import re
import sys

FIXTURE = Path(__file__).with_name('systems.example.json')
PROFILES = {'minimal', 'workspace', 'extended'}
COVERAGE = {'REFERENCE', 'REHEARSAL', 'DESIGN_ONLY'}
GATES = ('source_review', 'isolated_setup', 'allowed_access', 'denied_access',
         'state_retention', 'isolated_restore', 'rollback')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r'[a-z][a-z-]{0,31}', value)


def valid_list(value):
    return (isinstance(value, list) and len(value) <= 16
            and all(valid_id(item) for item in value)
            and len(set(value)) == len(value))


def validate(data):
    if (not isinstance(data, dict)
            or set(data) != {'schema_version', 'synthetic_fixture', 'systems', 'profiles'}
            or type(data['schema_version']) is not int or data['schema_version'] != 1
            or data['synthetic_fixture'] is not True):
        raise ValueError('fixture contract')
    systems = data['systems']
    if not isinstance(systems, list) or not 1 <= len(systems) <= 16:
        raise ValueError('system bound')
    index = {}
    for item in systems:
        if (not isinstance(item, dict) or set(item) != {'id', 'requires', 'coverage'}
                or not valid_id(item['id']) or not valid_list(item['requires'])
                or not isinstance(item['coverage'], str) or item['coverage'] not in COVERAGE
                or item['id'] in index):
            raise ValueError('system contract')
        index[item['id']] = item
    for item in systems:
        if any(dep not in index for dep in item['requires']):
            raise ValueError('missing dependency')
    profiles = data['profiles']
    if not isinstance(profiles, dict) or set(profiles) != PROFILES:
        raise ValueError('profile contract')
    for selected in profiles.values():
        if not valid_list(selected) or not selected or any(s not in index for s in selected):
            raise ValueError('profile selection')
    # Validate the entire graph, including systems outside the selected profile.
    order_systems(index, list(index))
    return index


def order_systems(index, selected):
    visiting, complete, ordered = set(), set(), []

    def visit(system):
        if system in visiting:
            raise ValueError('dependency cycle')
        if system in complete:
            return
        visiting.add(system)
        for dependency in index[system]['requires']:
            visit(dependency)
        visiting.remove(system)
        complete.add(system)
        ordered.append(system)

    for system in selected:
        visit(system)
    return ordered


def make_plan(data, profile='workspace'):
    index = validate(data)
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError('unknown profile')
    return {
        'schema_version': 1, 'synthetic_fixture': True, 'profile': profile,
        'deployment_authorized': False,
        'steps': [
            {'system': system, 'coverage': index[system]['coverage'],
             'requires': list(index[system]['requires']),
             'acceptance': {gate: 'NOT_RUN' for gate in GATES}}
            for system in order_systems(index, data['profiles'][profile])
        ],
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) > 1 or (args and args[0] not in PROFILES):
            raise ValueError('profile selection')
        if FIXTURE.is_symlink() or FIXTURE.stat().st_size > 16_384:
            raise ValueError('fixture bound')
        data = json.loads(FIXTURE.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
        plan = make_plan(data, args[0] if args else 'workspace')
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        # No supplied value, private path, or exception text enters the output.
        print(json.dumps({'result': 'REVIEW', 'deployment_authorized': False}, sort_keys=True))
        return 1
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
