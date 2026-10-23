#!/usr/bin/env python3
"""Read-only bounded screening of this guide checkout; no services or network."""
import ipaddress
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_FILES = 100
MAX_TOTAL_BYTES = 8_000_000
ALLOWED_EMAIL_DOMAINS = {'example.com', 'example.invalid', 'example.org'}


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
