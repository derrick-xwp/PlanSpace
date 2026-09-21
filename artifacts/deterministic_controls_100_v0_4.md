# Deterministic 100-task controls

v0.4 semantics passed the frozen internal AI gate; independent human validation remains pending.

| Control | Tasks | Goal valid | Partial-order match | Exact match |
| --- | ---: | ---: | ---: | ---: |
| Valid alternative/fallback | 100 | 100.00% | 100.00% | 19.00% |
| Required-action deletion | 100 | 0.00% | -- | -- |

Non-reference positive controls: 81/100; exact-match false rejection on that supported subset: 100.00%.

Deletion failures: 0 precondition failures and 100 executable goal misses.
