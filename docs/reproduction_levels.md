# Reproduction levels

## Level 1

Verified for included sanitized R14 outcomes. Seven metrics and ten contrasts, full question and cluster bootstrap, LOCO and McNemar outputs match official frozen results. CSV tables and two quantitative figures are generated from this replay. Complete H/C/external and exact manuscript-layout replay remain open.

## Level 2

Partially validated. The namespaced historical P3 wrapper runs on a fixed synthetic candidate pool. Unit tests check proxy availability, mixed valid/invalid chain behavior, fallback selection keys, structural-first ordering, the separate R14 Clean A beam and exact-final keys, and the no-Gold-input validator. The separate fixed-pool runner also returns four R14 cells on synthetic data, including a generated tokenizer JSON through the real CLI. Formal tokenizer/cohort execution is unverified.

## Level 3

Unverified and guarded. The package includes a preflight command and an external path template. A complete historical run would require separately authorized datasets, model assets, runtime versions, dependency identities, and formal experiment authorization.
