# Experiment matrix

| Identity | Meaning | Included in R2.1 candidate | Reproduction status |
| --- | --- | --- | --- |
| Historical H | Historical four-cell records and saved contrasts | Compact saved contrast summary only | Archived result source, offline arithmetic not fully rerun here |
| Historical C | R10 approved evaluator records | Counts and source mapping only | Historical archive, invocation evidence remains bounded |
| R14 A00 | Clean factorial baseline cell | Sanitized per-question metrics | Level 1 validated |
| R14 A01 | Clean factorial cell | Sanitized per-question metrics | Level 1 validated |
| R14 A10 | Clean factorial cell | Sanitized per-question metrics | Level 1 validated |
| R14 A11 | Clean factorial cell with coverage-prioritized beam and final selection | `src/cpcr/clean_factorial.py` plus CABES search source mapping | Level 1 validated, selection keys unit-tested |
| R14 SetR | Adapted external baseline arm | Sanitized per-question metrics | Descriptive rows included, formal rerun not performed |
| Reader runtime | Qwen-based historical Reader route | Receipt summaries only | Historical loader identity partially verified |
| Baselines | RECOMP, MMR, SetR and external comparisons | Compact references and summaries | Formal rerun not performed |
| P1/P2/new data | Future or separate studies | Excluded | Not authorized in this release-preparation task |

The R14 cells are kept separate from H and C. A11 is never relabeled as historical CPCR.
