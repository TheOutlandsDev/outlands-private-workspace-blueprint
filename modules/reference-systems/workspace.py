"""Synthetic workspace state and escaped HTML views; no private adapters."""
from html import escape

from advisories import review

SCENARIOS = {'fresh', 'stale', 'unavailable'}


class Workspace:
    def __init__(self, index, inventory, advisories):
        if inventory.get('synthetic_fixture') is not True:
            raise ValueError('synthetic inventory required')
        # The fixed advisory input is validated before the workspace is started.
        review(advisories, '2026-01-01T12:00:00Z')
        self.index = index
        self.inventory = inventory
        self.advisories = advisories
        self.scenario = 'fresh'

    def select_scenario(self, scenario, role):
        if role != 'owner' or not isinstance(scenario, str) or scenario not in SCENARIOS:
            raise ValueError('scenario denied')
        self.scenario = scenario

    def inventory_view(self):
        if self.scenario == 'unavailable':
            return {'state': 'UNAVAILABLE', 'synthetic_fixture': True}
        return {'state': 'STALE' if self.scenario == 'stale' else 'FRESH',
                'synthetic_fixture': True, 'data': self.inventory}

    def advisory_view(self, role):
        if role != 'owner':
            raise ValueError('advisory access denied')
        if self.scenario == 'unavailable':
            return {'state': 'UNAVAILABLE', 'synthetic_fixture': True}
        report = review(self.advisories, '2026-01-03T00:00:00Z' if self.scenario == 'stale'
                        else '2026-01-01T12:00:00Z')
        return {'state': report['freshness'], 'synthetic_fixture': True, 'data': report}

    def documents(self, role):
        if role != 'owner':
            raise ValueError('document administration denied')
        return sorted(self.index.documents)

    def summary(self, role):
        if role not in {'owner', 'reader'}:
            raise ValueError('role denied')
        return {'synthetic_fixture': True, 'role': role,
                'inventory': self.inventory_view(),
                'advisories': self.advisory_view(role) if role == 'owner' else {'state': 'DENIED'},
                'retrieval': {'state': 'READY', 'visible_documents':
                              sum(role in audience for audience in self.index.documents.values())},
                'real_host_qualified': False}


def esc(value):
    return escape(str(value), quote=True)


def badge(state):
    return f'<span class="badge" data-state="{esc(state)}">{esc(state)}</span>'


def logout_form(record):
    return ('<form method="post" action="/logout">'
            f'<input type="hidden" name="csrf" value="{esc(record["csrf"])}">'
            '<button class="quiet">Sign out</button></form>')


def page(title, content, record=None):
    account = (f'<span class="role">{esc(record["role"])} session</span>' + logout_form(record)
               if record else '<span class="role">Signed out</span>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(title)} · OUTLANDS</title><link rel="stylesheet" href="/workspace.css">'
            '</head><body><a class="skip" href="#main">Skip to content</a>'
            '<header><a class="brand" href="/">OUTLANDS<span>PRIVATE WORKSPACE BLUEPRINT</span></a>'
            f'<div class="account">{account}</div></header><main id="main">{content}</main>'
            '<footer>INVENTED DATA ONLY <span>Loopback reference · no real host acceptance</span></footer>'
            '</body></html>')


def login_page():
    return page('Sign in', '<section class="intro"><p class="eyebrow">INTEGRATED SYNTHETIC WORKSPACE</p>'
                '<h1>Your systems.<br>One clear boundary.</h1>'
                '<p class="lede">Explore inventory, document retrieval and advisory review with fictional data.</p></section>'
                '<section class="login card"><h2>Enter the local demo</h2><p>Choose a fictional role. '
                'These public accounts protect no real data.</p><form method="post" action="/login">'
                '<label for="username">Demo account</label><select id="username" name="username">'
                '<option value="fictional-owner">fictional-owner</option>'
                '<option value="fictional-reader">fictional-reader</option></select>'
                '<label for="password">Demo password</label>'
                '<input id="password" name="password" type="password" required maxlength="128" autocomplete="off">'
                '<p class="hint">Public fixture password: <code>synthetic-only</code></p>'
                '<button>Sign in</button></form></section>')


def denied_page(record=None, status='DENIED'):
    return page('Access denied', '<section class="intro">' + badge(status) +
                '<h1>Access is restricted.</h1><p class="lede">This session cannot open that resource.</p>'
                '<p><a href="/">Return to the workspace</a></p></section>', record)


def inventory_card(view):
    body = '<p>Fixture source is unavailable. No counts are shown.</p>'
    if 'data' in view:
        counts = view['data']['counts']
        body = '<dl class="stats">' + ''.join(
            f'<div><dt>{esc(kind.title())}</dt><dd>{esc(counts[kind]["lines"])} <small>lines</small></dd>'
            f'<span>{esc(counts[kind]["files"])} file' + ('' if counts[kind]['files'] == 1 else 's') + '</span></div>'
            for kind in ['code', 'configuration', 'prose']) + '</dl>'
        body += '<p class="hint">Partial by policy · saved files only · no authorship claim</p>'
    return '<section class="card"><div class="card-top"><h2>Source inventory</h2>' + badge(view['state']) + '</div>' + body + '</section>'


