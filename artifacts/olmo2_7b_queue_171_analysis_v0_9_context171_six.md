# Frozen 171-task model analysis

Model: `allenai/OLMo-2-1124-7B-Instruct` at `470b1fba1ae01581f270116362ee4aa1b97f4c84`.

| Metric | Estimate | 95% task-bootstrap CI |
| --- | ---: | ---: |
| parse_success_rate | 15.79% | [11.23%, 20.70%] |
| executable_rate | 6.32% | [3.16%, 9.94%] |
| goal_valid_rate | 5.61% | [2.69%, 9.12%] |
| exact_match_rate | 5.50% | [2.57%, 8.89%] |
| partial_order_match_rate | 5.50% | [2.57%, 8.89%] |
| mean_normalized_cost_regret_among_valid | 0.52% | [0.00%, 2.14%] |
| mean_reference_family_coverage | 7.89% | [4.09%, 11.99%] |
| novel_valid_rate_among_valid | 2.08% | [0.00%, 8.57%] |
| valid_minus_exact | 0.12% | [0.00%, 0.35%] |
| single_reference_false_rejection_among_valid | 2.08% | [0.00%, 8.57%] |

| Diversity metric | Value |
| --- | ---: |
| First-sample goal validity | 4.68% |
| Any-of-5 goal validity | 8.77% |
| Any-of-5 exact match | 8.19% |
| Unique valid plans per task | 0.088 |
| Unique fraction among valid samples | 31.25% |
| Mean validated reference-family coverage | 7.89% |
| Novel valid outputs among valid | 2.08% |
| Mean normalized cost regret among valid | 0.005 |

| Failure category | Count |
| --- | ---: |
| length_cap | 0 |
| parse | 720 |
| precondition | 81 |
| goal_miss | 6 |
| valid_exact | 47 |
| valid_nonexact | 1 |

| Parse/format subtype | Count |
| --- | ---: |
| invalid_json | 3 |
| no_json_object | 1 |
| schema | 10 |
| unknown_action_id | 706 |

## structural_split

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iid_core | 24 | 120 | 20.83% | 20.83% | 20.83% | 20.83% |
| ood_commutation | 89 | 445 | 3.60% | 3.60% | 3.60% | 7.87% |
| ood_goal_choice | 26 | 130 | 4.62% | 3.85% | 3.85% | 7.69% |
| ood_long_horizon | 25 | 125 | 0.80% | 0.80% | 0.80% | 4.00% |
| ood_operator_composition | 7 | 35 | 0.00% | 0.00% | 0.00% | 0.00% |

## operator_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CLOSE+OPEN+TRANSFER | 15 | 75 | 1.33% | 0.00% | 0.00% | 6.67% |
| CLOSE+TRANSFER | 2 | 10 | 10.00% | 10.00% | 10.00% | 50.00% |
| OPEN | 2 | 10 | 50.00% | 50.00% | 50.00% | 50.00% |
| OPEN+TOGGLE_ON+TRANSFER | 1 | 5 | 0.00% | 0.00% | 0.00% | 0.00% |
| OPEN+TRANSFER | 67 | 335 | 0.60% | 0.60% | 0.60% | 1.49% |
| TOGGLE_OFF | 3 | 15 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON+TRANSFER | 2 | 10 | 50.00% | 50.00% | 50.00% | 50.00% |
| TRANSFER | 77 | 385 | 2.34% | 2.34% | 2.34% | 6.49% |

## multiplicity_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 145 | 725 | 3.17% | 3.03% | 3.03% | 6.90% |
| single | 26 | 130 | 19.23% | 19.23% | 19.23% | 19.23% |

## length_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-3 | 62 | 310 | 12.58% | 12.58% | 12.58% | 17.74% |
| 4-6 | 70 | 350 | 2.29% | 2.00% | 2.00% | 4.29% |
| 7+ | 39 | 195 | 0.51% | 0.51% | 0.51% | 2.56% |
