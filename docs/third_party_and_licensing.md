# Third-party and licensing review

The user confirms authority to license independently owned code under MIT, identifies Xingyun Chen as the copyright holder for 2026, and confirms authority to distribute sanitized derived experimental results and figures. The MIT text and copyright notice appear in `LICENSE`.

The R3.1 manuscript refers to Qwen/Qwen2.5-7B-Instruct, a tokenizer snapshot, PyTorch, bitsandbytes, and other runtime components. Model weights, tokenizer files, package caches, and private runtime outputs are excluded. Their licenses and model terms must be reviewed separately before any public distribution.

The original experiment records contain references to external datasets and annotation exports. This package includes sanitized derived metrics and synthetic fixtures. The user's confirmation covers distribution of derived experimental results and figures, not redistribution of upstream datasets or model weights.

The `rights_status` entries in `source_mapping.json` record the earlier R2 inventory state. They are not a replacement for the later user-confirmed rights described above. A bounded review found no source headers identifying separately licensed third-party code, but absence of notices does not establish origin. External dependencies remain subject to their own licenses and distribution terms.

Paper authors Xingyun Chen and Shiyong Xiong, corresponding author Shiyong Xiong, software author Xingyun Chen, and the affiliation Chongqing University of Posts and Telecommunications were supplied by the user. No license for third-party code, datasets, models, derived data or figures is inferred from MIT for the independently owned code.

The GitHub URL in `CITATION.cff` is the requested remote target. The user authorized public push after release gates pass. No visibility change was authorized.
