# Blinded output-level validity audit

Consensus labels come from two isolated Codex roles. They quantify internal adversarial consistency and metric discrimination, not independent human or simulator construct validity.

## Reviewer agreement

| Field | Agreement | Cohen's kappa |
| --- | ---: | ---: |
| interface_compliant | 111/120 (92.5%) | 0.771 |
| valid_at_declared_abstraction | 118/120 (98.3%) | 0.967 |
| reasonable_high_level_behavior | 106/120 (88.3%) | 0.768 |

## Metric discrimination against consensus high-level reasonableness

| Metric | N | Accuracy | Precision | Recall | F1 / AUROC |
| --- | ---: | ---: | ---: | ---: | ---: |
| exact_match | 106 | 0.642 | 1.000 | 0.345 | 0.513 |
| partial_order_match | 106 | 0.830 | 1.000 | 0.690 | 0.816 |
| goal_valid | 106 | 1.000 | 1.000 | 1.000 | 1.000 |
| ordered_action_similarity | 106 | -- | -- | -- | AUROC 0.655 |
