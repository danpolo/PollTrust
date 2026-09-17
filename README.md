# PollTrust

PollTrust is a static Hebrew/RTL web application for comparing the historical accuracy of active Israeli election pollsters. Historical modeling is pollster-centric; current media outlets are presentation mappings only.

## v1 status

The historical calibration is now sourced production data rather than demo data. The repository contains:

- `data/historical-polls.json`: 187 validated historical polls from the 2009–2022 election cycles.
- `data/historical-model.json`: the deterministic precomputed reliability model consumed by the frontend.
- `data/historical-validation.json`: the audit report from the production historical build.

The collector uses immutable Wikipedia revision URLs for reproducible bulk election tables, records the SHA-256 of each fetched source snapshot, and keeps source provenance on every poll. TheMadad remains a useful cross-check, but it is not a required automated dependency because it returns HTTP 403 to GitHub Actions.

Current-poll network sources remain disabled by default until each deterministic source adapter is validated. This is deliberate fail-safe behavior: an unavailable or broken current source must never erase the last valid dataset.

## Historical coverage

Coverage is intentionally asymmetric: each current pollster lineage goes back only as far as both the source data and the continuity evidence support.

| Historical lineage | Imported election history | Notes |
| --- | --- | --- |
| Midgam / Mano Geva | 2009–2022 | Direct Midgam/Mano Geva continuity is documented by 2009. |
| Maagar Mohot / Yitzhak Katz | 2009–2022 | Continuity predates 2009. A reviewed 2006 archive row totals 119 seats and is reported but not repaired or imported. |
| Panels Politics → Lazar Research / Menachem Lazar | 2013–2022 where present | Generic 2009 `Panels` rows are excluded because personal continuity to Lazar was not sufficiently established. |
| Kantar / Dudi Hasid | 2019–2022 | Only explicitly Kantar-branded rows are inherited. Historical TNS/Teleseker rows are not automatically merged. |
| Direct Polls shared Filber/Sharon history | 2019–2022 | Stored as a shared historical lineage, not attributed to either current entity alone. |
| HaMadad | none yet | Treated as a new current entity. |
| Tatika | none yet | Treated as a new current entity. |

The committed dataset currently contains 187 polls: 8 (2009), 7 (2013), 23 (2015), 32 (April 2019), 12 (September 2019), 31 (2020), 35 (2021), and 39 (2022).

## Architecture

```text
index.html + assets/        static Hebrew/RTL frontend
data/                       production historical/current JSON
polltrust/                  metrics, model, validation and ingestion package
polltrust/adapters/         deterministic current-source adapter interface
scripts/                    collection, validation, modeling and update entry points
tests/                      metric, leakage, lineage, prior and fail-safe tests
.github/workflows/          CI, daily update, historical rebuild, Pages deploy
```

## Core methodology

`SeatTransferDistance = 0.5 * Σ | predicted_i - actual_i |`

The historical weighting unit is an election, not a poll. At X days before an election, the model selects the latest poll date available on or before `election_date - X` and never uses election-day/future information. If the same pollster has multiple distinct polls on the same latest date, they are averaged rather than selected arbitrarily. A maximum staleness window prevents very old polls from representing a pollster at a later horizon.

The model separately calculates raw error, consistency, election-list-aware truth bias, leave-one-election-out debiased precision, cluster-balanced relative lean, lean value added, alignment, uncertainty, and support. Cross-election debiasing only corrects party identifiers that are actually comparable across the relevant elections; changing Israeli party alliances are not silently treated as the same list.

Direct Polls / Zuriel Sharon and NEXT DATA / Shlomo Filber are separate current entities. Their five completed shared Direct Polls election cycles contribute a 0.5-discounted prior, i.e. 2.5 effective historical elections to each current entity. Independent completed-election history receives full weight and therefore progressively dominates the shared prior.

## Historical validation

The production audit is deterministic and checks:

- counts per election and pollster;
- valid dates and strict pre-election cutoffs;
- exactly 120 mandates in every imported poll;
- exact duplicates;
- competing same-pollster/same-day projections;
- unmatched pollster aliases;
- malformed rows and all skipped target-lineage rows;
- lineage coverage and source aliases;
- source-snapshot reparse equivalence;
- production model active-pollster coverage and shared-prior support.

Rows are never silently repaired to reach 120 seats. Known source anomalies remain in the validation diagnostics and are excluded.

Two legitimate same-day competing projections currently exist: Midgam on 2019-04-04 and Panels/Lazar on 2022-09-29. Both are retained, disclosed by the audit, and averaged deterministically when that date is selected by the model.

## Local development

Requires Python 3.11+.

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_historical_model.py
python scripts/validate_historical_dataset.py --model data/historical-model.json
python -m pytest
python -m http.server 8000
```

Open `http://localhost:8000`. The frontend fetches JSON files, so do not open `index.html` directly with `file://`.

Synthetic data remains available only as an explicit test/development fixture:

```bash
python scripts/build_historical_model.py --demo --output /tmp/demo-model.json
```

Production builds never fall back to it implicitly.

## Rebuilding the historical calibration

The configured archives are pinned to immutable Wikipedia revision IDs, so a rebuild uses the same source revisions:

```bash
python scripts/build_historical_dataset.py --refresh
python scripts/build_historical_model.py
python scripts/validate_historical_dataset.py --model data/historical-model.json
python -m pytest
```

The collector caches source HTML under `.cache/historical/`. The generated dataset records each source URL and source SHA-256. By default collection fails closed on a configured-source failure; `--allow-partial` is only for debugging and must not be used to produce committed production data.

## Current-poll ingestion

`data/sources.json` configures adapters. v1 includes normalized repository-fixture and remote-JSON adapters. Publisher-specific adapters can implement `PollSourceAdapter.fetch()`, normalize party identifiers, validate expected shape and 120-seat totals, and then be enabled. Incoming rows are validated before mutation and deduplicated.

## GitHub Actions

- `ci.yml`: rebuilds the model from the committed production dataset, byte-compares it with the committed model, validates the data/model, and runs the full test suite.
- `update-polls.yml`: runs daily and on manual dispatch; commits only validated current-poll changes.
- `rebuild-historical.yml`: manually recollects the pinned historical sources, rebuilds, validates, tests, and uploads the calibration artifact.
- `build-historical-dataset.yml`: manual historical collection/audit workflow.
- `deploy-pages.yml`: validates the production historical files and tests before staging and deploying GitHub Pages from `main`.

## UI

All user-facing application copy is Hebrew and the document is `dir="rtl"`. Code, filenames, documentation, and internal identifiers remain English.

PollTrust reports descriptive historical polling performance. It is not voting advice and does not predict an election outcome.
