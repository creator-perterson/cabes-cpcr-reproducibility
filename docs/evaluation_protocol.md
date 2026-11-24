# Evaluation protocol

R14 Level 1 contains 7,825 rows, 1,565 questions and five methods. Original record, question and first-seen cluster order is preserved for random-draw replay. Linkable hashes are replaced by local integer indices.

The basic script validates duplicate identities, full method grids and finite values. Expected means and point contrasts are copied directly from the frozen official statistics file with its source SHA-256.

The full statistics script invokes an AST-identical statistics function extracted from the original R14 evaluator. It replays seven metrics, ten contrasts, 10,000 PCG64 draws at seed 20261122, question and cluster intervals, LOCO, exact McNemar, effective denominators and cost summaries. Every output field matches frozen official statistics at absolute and relative tolerance 1e-12. Selector generation diagnostics remain prior evidence.

SetR empty selections retain the 1,565-question denominator. Undefined precision keeps effective n=1,505. Cluster draws weight by finite question counts. The 218 components include one of 1,248 questions. Inference and component exchangeability retain the exploratory limits recorded by R3.1.

Full H/C/external and matched-budget manuscript table replay remains open. Their stored identities and source inventories are retained independently.
