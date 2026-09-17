# PollTrust

PollTrust is a static Hebrew/RTL web application for comparing the historical accuracy of active Israeli election pollsters. Historical modeling is pollster-centric; current media outlets are presentation mappings only.

## v1 status

The application, calculation pipeline, tests, ingestion framework, daily update workflow, and GitHub Pages deployment are implemented. The historical calibration dataset is intentionally synthetic/demo data so the statistical pipeline and UI can be exercised without presenting unresearched historical conclusions as fact. Replace the demo generator with sourced historical polls before treating reliability values as production results.

Current network sources are disabled by default until each deterministic source parser has been validated. This is deliberate fail-safe behavior: unavailable or broken sources must never erase the last valid dataset.

## Architecture

```text
index.html + assets/        static Hebrew/RTL frontend
data/                       current election/poll/source configuration
polltrust/                  metrics, model, validation and ingestion package
polltrust/adapters/         deterministic source adapter interface
scripts/                    historical build and daily update entry points
tests/                      metric, leakage, prior and fail-safe tests
.github/workflows/          CI, daily update, historical rebuild, Pages deploy
```

## Core methodology

`SeatTransferDistance = 0.5 * Σ | predicted_i - actual_i |`

The historical weighting unit is an election, not a poll. At X days before an election, the model chooses the latest poll available on or before `election_date - X` and never uses future information. A maximum staleness window prevents very old polls from standing in for a pollster at a later horizon.

The model separately calculates raw error, consistency, truth bias for a configured bloc, leave-one-election-out debiased precision, cluster-balanced relative lean, lean value added, alignment, uncertainty, and support.

Direct Polls / Zuriel Sharon and NEXT DATA / Shlomo Filber are separate current entities. Both inherit a discounted shared prior from their joint historical Direct Polls record; independent completed-election history receives full weight and therefore progressively dominates the prior.

## Local development

Requires Python 3.11+.

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_historical_model.py
python -m pytest
python -m http.server 8000
```

Open `http://localhost:8000`. The frontend fetches JSON files, so do not open `index.html` directly with `file://`.

## Historical data workflow

The default build uses `polltrust/demo_data.py`, which contains clearly synthetic party identifiers and observations. For production, normalize sourced historical polls into the same raw structure and run:

```bash
python scripts/build_historical_model.py --input path/to/historical.json --output data/historical-model.json
```

The frontend consumes only the generated static model; it does not recompute the statistical model in the browser.

## Current-poll ingestion

`data/sources.json` configures adapters. v1 includes a normalized repository fixture adapter and a normalized remote JSON adapter. Publisher-specific adapters can implement `PollSourceAdapter.fetch()`, normalize party identifiers, validate against fixtures, and then be enabled. Incoming rows are validated before mutation, must total exactly 120 seats, and are deduplicated.

## GitHub Actions

- `ci.yml`: builds the model and runs tests on pushes/PRs.
- `update-polls.yml`: runs daily and on manual dispatch; commits only validated changes.
- `rebuild-historical.yml`: manually produces a reproducible historical-model artifact.
- `deploy-pages.yml`: builds, tests, stages, and deploys GitHub Pages from `main`.

The Pages workflow uses GitHub's Actions deployment source and generates the static historical model during the build.

## UI

All user-facing application copy is Hebrew and the document is `dir="rtl"`. Code, filenames, documentation, and identifiers are English.

PollTrust reports descriptive statistical performance. It is not voting advice and does not predict who should win an election.
