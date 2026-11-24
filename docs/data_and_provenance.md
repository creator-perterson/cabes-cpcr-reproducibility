# Data sources and provenance

The recorded manuscript baseline is the R3.1 author-review finalization package dated 2026-11-24. The recorded LaTeX source archive SHA-256 is `e78fa2d66ad3b8c94b8c49985ca28b59f4dfdca5041d291aa62ce80c1afd71a2`. At the R2.2 check, the archive at the recorded location had SHA-256 `c8b3c720d4f3064dd6b8e73bc7800ed1b92e603fce01d3e6064a442d6a2efb8e`; eight recorded member hashes differed. The `main.tex` and `metadata.tex` member hashes matched the recorded inventory, including the manuscript title. The archive discrepancy remains unresolved.

The R3.1 independent audit recorded 3,221 Gold binding checks, 7,825 Reader identity checks, 37,560 C archive rows, 2,620 normalized query entities in the eligible cohort, and 107 bounded tests. These counts are contextual audit records, not rerun results from this package.

The Level 1 file is derived from `R14_REVIEW_PER_QUESTION_METRICS.json`. Its question and cluster hashes were replaced by local integer indices. Raw questions, context text, evidence text, prompts, predictions, answers, Gold annotations, and model artifacts were removed. The transformation preserves method identity and numeric metric fields needed for descriptive recomputation.

The public-facing `source_mapping.json` records source artifact names, hashes, versions, destinations and transformations. The full local path mapping is retained in the separate review archive. The original workspaces remain outside this repository.
