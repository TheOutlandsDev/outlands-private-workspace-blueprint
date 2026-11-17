#!/usr/bin/env python3
"""Finite HTTPS rehearsal, with ephemeral trust confined to its own clients."""
import asyncio
from contextlib import asynccontextmanager
import datetime
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import httpx2 as httpx
import uvicorn

from native_auth import Adapter, Config
from fake_issuer import FakeIssuer
from run import seed_state, workspace_persistent
from state_store import StateStore


def certificates(directory):
    now = datetime.datetime.now(datetime.timezone.utc)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Invented loopback fixture')])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(hours=1))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1')),
                                                       x509.DNSName('localhost')]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path, key_path = directory / 'fixture-cert.pem', directory / 'fixture-key.pem'
    for path, data in [(cert_path, cert.public_bytes(serialization.Encoding.PEM)),
                       (key_path, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                    serialization.NoEncryption()))]:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
    context = ssl.create_default_context(cafile=str(cert_path))
    return cert_path, key_path, context


def loopback_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    sock.listen(32)
    sock.setblocking(False)
    return sock


@asynccontextmanager
async def tls_fixture():
    with tempfile.TemporaryDirectory(prefix='invented-oidc-') as temporary:
        root = Path(temporary)
        cert, key, context = certificates(root)
        sockets = [loopback_socket(), loopback_socket()]
        servers, tasks = [], []
        workspace = None
        try:
            config = Config(f'https://127.0.0.1:{sockets[0].getsockname()[1]}',
                            f'https://localhost:{sockets[1].getsockname()[1]}')
            with StateStore.create(root / 'state', seed_state()):
                pass
            workspace = workspace_persistent(root / 'state')
            issuer = FakeIssuer(config)
            adapter = Adapter(config, workspace, verify=context)
            for app, sock in zip([adapter.app(), issuer.app()], sockets):
                server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', workers=1,
                    ssl_certfile=str(cert), ssl_keyfile=str(key), proxy_headers=False,
                    server_header=False, access_log=False, log_config=None, log_level='critical',
                    lifespan='off', ws='none', timeout_keep_alive=2, timeout_graceful_shutdown=2,
                    limit_concurrency=32, h11_max_incomplete_event_size=8192))
                servers.append(server)
                tasks.append(asyncio.create_task(server.serve(sockets=[sock])))
            for _ in range(200):
                if all(s.started for s in servers):
                    break
                if any(t.done() for t in tasks):
                    raise RuntimeError('fixture startup failed')
                await asyncio.sleep(0.01)
            else:
                raise RuntimeError('fixture startup timeout')
            yield config, issuer, adapter, context, root
        finally:
            for server in servers:
                server.should_exit = True
            if tasks:
                await asyncio.wait_for(asyncio.gather(*tasks), 5)
            for sock in sockets:
                sock.close()
            if workspace:
                workspace.close()


async def login(browser, config):
    first = await browser.get(config.origin + '/auth/login')
    assert first.status_code == 303
    issued = await browser.get(first.headers['location'])
    assert issued.status_code == 303
    result = await browser.get(issued.headers['location'])
    assert result.status_code == 303
    return result


async def rehearsal():
    async with tls_fixture() as (config, issuer, adapter, context, root):
        async with httpx.AsyncClient(verify=context, trust_env=False, follow_redirects=False, timeout=3) as browser:
            # Default trust must reject the temporary certificate.
            async with httpx.AsyncClient(trust_env=False, timeout=3) as untrusted:
                try:
                    await untrusted.get(config.origin)
                except httpx.ConnectError:
                    pass
                else:
                    raise AssertionError('untrusted TLS accepted')
            await login(browser, config)
            session = (await browser.get(config.origin + '/session')).json()
            assert session['role'] == 'owner'
            csrf = session['logout_csrf']
            changed = await browser.post(config.origin + '/admin/scenario',
                headers={'origin': config.origin}, data={'csrf': csrf, 'scenario': 'stale'})
            assert changed.status_code == 303
            assert adapter.workspace.store.generation == 2
            await browser.post(config.origin + '/logout', headers={'origin': config.origin}, data={'csrf': csrf})
            assert (await browser.get(config.origin + '/session')).status_code == 401
            issuer.subject = 'invented-reader'
            await login(browser, config)
            assert (await browser.get(config.origin + '/api/advisories')).status_code == 403
            assert not (await browser.get(config.origin + '/api/search?q=recovery')).json()['results']
            assert (await browser.get(config.origin + '/api/summary')).json()['inventory']['state'] == 'STALE'
            assert all(p.stat().st_mode & 0o777 == 0o600 for p in (root / 'state').iterdir())
    return {'result': 'PASS', 'synthetic_fixture': True, 'verified_loopback_tls': True,
            'native_auth_rehearsal': 'PASS', 'real_provider_qualified': False,
            'real_host_qualified': False, 'trust_store_modified': False}


def main():
    if sys.argv[1:] != ['rehearse']:
        print(json.dumps({'result': 'REVIEW', 'real_host_qualified': False}))
        return 1
    try:
        result = asyncio.run(rehearsal())
    except Exception:
        print(json.dumps({'result': 'REVIEW', 'real_host_qualified': False}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
