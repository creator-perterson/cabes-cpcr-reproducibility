# Algorithm scope

CABES is represented by the selected frozen BlockSearch implementation and its base scoring modules. The copied code keeps the candidate pool, relevance, token budget, transition limits, objective components, beam width, path cost, global edit counters, and deterministic tie keys at the same algorithm boundary as the recorded source.

CPCR is represented by a structural chain coverage proxy layered on the CABES state objects. The proxy counts structurally valid chains whose evidence UIDs are fully contained in the selected state. Structural validity requires the retained bridge identity and relation-alignment fields. An absent or empty chain universe, or a universe with no structurally valid records, makes the proxy unavailable and retains the original CABES ordering. Invalid records in a mixed universe are ignored by the frozen proxy while valid records remain countable.

The historical P3 CPCR wrapper uses proxy-first retention and final selection followed by the historical rounded-objective, path-cost, token-count, and UID tie keys. `src/cpcr/clean_factorial.py` is a separate R14 implementation. It retains the original rounded-objective beam tie key and applies an exact-objective final key, with coverage priority independently enabled for beam retention and final selection. The Clean A11 cell enables both R14 coverage-priority rules. It is not the historical P3 CPCR implementation. `src/cpcr/factorial_search.py` contains the original R14 `FactorialSearch` and `run_one` bodies with package imports adapted and external inputs injected.

Unit tests cover the historical proxy's mixed-record behavior, unavailable-proxy fallback keys, and structural-first ordering. They separately test the R14 Clean A beam and exact-objective final selection keys. The smoke path executes the copied historical wrapper on a synthetic candidate pool.

The package does not claim semantic relation correctness, independent evidence units, historical runtime loading identity, or end-to-end equivalence to the formal Reader runs.
