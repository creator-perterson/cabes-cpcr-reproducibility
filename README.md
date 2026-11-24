# CABES/CPCR Reproducibility Package

**v0.1.0 preliminary research release preparation. Publication is pending completion of the copyright notice and explicit authorization for the current public remote.**

This repository is a bounded package for the CABES/CPCR KAIS manuscript. It contains selected source modules, frozen derived outcomes, configurations, and provenance records.

The package corresponds to the R3.1 author-review manuscript candidate. The related manuscript is *Completeness-Prioritized Candidate Retention for Multi-Hop RAG with Fixed Evidence Pools*. Paper authors are Xingyun Chen and Shiyong Xiong, with Shiyong Xiong as corresponding author. The software author is Xingyun Chen. Their affiliation is Chongqing University of Posts and Telecommunications.

The package has three reproduction levels.

- Level 1 replays seven R14 metrics and ten contrasts, including 10,000-draw question and cluster bootstrap, LOCO and McNemar calculations. Numeric fields match official frozen statistics under absolute and relative tolerances of 1e-12.
- Level 2 runs the namespaced CABES and CPCR implementation on a small fixed synthetic candidate pool. It verifies module behavior and interface contracts. It does not validate the historical formal cohort.
- Level 3 provides a guarded entry point and configuration template for a complete run. It is documentation and preflight only in this package. It does not load a model or start Search, Reader, Retrieval, Baseline, P1, P2, or new dataset experiments.

The R14 factorial cells A00, A01, A10, and A11 retain their own experiment identities. `src/cpcr/clean_factorial.py` is the R14 Clean A selection rule. `src/cpcr/search.py` preserves the earlier P3 historical CPCR wrapper as a separate implementation. A11 is the Clean A11 cell and is not described as historical CPCR. Historical H and C four-cell records remain separate from the R14 clean factorial.

## Quick start

Validation requires Python 3.10 or newer. Install the bounded tokenizer and statistics dependencies before running the full test suite and R14 replay.

```powershell
# Run from your checkout directory.
python -m pip install -r environment/fixed-pool-requirements.txt -r environment/statistics-requirements.txt
python -m unittest discover -s tests -v
python scripts/recompute_level1.py
python scripts/recompute_full_statistics.py
python scripts/run_level2_smoke.py
python scripts/run_level3.py --check
python scripts/scan_release_boundary.py --fail-on-history
```

The statistical replay and synthetic checks use included sanitized outcomes and fixtures. They do not load model weights, contact external datasets, or start formal experiments. The release-boundary command scans text files and reachable Git blobs for bounded path and credential patterns plus prohibited payload extensions. It is a release gate, not a legal rights determination.

## Repository map

`src/cabes/` contains the selected CABES BlockSearch and base scoring modules. `src/cpcr/` contains the CPCR wrapper, structural coverage proxy, and state-selection keys. `src/evaluation/` contains offline aggregation helpers. `configs/` records bounded configurations. `results/level1/` contains sanitized derived metrics. `results/` contains expected and recomputed summaries. `docs/` describes the algorithm, experiment matrix, evidence mapping, provenance limits, and third-party status.

The repository does not contain model weights, private Reader jobs, private predictions, raw questions, raw evidence text, Gold annotations, validation Parquet files, API keys, or the original engineering workspace.

## Validation status

R14 statistics and synthetic Level 2 are verified within the scopes described in `docs/reproduction_levels.md`. Level 3 remains preflight. Complete H/C, external baseline and matched-budget replay remains open. Historical execution identity limits are recorded in `docs/known_limitations.md`.

## Citation

Use `CITATION.cff` for software and related manuscript citation metadata. No acceptance, publication date or DOI is asserted.

## Rights and access

The user has authorized MIT licensing for independently owned code and public distribution of sanitized derived results and figures. The copyright holder for the MIT notice still requires identification, so the repository `LICENSE` is pending. Data and figures do not automatically inherit the code license. Upstream datasets and model assets are excluded; acquisition details and conditions are recorded in `docs/restricted_assets.json` and `docs/third_party_and_licensing.md`.

## Complete offline R14 replay

```text
python -m pip install -r environment/statistics-requirements.txt
python scripts/recompute_full_statistics.py
python -m pip install -r environment/plotting-requirements.txt
python scripts/plot_level1.py --statistics results/local/full_statistics/statistics.json --output-dir results/local/figures
```

Basic commands write summaries under `results/`. Full statistics default to ignored `results/local/`. The external fixed-pool runner is documented in `docs/level2_fixed_pool.md`.
