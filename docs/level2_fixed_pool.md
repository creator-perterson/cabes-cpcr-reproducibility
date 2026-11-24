# R14 fixed-pool entry point

`scripts/run_fixed_pool.py` exposes the original R14 `FactorialSearch` class and `run_one` bodies after import-only packaging. A single question produces A00, A01, A10 and A11 cells. Each pair of final choices shares its corresponding B0 or B1 trajectory.

Inputs must be frozen JSONL search records with `question_id`, `question`, `evidence`, `chains`, `relevance`, `demand` and `candidate_universe_sha256`. Evidence records use the historical `sentence_uid`, document, sentence position, rank and text fields. The top-level historical label-field validator executes before search. Nested data semantics remain the caller's responsibility under the historical contract.

The command requires `tokenizers` as listed in `environment/fixed-pool-requirements.txt`, a local tokenizer JSON file, its expected SHA-256 and an explicit JSON configuration derived from the recorded CABES-v0.1.2 configuration. The runner enforces a 256-token ceiling through the historical `run_one` implementation. The configuration's `context_budget` field does not change that fixed ceiling. The output must not already exist. Synthetic tests exercise the CLI with a locally generated tokenizer JSON and do not establish historical tokenizer equivalence.

```text
python scripts/run_fixed_pool.py --input fixed_inputs.jsonl --tokenizer tokenizer.json --tokenizer-sha256 EXPECTED_SHA256 --config configs/r14_search.json --output results/local/selections.jsonl
```

The tokenizer and dataset are controlled external assets. The Reader model revision recorded in the R3.1 supplement is `fe11104b620d588ccc049ff6631dd3ea002e3d98`. It is not loaded by this fixed-pool Search command. Tokenizer paths and hashes must be supplied by the authorized asset provider. A generated synthetic tokenizer and synthetic records were used to check the CLI. The formal frozen-cohort path remains unverified.
