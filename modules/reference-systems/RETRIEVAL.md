# Admitted, access-filtered synthetic retrieval

This working lexical engine parses a small invented corpus, checks admission,
chunks text, ranks permitted chunks and returns source references. It requires
no model, embedding service, vector database or network connection.

```sh
python3 -I -B modules/reference-systems/run.py retrieval --demo owner recovery
python3 -I -B modules/reference-systems/run.py retrieval --demo reader recovery
python3 -I -B modules/reference-systems/run.py retrieval --demo reader lamp
```

The owner query returns the fictional owner note; the reader recovery query
returns an empty result. The role argument is a simulation of trusted caller
context, not authentication. Use the [identity gate](IDENTITY.md) to exercise
actual session-to-role-to-retrieval integration. The HTTP caller cannot supply
its own role. A private or multi-user deployment needs an independently reviewed
identity and resource-authorization design.

## Admission and indexing

The checked-in [corpus](fixtures/corpus.example.json) declares
`synthetic_fixture=true`. Each document needs a unique simple ID, explicit
`admitted=true`, `rights=synthetic-original`, a nonempty allowed audience and
bounded text. Unknown metadata, unsupported roles, missing admission and rights,
and duplicate IDs reject the entire corpus. Those declarations bind a fixture
contract; they cannot prove permission or that text is fictional.

At most 16 documents of 4096 characters are accepted. Each is split into
240-character chunks, with source ID and zero-based chunk number. Tokenization
uses lowercase ASCII letters/digits. Ranking sums occurrences of distinct query
terms, then uses source ID and chunk number for stable ties. Queries are bounded
to 256 characters and results to five chunks. Authorization filters chunks
before scoring and limiting. An unknown role is refused.

Results contain a source ID, chunk, score and extract, marked
`untrusted_source_text=true`; `answer_generated` stays false. An invented
instruction-like document tests that retrieved content remains plain data.
The engine executes no document, follows no link and issues no tool call.
It cannot prevent a downstream application from mishandling retrieved text.

## Deletion and tests

`Index.delete(source_id, 'owner')` removes the document and every derived chunk
from that in-memory index; a reader deletion is refused. Missing IDs return
false. Caller mutation of the original corpus cannot expand indexed permissions.

```sh
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_retrieval.py'
python3 -I -B modules/reference-systems/run.py demo
```

The combined demo also checks session-derived role filtering, logout revocation
and deletion. Tests cover refused admission, bounds, deterministic chunks,
untrusted extracts and denied document identifiers remaining absent from output.

## Setup boundary, maintenance and rollback

The launcher reads only the fixed public corpus. It has no real-document import,
private connector, embedding operation or model-admission path. A future private
adapter must independently handle rights, tenancy, source lifetimes, parser
safety, deletion propagation and evidence before reading a real collection.
This is working retrieval code, not a qualified generative RAG application.

The index lives in memory. Stopping the process clears it; a new process reloads
the unchanged fixture, including documents deleted in the previous process.
Persistent deletion and external replicas are not implemented. Revert an isolated
fixture/source change and rerun tests to roll back a demo; never use this action
as a claim that real documents were deleted from another system.
