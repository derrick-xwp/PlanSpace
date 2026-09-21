# Independent state-space search audit

The search never consumes reference plans, reference DAGs, or deterministic controls. It shares the frozen grounded action semantics and goal predicate with the evaluator, so it is an independent search implementation rather than external semantic validation.

- Tasks: 171
- Tasks with an independently discovered solution: 161
- Tasks with an independently discovered non-reference solution: 145
- Distinct discovered solutions: 2084
- Distinct non-reference solutions: 1939
- Tasks hitting a resource bound: 30
