#!/usr/bin/env python3
"""Offline checks of original fictional app pages; no network or native app use."""
import importlib.util
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
from types import SimpleNamespace
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples/app-tour'

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.forbidden = []
        self.headings = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script','form','input','button','iframe','object','embed','base'):
            self.forbidden.append(tag)
        if tag == 'h1': self.headings += 1
        if any(k.lower().startswith('on') for k in attrs): self.forbidden.append('event')
        for key in ('href','src'):
            if key in attrs and not attrs[key].startswith('#'):
                self.resources.append(attrs[key])

def main():
    failures = []
    def check(ok, label):
        if not ok: failures.append(label)
    pages = sorted(EXAMPLE.glob('*.html'))
    check(len(pages)==13,'thirteen_pages')
    for path in pages:
        text = path.read_text()
        p = Page();p.feed(text)
        check(p.headings==1 and not p.forbidden,'inert_semantic_page')
        check('ILLUSTRATIVE MOCKUP' in text and 'FICTIONAL DATA' in text,'visible_mockup_label')
        for target in p.resources:
            resolved = (EXAMPLE / target).resolve()
            check(':' not in target and resolved.is_relative_to(EXAMPLE) and resolved.is_file(),'local_resource')
        check((ROOT / 'assets' / (path.stem+'-demo.jpg')).is_file(),'guide_screenshot_present')
    css = (EXAMPLE / 'tour.css').read_text()
    check('@import' not in css and not re.search(r'https?:',css),'no_remote_styles')
    for target in re.findall(r'url\([\'\"]?([^\)\'\"]+)',css):
        check((EXAMPLE / target).is_file(),'local_css_asset')
    tree = ET.fromstring((EXAMPLE / 'wall.svg').read_bytes())
    for node in tree.iter():
        check(node.tag.split('}')[-1] not in ('script','foreignObject','image','animate'),'inert_svg')
        check(not any(k.lower().startswith('on') or k.endswith('href') for k in node.attrib),'no_svg_external_reference')
    spec = importlib.util.spec_from_file_location('app_tour',EXAMPLE/'serve_demo.py')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    expected = {'/','/tour.css','/wall.svg'} | {'/'+p.name for p in pages}
    check(set(module.FILES)==expected,'exact_route_registry')
    cases = 0
    for host in ('127.0.0.1:8766','localhost:8766','unrelated.invalid'):
        for route in list(module.FILES)+['/../README.md','/homepage.html?x=1','/%68omepage.html','/api/containers','/serve_demo.py']:
            for head in (False,True):
                obj = object.__new__(module.Handler)
                obj.server=SimpleNamespace(server_address=('127.0.0.1',8766))
                obj.headers={'Host':host};obj.path=route;obj.wfile=BytesIO()
                observed={};headers={}
                obj.send_response=lambda code:observed.update(code=code)
                obj.send_error=lambda code:observed.update(code=code)
                obj.send_header=lambda k,v:headers.update({k:v})
                obj.end_headers=lambda:None
                obj.respond(body=not head);cases += 1
                expected_code=400 if host=='unrelated.invalid' else 200 if route in module.FILES else 404
                check(observed['code']==expected_code,'handler_denial_or_fixed_file')
                if head:check(not obj.wfile.getvalue(),'head_empty_body')
                if expected_code==200:
                    check(headers.get('Cache-Control')=='no-store','no_store')
                    check("default-src 'none'" in headers.get('Content-Security-Policy',''),'restrictive_csp')
    check(not hasattr(module.Handler,'do_POST') and not hasattr(module.Handler,'do_PUT'),'no_write_handlers')
    check("ThreadingHTTPServer(('127.0.0.1'," in (EXAMPLE/'serve_demo.py').read_text(),'loopback_bind')
    print(json.dumps({'result':'PASS' if not failures else 'REVIEW','pages':len(pages),
        'synthetic_handler_cases':cases,'findings':failures,'network_requests':0,'native_app_changes':0},sort_keys=True))
    return bool(failures)

if __name__ == '__main__':
    raise SystemExit(main())
