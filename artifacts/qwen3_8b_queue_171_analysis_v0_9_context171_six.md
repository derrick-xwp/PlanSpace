# Frozen 171-task model analysis

Model: `Qwen/Qwen3-8B` at `b968826d9c46dd6066d109eabc6255188de91218`.

| Metric | Estimate | 95% task-bootstrap CI |
| --- | ---: | ---: |
| parse_success_rate | 87.95% | [83.27%, 92.28%] |
| executable_rate | 86.08% | [81.17%, 90.64%] |
| goal_valid_rate | 82.81% | [77.31%, 88.07%] |
| exact_match_rate | 65.61% | [58.71%, 72.51%] |
| partial_order_match_rate | 70.41% | [63.74%, 76.96%] |
| mean_normalized_cost_regret_among_valid | 3.24% | [1.05%, 6.14%] |
| mean_reference_family_coverage | 69.09% | [62.26%, 75.81%] |
| novel_valid_rate_among_valid | 14.97% | [9.39%, 20.75%] |
| valid_minus_exact | 17.19% | [11.93%, 22.57%] |
| single_reference_false_rejection_among_valid | 20.76% | [14.43%, 27.26%] |

| Diversity metric | Value |
| --- | ---: |
| First-sample goal validity | 81.87% |
| Any-of-5 goal validity | 87.72% |
| Any-of-5 exact match | 69.59% |
| Unique valid plans per task | 0.930 |
| Unique fraction among valid samples | 22.46% |
| Mean validated reference-family coverage | 69.09% |
| Novel valid outputs among valid | 14.97% |
| Mean normalized cost regret among valid | 0.032 |

| Failure category | Count |
| --- | ---: |
| length_cap | 0 |
| parse | 103 |
| precondition | 16 |
| goal_miss | 28 |
| valid_exact | 561 |
| valid_nonexact | 147 |

| Parse/format subtype | Count |
| --- | ---: |
| unknown_action_id | 103 |

## structural_split

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iid_core | 24 | 120 | 92.50% | 84.17% | 84.17% | 95.83% |
| ood_commutation | 89 | 445 | 81.80% | 76.18% | 77.30% | 85.39% |
| ood_goal_choice | 26 | 130 | 83.08% | 33.85% | 53.08% | 92.31% |
| ood_long_horizon | 25 | 125 | 84.00% | 49.60% | 58.40% | 92.00% |
| ood_operator_composition | 7 | 35 | 57.14% | 42.86% | 42.86% | 57.14% |

## operator_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CLOSE+OPEN+TRANSFER | 15 | 75 | 64.00% | 41.33% | 52.00% | 73.33% |
| CLOSE+TRANSFER | 2 | 10 | 100.00% | 50.00% | 50.00% | 100.00% |
| OPEN | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| OPEN+TOGGLE_ON+TRANSFER | 1 | 5 | 100.00% | 0.00% | 0.00% | 100.00% |
| OPEN+TRANSFER | 67 | 335 | 94.93% | 68.36% | 70.15% | 97.01% |
| TOGGLE_OFF | 3 | 15 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON+TRANSFER | 2 | 10 | 0.00% | 0.00% | 0.00% | 0.00% |
| TRANSFER | 77 | 385 | 75.84% | 67.79% | 74.81% | 83.12% |

## multiplicity_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 145 | 725 | 82.34% | 63.45% | 69.10% | 87.59% |
| single | 26 | 130 | 85.38% | 77.69% | 77.69% | 88.46% |

## length_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-3 | 62 | 310 | 76.77% | 72.90% | 73.55% | 79.03% |
| 4-6 | 70 | 350 | 88.00% | 73.14% | 76.00% | 92.86% |
| 7+ | 39 | 195 | 83.08% | 40.51% | 55.38% | 92.31% |