def advisory_card(view):
    if view['state'] == 'DENIED':
        body = '<p>Advisory details are restricted to the owner role.</p>'
    elif 'data' not in view:
        body = '<p>Fixture source is unavailable. No candidate counts are shown.</p>'
    else:
        report = view['data']
        count = sum(item['status'] == 'REVIEW_CANDIDATE' for item in report['results'])
        body = f'<p class="big-number">{count}<span>review candidate</span></p>'
        body += '<p class="hint">A range match does not confirm exposure.</p><a href="/workspace/advisories">Review fictional candidates →</a>'
    return '<section class="card"><div class="card-top"><h2>Advisory review</h2>' + badge(view['state']) + '</div>' + body + '</section>'


def search_form(query=''):
    return ('<form class="search" method="get" action="/workspace/search">'
            '<label for="q">Search permitted fictional documents</label><div class="search-row">'
            f'<input id="q" name="q" maxlength="256" required value="{esc(query)}" placeholder="Try lamp or recovery">'
            '<button>Search</button></div></form>')


def home_page(workspace, record, notice=''):
    summary = workspace.summary(record['role'])
    message = {'deleted': 'Document removed from this in-memory workspace.',
               'missing': 'That document is already absent.',
               'scenario': 'Synthetic source state changed.'}.get(notice, '')
    content = ('<section class="intro"><p class="eyebrow">INTEGRATED SYNTHETIC WORKSPACE</p>'
               '<div class="title-row"><h1>Workspace overview</h1>' + badge('SYNTHETIC') + '</div>'
               '<p class="lede">Four reference systems. One session. Explicit access at every endpoint.</p></section>')
    if message:
        content += f'<p class="notice" role="status">{esc(message)}</p>'
    content += '<div class="cards">' + inventory_card(summary['inventory'])
    content += ('<section class="card"><div class="card-top"><h2>Document retrieval</h2>' + badge('READY') + '</div>'
                f'<p class="big-number">{summary["retrieval"]["visible_documents"]}<span>permitted documents</span></p>'
                '<p>Session permissions filter results before ranking.</p><p class="hint">Lexical search · untrusted extracts · no generated answer</p></section>')
    content += advisory_card(summary['advisories']) + '</div><section class="card search-card"><h2>Find a source</h2>'
    content += search_form() + '<p class="hint">Try “recovery” as each role to compare access. Unmatched queries show an explicit empty state.</p></section>'
    if record['role'] == 'owner':
        csrf = f'<input type="hidden" name="csrf" value="{esc(record["csrf"])}">'
        content += ('<section class="card admin"><p class="eyebrow">OWNER CONTROLS</p><h2>Rehearse a change</h2>'
                    '<div class="admin-grid"><form method="post" action="/admin/scenario">' + csrf +
                    '<label for="scenario">Synthetic source state</label><select id="scenario" name="scenario">' +
                    ''.join(f'<option value="{s}"' + (' selected' if workspace.scenario == s else '') + f'>{s.title()}</option>'
                            for s in ['fresh', 'stale', 'unavailable']) + '</select><button>Apply fixture state</button></form>')
        documents = workspace.documents('owner')
        if documents:
            content += ('<form method="post" action="/admin/delete">' + csrf +
                        '<label for="source_id">Remove an invented document</label><select id="source_id" name="source_id">' +
                        ''.join(f'<option>{esc(source)}</option>' for source in documents) + '</select>'
                        '<button class="danger">Delete from memory</button></form>')
        else:
            content += '<p>No documents remain in this process.</p>'
        content += '</div><p class="hint">Changes affect this shared demo process. Restart restores the fixtures; deletion is not persistent.</p></section>'
    return page('Workspace', content, record)


def search_page(workspace, record, query):
    report = workspace.index.search(query, record['role'])
    state = 'RESULTS' if report['results'] else 'EMPTY'
    content = '<section class="intro"><a href="/">← Workspace</a><h1>Permitted sources</h1>' + badge(state) + '</section>'
    content += '<section class="card">' + search_form(query) + '</section><section class="results" aria-label="Search results">'
    for hit in report['results']:
        content += (f'<article class="card"><h2>{esc(hit["source_id"])}</h2>'
                    f'<p class="hint">Chunk {hit["chunk"]} · untrusted source text · no instruction execution</p>'
                    f'<blockquote>{esc(hit["text"])}</blockquote></article>')
    if not report['results']:
        content += '<div class="card"><h2>No permitted matches</h2><p>Try another term. Restricted source identifiers are never included.</p></div>'
    return page('Search', content + '</section>', record)


def advisory_page(workspace, record):
    view = workspace.advisory_view(record['role'])
    content = '<section class="intro"><a href="/">← Workspace</a><h1>Fictional advisory review</h1>' + badge(view['state']) + '</section>'
    if 'data' not in view:
        return page('Advisory review', content + '<section class="card"><h2>Source unavailable</h2><p>No candidate data is shown.</p></section>', record)
    content += ('<section class="card table-card"><table><caption>Invented assets and range-review results</caption>'
                '<thead><tr><th scope="col">Asset</th><th scope="col">Range review</th><th scope="col">Exposure</th></tr></thead><tbody>')
    for row in view['data']['results']:
        content += f'<tr><td>{esc(row["asset_id"])}</td><td>{esc(row["status"])}</td><td>Unconfirmed</td></tr>'
    content += '</tbody></table><p class="hint">No active testing or remediation. A no-match result is not a safety finding.</p></section>'
    return page('Advisory review', content, record)
