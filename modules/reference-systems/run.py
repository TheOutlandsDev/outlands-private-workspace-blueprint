#!/usr/bin/env python3
"""Explicit entry points for the four synthetic reference systems."""
import json
from pathlib import Path
import sys

# -I omits the script directory. Add this reviewed package, never the caller CWD.
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from advisories import review
from identity import DEMO_PASSWORD, Sessions, make_server
from inventory import private_scan, scan
from retrieval import Index
from runtime_io import load_json
from workspace import Workspace


def index_fixture():
    return Index(load_json(HERE / 'fixtures/corpus.example.json'))


def workspace_fixture():
    return Workspace(index_fixture(), scan((HERE / 'fixtures/source-tree').resolve(), synthetic=True),
                     load_json(HERE / 'fixtures/advisories.example.json'))


def demo():
    index = index_fixture()
    sessions = Sessions()
    owner = sessions.login('fictional-owner', DEMO_PASSWORD)
    reader = sessions.login('fictional-reader', DEMO_PASSWORD)
    owner_hits = index.search('recovery', sessions.principal(owner)['role'])['results']
    reader_hits = index.search('recovery', sessions.principal(reader)['role'])['results']
    csrf = sessions.principal(owner)['csrf']
    if not owner_hits or reader_hits or not sessions.logout(owner, csrf) or sessions.principal(owner):
        raise ValueError('integration failure')
    index.delete('fictional-owner-note', 'owner')
    if index.search('recovery', 'owner')['results']:
        raise ValueError('deletion failure')
    return {'result': 'PASS', 'synthetic_fixture': True,
            'identity_to_retrieval': 'PASS', 'revocation_and_deletion': 'PASS',
            'source_inventory': scan((HERE / 'fixtures/source-tree').resolve(), synthetic=True),
            'advisory_review': review(load_json(HERE / 'fixtures/advisories.example.json'),
                                      '2026-01-01T12:00:00Z'),
            'real_host_qualified': False}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if args == ['demo'] or not args:
            result = demo()
        elif args == ['inventory', '--demo']:
            result = scan((HERE / 'fixtures/source-tree').resolve(), synthetic=True)
        elif len(args) == 5 and args[0:2] == ['inventory', '--scan-root'] and args[3] == '--report':
            result = private_scan(args[2], args[4])
        elif len(args) == 4 and args[0:2] == ['retrieval', '--demo']:
            result = index_fixture().search(args[3], args[2])
        elif args == ['advisories', '--demo']:
            result = review(load_json(HERE / 'fixtures/advisories.example.json'), '2026-01-01T12:00:00Z')
        elif len(args) == 4 and args[0:3] == ['advisories', '--demo', '--as-of']:
            result = review(load_json(HERE / 'fixtures/advisories.example.json'), args[3])
        elif args == ['workspace', '--demo']:
            result = workspace_fixture().summary('reader')
        elif args == ['workspace', '--serve'] or (len(args) == 4 and args[0:3] == ['workspace', '--serve', '--port']):
            workspace = workspace_fixture()
            server = make_server(workspace.index, int(args[3]) if len(args) == 4 else 0, workspace=workspace)
            try:
                print(f'Synthetic workspace: http://127.0.0.1:{server.server_port}/', flush=True)
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        elif args == ['identity', '--serve'] or (len(args) == 4 and args[0:3] == ['identity', '--serve', '--port']):
            server = make_server(index_fixture(), int(args[3]) if len(args) == 4 else 0)
            try:
                print(f'Fictional loopback demo: http://127.0.0.1:{server.server_port}/', flush=True)
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        else:
            raise ValueError('command')
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError):
        print(json.dumps({'result': 'REVIEW', 'real_host_qualified': False}, sort_keys=True))
        return 1


if __name__ == '__main__':
    sys.exit(main())
