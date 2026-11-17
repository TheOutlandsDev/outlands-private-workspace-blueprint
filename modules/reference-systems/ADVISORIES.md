# Offline synthetic advisory review

This working matcher joins invented product/version records to invented
advisory ranges. It does no network fetch, host discovery, target testing,
package update or remediation. All source URLs use a reserved fictional domain.

```sh
python3 -I -B modules/reference-systems/run.py advisories --demo
python3 -I -B modules/reference-systems/run.py advisories --demo \
  --as-of 2026-01-03T00:00:00Z
```

The fixed [fixture](fixtures/advisories.example.json) has three invented assets.
One lamp version is inside the range, one is exactly the fixed version, and a
different product has a similar version. Only the first is a
`REVIEW_CANDIDATE`. The second command marks the observation `STALE`.

## Matching contract

Inputs are bounded to 32 assets and 32 advisories, with unique simple IDs,
exact product IDs, an observed UTC time and a synthetic declaration. Only numeric
`major.minor.patch` release tuples are supported. Leading zeroes, prereleases,
build metadata, distribution revisions and other version schemes are refused;
this is deliberately a subset of [Semantic Versioning](https://semver.org/).
Numeric comparison avoids lexical errors such as ordering `1.10.0` below `1.2.0`.

The introduced bound is inclusive and fixed bound exclusive. Invalid or reversed
ranges reject the input. A nonmatching record is `NO_RANGE_MATCH`, never “safe.”
Every result keeps `exposure_confirmed=false`, and the report keeps
`active_testing_performed=false` and `remediation_authorized=false`. A candidate
is a review prompt; product naming, backports, build options, configuration and
reachability need separate evidence.

The report retains the fixture source URL, observation time and explicit as-of
time. Observations older than 24 hours are stale; future observations are refused.
Freshness is a fixture policy, not a guarantee that an advisory source is complete.
The primary source URLs in this demo are invented and are never contacted.

```sh
python3 -I -B -m unittest discover -s modules/reference-systems -p 'test_advisories.py'
```

Tests verify inclusive/exclusive boundaries, exact product matching, version
syntax refusal, duplicate and range rejection, freshness and retained limits.

## Private integration, maintenance and rollback

The launcher accepts only the adjacent synthetic fixture; it has no live feed or
asset importer. Before implementing an adapter privately, establish source
provenance, product normalization, supported version semantics, completeness,
refresh failures and rights. Keep installed-product inventories and candidate
findings private. A public advisory match never grants testing authorization.

To update the isolated demo, change invented inputs on a reviewed branch and
rerun its tests. Preserve the prior source revision. Rollback restores that
fixture/source revision; no actual asset is changed and no remediation is
performed. Schedule, alert delivery, live-source parsing and real exposure
validation remain separate acceptance work.
