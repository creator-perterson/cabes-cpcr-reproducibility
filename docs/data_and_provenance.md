# Data sources and provenance

The recorded R2 baseline is the R3.1 author-review finalization archive with SHA-256 `e78fa2d66ad3b8c94b8c49985ca28b59f4dfdca5041d291aa62ce80c1afd71a2`. The source archive matching the author-specified abstract has SHA-256 `cc87e590f3cc89bddabbfdf81d3866964974e2f2bac04ba0620e24d166518400`. Its per-member hashes and the earlier inventory are recorded in `manuscript_source_manifest.json`. The revisions differ in several text sections, while the archived tables and figures remain byte-identical. Reproduction remains limited to the results identified in the package.

The R3.1 independent audit recorded 3,221 Gold binding checks, 7,825 Reader identity checks, 37,560 C archive rows, 2,620 normalized query entities in the eligible cohort, and 107 bounded tests. These counts are contextual audit records, not rerun results from this package.

The Level 1 file is derived from `R14_REVIEW_PER_QUESTION_METRICS.json`. Its question and cluster hashes were replaced by local integer indices. Raw questions, context text, evidence text, prompts, predictions, answers, Gold annotations, and model artifacts were removed. The transformation preserves method identity and numeric metric fields needed for descriptive recomputation.

The public-facing `source_mapping.json` records source artifact names, hashes, versions, destinations and transformations. The full local path mapping is retained in the separate review archive. The original workspaces remain outside this repository.
