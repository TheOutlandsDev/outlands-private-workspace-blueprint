#!/usr/bin/env python3
"""Read-only bounded screening of this guide checkout; no services or network."""
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_FILES = 100
MAX_TOTAL_BYTES = 8_000_000
ALLOWED_EMAIL_DOMAINS = {'example.com', 'example.invalid', 'example.org'}
# Visually reviewed captures of the original fictional fixture only.
# Any changed/new image requires a fresh review; arbitrary binaries stay blocked.
REVIEWED_DEMO_IMAGES = {'assets/ai-workbench-demo.jpg': '141f70171f442482b1b7c00a9e1f8e7179c71786ba099b85f9d6ccd656de43d1', 'assets/alertmanager-demo.jpg': 'cd815e308f5a03b0eaec8cf59738b99fa52b209b07f9ad6d941b2787fb5afb75', 'assets/cadvisor-demo.jpg': 'e5daedf21f0221bc74dd7e6e1b2c0bf3c9c99c7af826c25f69f03ec3df854cb1', 'assets/dockhand-demo-desktop.jpg': 'b9f9ac0cb9d163d5ab04b37e5856a362a6778fda78457a2a04646eb7015a17f2', 'assets/dockhand-demo-portrait.jpg': 'cd6ba476237dc009b45997f7e701e6a0cdd48a9b27d8bf4b0dfaec3633a52535', 'assets/fleet-demo.jpg': '286d7bfb79530385716575a7c3a65043ec0386ab34d8a4b5aaea87b4d31dcbb6', 'assets/game-connections-demo.jpg': 'be0c329396657e71ed07cc0b5514055ff1bea650f017167faa86d78633362abc', 'assets/git-manager-demo.jpg': '8ca3fe58539e73a2f3af52aec6f02df80d5b75457deec6c69d15c46a9d3f896f', 'assets/grafana-demo.jpg': 'c17fd6f792810c224daf794f28c4f480883668911f33e42500bdec87422f6e50', 'assets/homepage-demo.jpg': '11aac8641d24b36448560eba6447ad3925618a197abf7db63acfc26c9a60ee15', 'assets/identity-demo.jpg': '77c89434a40723cb1821854d44853137dfc79418b869fb026f4fa70f49fd3a83', 'assets/learning-demo.jpg': 'e6d54c22b12e0b8b1fb84e0693f50e0dcfab0152e39b60543798705444cc6b91', 'assets/local-tools-demo.jpg': 'f42876c1698129aad4d8c7ff21465ec777234b9304f052921e4b97f2a7633907', 'assets/portals-demo.jpg': '630be7f0b473d73e19123700a8add164a712ddd7c5f16ce4552a2ba57c6173ee', 'assets/prometheus-demo.jpg': '4b3149c1f9842af50ce3fc26fb10211ac21db9fcd2e3ad36bc8e03b54cdb9454'}


def main():
    findings = []
    total = 0
    count = 0
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if '.git' in relative.parts or '__pycache__' in relative.parts:
            continue
        if path.is_symlink():
            findings.append({'file': str(relative), 'check': 'symlink'})
            continue
        if not path.is_file():
            continue
        count += 1
        size = path.stat().st_size
        total += size
        if count > MAX_FILES or total > MAX_TOTAL_BYTES or size > 2_000_000:
            findings.append({'check': 'bounded_source_limit'})
            break
        if ((path.name.startswith('.env') and path.name != '.env.example')
                or path.suffix.lower() in ('.key', '.pem', '.db', '.sqlite', '.sqlite3')):
            findings.append({'file': str(relative), 'check': 'private_file_type'})
        if relative.as_posix() in REVIEWED_DEMO_IMAGES:
            data = path.read_bytes()
            if (not data.startswith(b'\xff\xd8\xff') or not data.endswith(b'\xff\xd9')
                    or hashlib.sha256(data).hexdigest() != REVIEWED_DEMO_IMAGES[relative.as_posix()]):
                findings.append({'file': str(relative), 'check': 'reviewed_demo_image_changed'})
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeError:
            findings.append({'file': str(relative), 'check': 'unreviewed_binary'})
            continue
        patterns = {
            'private_home_or_service_path': r'/(?:home|srv)/[A-Za-z0-9_-]+',
            'private_tailnet_fingerprint': r'\btail[a-f0-9]{6}\.ts\.net\b',
            'private_key_header': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            'github_token_shape': r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',
            'cloud_key_shape': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        }
        for check, pattern in patterns.items():
            if re.search(pattern, text):
                findings.append({'file': str(relative), 'check': check})
        for address in re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text):
            try:
                ip = ipaddress.ip_address(address)
            except ValueError:
                continue
            if any(ip in ipaddress.ip_network((base, width)) for base, width in
                   ((0x0A000000, 8), (0xAC100000, 12),
                    (0xC0A80000, 16), (0x64400000, 10))):
                findings.append({'file': str(relative), 'check': 'private_network_address'})
        for email in re.findall(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b', text):
            if email not in ALLOWED_EMAIL_DOMAINS:
                findings.append({'file': str(relative), 'check': 'nonexample_email'})
        if path.suffix.lower() == '.md':
            for target in re.findall(r'\]\(([^)\s]+)(?:\s+[^)]*)?\)', text):
                if target.startswith(('https://', 'http://', '#', 'mailto:')):
                    continue
                destination = (path.parent / target.split('#', 1)[0]).resolve()
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    findings.append({'file': str(relative), 'check': 'local_link'})
    compose = (ROOT / 'examples/homepage/compose.yaml').read_text()
    if '127.0.0.1:3000:3000' not in compose or 'docker.sock' in compose:
        findings.append({'check': 'homepage_loopback_and_no_socket'})
    if '${HOMEPAGE_IMAGE:?' not in compose:
        findings.append({'check': 'explicit_image_selection'})
    print(json.dumps({'result': 'PASS' if not findings else 'REVIEW',
                      'files_checked': count, 'bytes_checked': total,
                      'findings': findings, 'services_started': 0,
                      'network_requests': 0}, sort_keys=True))
    return 0 if not findings else 1


if __name__ == '__main__':
    sys.exit(main())
