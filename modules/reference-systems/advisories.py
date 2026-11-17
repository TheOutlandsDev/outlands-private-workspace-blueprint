"""Offline advisory candidates; exact product IDs and bounded release tuples."""
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

from runtime_io import identifier


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})', value):
        raise ValueError('unsupported version')
    return tuple(int(part) for part in value.split('.'))


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', value):
        raise ValueError('UTC timestamp')
    return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def review(data, as_of):
    now = timestamp(as_of)
    if (not isinstance(data, dict)
            or set(data) != {'schema_version', 'synthetic_fixture', 'observed_at', 'assets', 'advisories'}
            or type(data['schema_version']) is not int or data['schema_version'] != 1
            or data['synthetic_fixture'] is not True):
        raise ValueError('advisory contract')
    observed = timestamp(data['observed_at'])
    if observed > now:
        raise ValueError('future observation')
    for key in ['assets', 'advisories']:
        if not isinstance(data[key], list) or not 1 <= len(data[key]) <= 32:
            raise ValueError('record bound')
    assets, advisories = {}, {}
    for asset in data['assets']:
        if (not isinstance(asset, dict) or set(asset) != {'id', 'product', 'version'}
                or not identifier(asset['id']) or not identifier(asset['product'])
                or asset['id'] in assets):
            raise ValueError('asset contract')
        assets[asset['id']] = (asset['product'], version(asset['version']))
    for entry in data['advisories']:
        if (not isinstance(entry, dict)
                or set(entry) != {'id', 'product', 'introduced', 'fixed', 'source'}
                or not identifier(entry['id']) or not identifier(entry['product'])
                or entry['id'] in advisories or not isinstance(entry['source'], str)
                or len(entry['source']) > 256):
            raise ValueError('advisory entry')
        url = urlsplit(entry['source'])
        if (url.scheme != 'https' or url.hostname != 'advisories.example.invalid'
                or url.username or url.password or url.port or url.fragment or url.query
                or not re.fullmatch(r'/[a-z0-9-]+', url.path)):
            raise ValueError('synthetic source URL')
        low, high = version(entry['introduced']), version(entry['fixed'])
        if low >= high:
            raise ValueError('range order')
        advisories[entry['id']] = (entry['product'], low, high, entry['source'])
    results = []
    for asset_id, (product, installed) in sorted(assets.items()):
        matches = [{'advisory_id': aid, 'source': source}
                   for aid, (candidate, low, high, source) in sorted(advisories.items())
                   if product == candidate and low <= installed < high]
        results.append({'asset_id': asset_id, 'status': 'REVIEW_CANDIDATE' if matches else 'NO_RANGE_MATCH',
                        'matches': matches, 'exposure_confirmed': False})
    return {'synthetic_fixture': True, 'observed_at': data['observed_at'], 'as_of': as_of,
            'freshness': 'STALE' if (now - observed).total_seconds() > 86400 else 'FRESH',
            'results': results, 'active_testing_performed': False, 'remediation_authorized': False}
