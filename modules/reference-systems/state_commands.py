"""Explicit offline administration and a disposable synthetic recovery rehearsal."""
from pathlib import Path
import tempfile

from state_store import CURRENT_SCHEMA, StateStore, restore


def options(args, required=(), optional=()):
    if len(args) % 2:
        raise ValueError('option pairs required')
    result = {}
    for offset in range(0, len(args), 2):
        key, value = args[offset:offset + 2]
        if key not in set(required) | set(optional) or key in result or not value:
            raise ValueError('unknown or duplicate option')
        result[key] = value
    if not set(required) <= set(result):
        raise ValueError('missing option')
    return result


def number(value):
    if not 1 <= len(value) <= 7 or not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 1_000_000:
        raise ValueError('generation')
    return int(value)


def reset(store, seed, expected, confirmation):
    if confirmation != 'RESET-SYNTHETIC-STATE' or store.payload['schema_version'] != CURRENT_SCHEMA:
        raise ValueError('explicit current-schema reset required')
    payload = seed()
    payload['reset_count'] = store.payload['reset_count'] + 1
    store.commit(payload, expected)


def rehearsal(seed):
    with tempfile.TemporaryDirectory(prefix='outlands-synthetic-state-') as temporary:
        parent = Path(temporary)
        original = seed()
        original.pop('reset_count')
        original['schema_version'] = 1
        with StateStore.create(parent / 'state', original) as store:
            store.upgrade(store.generation)
            payload = store.payload
            payload['scenario'] = 'stale'
            payload['corpus']['documents'] = [d for d in payload['corpus']['documents'] if d['id'] != 'fictional-owner-note']
            store.commit(payload)
            store.backup(parent / 'snapshot.json')
            committed = store.payload
        with StateStore(parent / 'state') as store:
            if store.payload != committed:
                raise ValueError('restart mismatch')
            store.rollback(1, store.generation)
            if store.payload != original:
                raise ValueError('rollback mismatch')
            store.upgrade(store.generation)
            reset(store, seed, store.generation, 'RESET-SYNTHETIC-STATE')
            if store.payload['reset_count'] != 1:
                raise ValueError('reset mismatch')
        with restore(parent / 'snapshot.json', parent / 'restored') as store:
            if store.payload != committed:
                raise ValueError('restore mismatch')
    return {'result': 'PASS', 'synthetic_fixture': True, 'restart': 'PASS',
            'backup_restore': 'PASS', 'upgrade_rollback': 'PASS', 'explicit_reset': 'PASS',
            'real_restore_qualified': False}


def handle(args, seed):
    if args == ['rehearse']:
        return rehearsal(seed)
    if not args:
        raise ValueError('state operation')
    operation = args[0]
    contracts = {
        'init': ('--directory',), 'inspect': ('--directory',),
        'backup': ('--directory', '--output'), 'restore': ('--input', '--directory'),
        'upgrade': ('--directory', '--expect-generation'),
        'rollback': ('--directory', '--to-generation', '--expect-generation'),
        'reset': ('--directory', '--expect-generation', '--confirm-reset'),
    }
    if operation not in contracts:
        raise ValueError('state operation')
    selected = options(args[1:], required=contracts[operation])
    if operation == 'init':
        context = StateStore.create(selected['--directory'], seed())
    elif operation == 'restore':
        context = restore(selected['--input'], selected['--directory'])
    else:
        context = StateStore(selected['--directory'])
    with context as store:
        changed = False
        if operation == 'backup':
            store.backup(selected['--output'])
        elif operation == 'upgrade':
            changed = store.upgrade(number(selected['--expect-generation']))
        elif operation == 'rollback':
            store.rollback(number(selected['--to-generation']), number(selected['--expect-generation']))
        elif operation == 'reset':
            reset(store, seed, number(selected['--expect-generation']), selected['--confirm-reset'])
        return {'result': 'PASS', 'operation': operation, 'generation': store.generation,
                'state_schema': store.payload['schema_version'],
                'requires_upgrade': store.payload['schema_version'] != CURRENT_SCHEMA,
                'upgrade_changed': changed}
