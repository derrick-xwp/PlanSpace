# Blinded output-level validity audit

Labels come from agreement between two isolated Codex roles with a third isolated Codex role adjudicating disagreements. They quantify internal adversarial consistency and metric discrimination, not independent human or simulator construct validity.

## Reviewer agreement

| Field | Agreement | Cohen's kappa |
| --- | ---: | ---: |
| interface_compliant | 111/120 (92.5%) | 0.771 |
| valid_at_declared_abstraction | 118/120 (98.3%) | 0.967 |
| reasonable_high_level_behavior | 106/120 (88.3%) | 0.768 |

## Metric discrimination against consensus high-level reasonableness

| Metric | N | Accuracy | Precision | Recall | F1 / AUROC |
| --- | ---: | ---: | ---: | ---: | ---: |
| exact_match | 120 | 0.567 | 1.000 | 0.278 | 0.435 |
| partial_order_match | 120 | 0.733 | 1.000 | 0.556 | 0.714 |
| goal_valid | 120 | 0.900 | 1.000 | 0.833 | 0.909 |
| ordered_action_similarity | 120 | -- | -- | -- | AUROC 0.565 |
