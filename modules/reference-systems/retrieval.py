"""In-memory lexical retrieval with admission, role filtering, and deletion."""
from collections import Counter
import re

from runtime_io import identifier

ROLES = {'owner', 'reader'}


def tokens(text):
    return re.findall(r'[a-z0-9]+', text.lower())


class Index:
    def __init__(self, corpus):
        if (not isinstance(corpus, dict)
                or set(corpus) != {'schema_version', 'synthetic_fixture', 'documents'}
                or type(corpus['schema_version']) is not int or corpus['schema_version'] != 1
                or corpus['synthetic_fixture'] is not True
                or not isinstance(corpus['documents'], list)
                or not 1 <= len(corpus['documents']) <= 16):
            raise ValueError('corpus contract')
        self.documents = {}
        self.chunks = []
        for doc in corpus['documents']:
            if (not isinstance(doc, dict)
                    or set(doc) != {'id', 'admitted', 'rights', 'audience', 'text'}
                    or not identifier(doc['id']) or doc['id'] in self.documents
                    or doc['admitted'] is not True or doc['rights'] != 'synthetic-original'
                    or not isinstance(doc['audience'], list) or not doc['audience']
                    or any(not isinstance(r, str) or r not in ROLES for r in doc['audience'])
                    or len(set(doc['audience'])) != len(doc['audience'])
                    or not isinstance(doc['text'], str) or not 1 <= len(doc['text']) <= 4096
                    or any(ord(c) < 32 and c not in '\n\t' for c in doc['text'])):
                raise ValueError('document admission')
            # Copy mutable caller data; subsequent caller mutations cannot grant access.
            self.documents[doc['id']] = frozenset(doc['audience'])
            for offset in range(0, len(doc['text']), 240):
                text = doc['text'][offset:offset + 240]
                self.chunks.append((doc['id'], offset // 240, text, Counter(tokens(text))))

    def search(self, query, role, limit=3):
        if (not isinstance(role, str) or role not in ROLES
                or not isinstance(query, str) or not 1 <= len(query) <= 256
                or type(limit) is not int or not 1 <= limit <= 5):
            raise ValueError('search contract')
        wanted = set(tokens(query))
        ranked = []
        for source, chunk, text, terms in self.chunks:
            if role not in self.documents[source]:
                continue
            score = sum(terms[word] for word in wanted)
            if score:
                ranked.append({'source_id': source, 'chunk': chunk, 'score': score,
                               'text': text, 'untrusted_source_text': True})
        ranked.sort(key=lambda r: (-r['score'], r['source_id'], r['chunk']))
        return {'synthetic_fixture': True, 'results': ranked[:limit],
                'answer_generated': False}

    def delete(self, source, role):
        if role != 'owner' or not identifier(source):
            raise ValueError('deletion denied')
        existed = source in self.documents
        self.documents.pop(source, None)
        self.chunks = [c for c in self.chunks if c[0] != source]
        return existed
