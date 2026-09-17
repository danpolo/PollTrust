# Data schemas

These normalized v1 contracts are intentionally small.

## `data/election.json`

Contains the current election identifier/date/source, stale-data threshold, and a map of current `pollster_id` to Hebrew display name, current outlet mapping, and optional lineage disclosure.

## `data/current-polls.json`

Top-level fields: `schema_version`, `last_successful_update`, and `polls[]`.

Each poll requires `pollster`, ISO `date`, HTTP(S) `source`, and `parties`. Party mandates must total exactly 120. `outlet` is optional presentation metadata and never affects historical scoring.

## Historical raw input

The historical build contract contains `active_pollsters[]`, `historical_pollsters[]`, `elections[]`, `polls[]`, `analysis`, and `shared_prior`. Every production historical poll should retain its source reference. The bundled generator is demo-only.

## `data/historical-model.json`

Generated static artifact. Per active pollster it contains overall/median/final-poll error, consistency, expected error curve by days before election, truth bias, debiased error, bias cost, cluster-balanced relative lean, lean value added, alignment, uncertainty, election support, independent support, shared-prior effective support, and lineage notes.
