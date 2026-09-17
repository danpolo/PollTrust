# Data schemas

These normalized v1 contracts are intentionally small.

## `data/election.json`

Contains the current election identifier/date/source, stale-data threshold, and a map of current `pollster_id` to Hebrew display name, current outlet mapping, and optional lineage disclosure.

## `data/current-polls.json`

Top-level fields: `schema_version`, `last_successful_update`, and `polls[]`.

Each poll requires `pollster`, ISO `date`, HTTP(S) `source`, and `parties`. Party mandates must total exactly 120. `outlet` is optional presentation metadata and never affects historical scoring.

## `data/historical-polls.json`

Committed production calibration input. Important top-level fields:

- `demo_mode: false`;
- `elections[]` with election date, exact 120-seat result vector, and election-specific truth-bias bloc mapping where defensible;
- `polls[]`, each with historical pollster ID, election ID, ISO date, immutable source reference, original source pollster label, optional outlet, and an exact 120-seat party vector;
- `historical_pollsters[]` and `active_pollsters[]`;
- `historical_coverage_notes` documenting asymmetric lineage cutoffs;
- `shared_prior` for the discounted Direct Polls shared Filber/Sharon record;
- `analysis` configuration;
- `provenance` with source revision URLs, SHA-256 hashes, counts, and parser diagnostics.

Production collection never fills a missing seat to force a row to 120.

## `data/historical-validation.json`

Audit artifact produced by `scripts/validate_historical_dataset.py`. It contains:

- counts by election and pollster;
- lineage coverage and observed source aliases;
- exact duplicate and same-day competing-poll reports;
- suspicious imported-value report;
- parser diagnostics for unmatched pollsters/parties, malformed rows, skipped rows and removed duplicates;
- source-snapshot reparse verification;
- dataset/model validation errors.

A committed production calibration is valid only when `valid` is true and both dataset/model error lists are empty.

## `data/historical-model.json`

Generated static artifact. Per active pollster it contains overall/median/final-poll error, consistency, expected error curve by days before election, election-list-aware truth bias, debiased error, bias cost, cluster-balanced relative lean, lean value added, alignment, uncertainty, election support, independent support, shared-prior effective support, and lineage notes.

The current Direct Polls shared record is not represented as an active pollster. Its discounted support is inherited by the two separate current entities, Sharon/Direct Polls and Filber/NEXT DATA.
