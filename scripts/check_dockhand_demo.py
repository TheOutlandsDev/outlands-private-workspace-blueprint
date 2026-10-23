#!/usr/bin/env python3
"""Offline checks of the fictional demo and fixed-file policy; no network."""
import importlib.util
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
from types import SimpleNamespace
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/dockhand-theme'

class Fixture(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.forbidden = []
        self.controls = []
        self.in_body = False
        self.rows = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'iframe', 'form', 'object', 'embed'):
            self.forbidden.append(tag)
        if tag in ('input', 'button'):
            self.controls.append('disabled' in attrs)
        for key in ('src', 'href'):
            if key in attrs and not attrs[key].startswith('#'):
                self.resources.append(attrs[key])
        if tag == 'tbody': self.in_body = True
        if tag == 'tr' and self.in_body: self.rows += 1
    def handle_endtag(self, tag):
        if tag == 'tbody': self.in_body = False

def main():
    findings = []
    def check(ok, code):
        if not ok: findings.append(code)
    html = (EXAMPLE / 'demo/index.html').read_text()
    fixture = Fixture();fixture.feed(html)
    check(not fixture.forbidden and fixture.rows == 6 and all(fixture.controls), 'fixture_inert_and_six_rows')
    check('ILLUSTRATIVE MOCKUP' in html and 'Fictional data' in html, 'visible_fictional_label')
    for target in fixture.resources:
        destination = (EXAMPLE / 'demo' / target).resolve()
        check(':' not in target and destination.is_relative_to(EXAMPLE) and destination.is_file(), 'local_fixture_resource')
    for css in EXAMPLE.rglob('*.css'):
        text = css.read_text()
        check('@import' not in text and 'http:' not in text and 'https:' not in text, 'no_remote_css')
        for target in re.findall(r'url\([\'\"]?([^\)\'\"]+)', text):
            destination = (css.parent / target).resolve()
            check(destination.is_relative_to(EXAMPLE) and destination.is_file(), 'relative_artwork')
    for svg in EXAMPLE.rglob('*.svg'):
        tree = ET.fromstring(svg.read_bytes())
        for node in tree.iter():
            tag = node.tag.split('}')[-1]
            check(tag not in ('script', 'foreignObject', 'image', 'animate'), 'inert_original_svg')
            check(not any(key.lower().startswith('on') or key.endswith('href') for key in node.attrib), 'no_svg_event_or_external_reference')
    for doc in ROOT.rglob('*.md'):
        for target in re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', doc.read_text()):
            path = (doc.parent / target).resolve()
            check(':' not in target and path.is_relative_to(ROOT) and path.is_file(), 'local_markdown_html_image')
    config = (EXAMPLE / 'nginx-theme-assets.example.conf').read_text()
    check('internal;\n    return 403;' in config, 'placeholder_denies_everyone')
    check(config.count('auth_request /_outlands_owner_check;') == 3, 'three_owner_protected_assets')
    check('return 200' not in config and 'proxy_pass' not in config, 'no_asset_auth_bypass_or_app_route')
    spec = importlib.util.spec_from_file_location('fictional_demo', EXAMPLE / 'serve_demo.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    cases = 0
    for route in list(module.FILES) + ['/not-a-file','/../README.md','/demo/?x=1','/api/containers']:
        for head in (False, True):
            obj = object.__new__(module.Handler)
            obj.server = SimpleNamespace(server_address=('127.0.0.1',8765))
            obj.headers = {'Host':'127.0.0.1:8765'};obj.path=route;obj.wfile=BytesIO()
            result = {};obj.send_response=lambda code:result.update(code=code)
            obj.send_error=lambda code:result.update(code=code)
            obj.send_header=lambda *a:None;obj.end_headers=lambda:None
            obj.respond(body=not head);cases += 1
            check(result['code'] == (200 if route in module.FILES else 404), 'fixed_file_handler_path')
            if head: check(not obj.wfile.getvalue(), 'head_has_no_body')
    obj.headers = {'Host':'unrelated.invalid'};obj.path='/demo/'
    obj.respond();check(result['code']==400,'fixed_file_handler_host');cases += 1
    print(json.dumps({'result':'PASS' if not findings else 'REVIEW','findings':findings,
        'synthetic_handler_cases':cases,'network_requests':0,'native_app_changes':0},sort_keys=True))
    return bool(findings)

if __name__ == '__main__':
    raise SystemExit(main())
