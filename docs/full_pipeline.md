# Full experiment pipeline

The recorded workflow contains a frozen dataset and candidate-pool preparation, CABES or R14 fixed-pool selection, adapted baseline selection, context serialization, Reader generation, post-freeze Gold scoring, and paired statistical analysis. H, C and Clean A have distinct execution identities. R14 A11 must be identified as Clean A11.

The included `scripts/run_fixed_pool.py` covers the R14 selection stage when an authorized input JSONL, tokenizer JSON and verified tokenizer SHA-256 are supplied. It uses the 256-token serializer. The CLI has been checked with a generated synthetic tokenizer and synthetic pool. It has not been checked on the historical tokenizer or formal cohort in this release candidate.

The repository does not include operational retrieval, SetR-IRI, RECOMP, MMR or Reader execution workflows. It does not contain the raw dataset, model or tokenizer. `scripts/run_level3.py --check` only displays configured external path checks, and a passing command exit does not mean the missing assets or pipeline are ready. An end-to-end run remains unverified.

The recorded Reader specification names Qwen/Qwen2.5-7B-Instruct revision `fe11104b620d588ccc049ff6631dd3ea002e3d98`. Historical actual loaded tensors, tokenizer execution, and batch membership lack complete run-bound attestation. The dataset publication revision and redistribution rights remain unresolved. Model and data acquisition must follow the respective provider terms and rights-holder instructions.

`scripts/recompute_full_statistics.py` works on the retained sanitized R14 outcomes and does not invoke Reader or Search. `scripts/check_archived_aggregates.py --help` describes a separate, hash-guarded local check for an authorized C summary, C configuration, SetR receipt and R14 statistical summary. The input hashes of the recorded artifacts are listed in `docs/archived_results.md`. The script checks saved point estimates and receipt counts, and does not recalculate historical confidence intervals.
