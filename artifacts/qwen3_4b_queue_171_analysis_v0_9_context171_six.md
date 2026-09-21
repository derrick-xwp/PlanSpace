# Frozen 171-task model analysis

Model: `Qwen/Qwen3-4B` at `1cfa9a7208912126459214e8b04321603b3df60c`.

| Metric | Estimate | 95% task-bootstrap CI |
| --- | ---: | ---: |
| parse_success_rate | 99.42% | [98.48%, 100.00%] |
| executable_rate | 97.54% | [95.20%, 99.30%] |
| goal_valid_rate | 92.98% | [89.12%, 96.37%] |
| exact_match_rate | 75.56% | [69.12%, 81.87%] |
| partial_order_match_rate | 79.65% | [73.68%, 85.38%] |
| mean_normalized_cost_regret_among_valid | 3.10% | [1.09%, 5.69%] |
| mean_reference_family_coverage | 74.64% | [68.29%, 80.96%] |
| novel_valid_rate_among_valid | 14.34% | [9.14%, 19.80%] |
| valid_minus_exact | 17.43% | [11.93%, 23.04%] |
| single_reference_false_rejection_among_valid | 18.74% | [12.89%, 24.84%] |

| Diversity metric | Value |
| --- | ---: |
| First-sample goal validity | 92.40% |
| Any-of-5 goal validity | 94.15% |
| Any-of-5 exact match | 76.02% |
| Unique valid plans per task | 0.959 |
| Unique fraction among valid samples | 20.63% |
| Mean validated reference-family coverage | 74.64% |
| Novel valid outputs among valid | 14.34% |
| Mean normalized cost regret among valid | 0.031 |

| Failure category | Count |
| --- | ---: |
| length_cap | 0 |
| parse | 5 |
| precondition | 16 |
| goal_miss | 39 |
| valid_exact | 646 |
| valid_nonexact | 149 |

| Parse/format subtype | Count |
| --- | ---: |
| unknown_action_id | 5 |

## structural_split

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iid_core | 24 | 120 | 100.00% | 83.33% | 83.33% | 100.00% |
| ood_commutation | 89 | 445 | 98.65% | 92.81% | 94.16% | 100.00% |
| ood_goal_choice | 26 | 130 | 93.85% | 42.31% | 53.08% | 96.15% |
| ood_long_horizon | 25 | 125 | 83.20% | 55.20% | 67.20% | 84.00% |
| ood_operator_composition | 7 | 35 | 28.57% | 25.71% | 25.71% | 28.57% |

## operator_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CLOSE+OPEN+TRANSFER | 15 | 75 | 56.00% | 25.33% | 32.00% | 60.00% |
| CLOSE+TRANSFER | 2 | 10 | 40.00% | 40.00% | 40.00% | 50.00% |
| OPEN | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| OPEN+TOGGLE_ON+TRANSFER | 1 | 5 | 0.00% | 0.00% | 0.00% | 0.00% |
| OPEN+TRANSFER | 67 | 335 | 95.52% | 69.85% | 71.34% | 97.01% |
| TOGGLE_OFF | 3 | 15 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON+TRANSFER | 2 | 10 | 100.00% | 0.00% | 0.00% | 100.00% |
| TRANSFER | 77 | 385 | 99.74% | 91.95% | 98.44% | 100.00% |

## multiplicity_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 145 | 725 | 93.10% | 75.31% | 80.14% | 94.48% |
| single | 26 | 130 | 92.31% | 76.92% | 76.92% | 92.31% |

## length_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-3 | 62 | 310 | 96.77% | 88.71% | 88.71% | 96.77% |
| 4-6 | 70 | 350 | 93.14% | 80.57% | 83.71% | 95.71% |
| 7+ | 39 | 195 | 86.67% | 45.64% | 57.95% | 87.18% |
