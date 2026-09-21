# Frozen 171-task model analysis

Model: `mistralai/Mistral-7B-Instruct-v0.3` at `c170c708c41dac9275d15a8fff4eca08d52bab71`.

| Metric | Estimate | 95% task-bootstrap CI |
| --- | ---: | ---: |
| parse_success_rate | 86.20% | [81.87%, 90.18%] |
| executable_rate | 80.82% | [75.79%, 85.61%] |
| goal_valid_rate | 75.20% | [69.47%, 80.70%] |
| exact_match_rate | 66.78% | [60.47%, 72.99%] |
| partial_order_match_rate | 69.36% | [63.27%, 75.44%] |
| mean_normalized_cost_regret_among_valid | 2.09% | [0.15%, 4.59%] |
| mean_reference_family_coverage | 74.57% | [68.21%, 80.78%] |
| novel_valid_rate_among_valid | 7.78% | [3.81%, 12.26%] |
| valid_minus_exact | 8.42% | [4.91%, 12.28%] |
| single_reference_false_rejection_among_valid | 11.20% | [6.61%, 16.27%] |

| Diversity metric | Value |
| --- | ---: |
| First-sample goal validity | 74.85% |
| Any-of-5 goal validity | 85.96% |
| Any-of-5 exact match | 77.19% |
| Unique valid plans per task | 0.924 |
| Unique fraction among valid samples | 24.57% |
| Mean validated reference-family coverage | 74.57% |
| Novel valid outputs among valid | 7.78% |
| Mean normalized cost regret among valid | 0.021 |

| Failure category | Count |
| --- | ---: |
| length_cap | 10 |
| parse | 108 |
| precondition | 46 |
| goal_miss | 48 |
| valid_exact | 571 |
| valid_nonexact | 72 |

| Parse/format subtype | Count |
| --- | ---: |
| length_cap | 10 |
| no_json_object | 30 |
| unknown_action_id | 78 |

## structural_split

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iid_core | 24 | 120 | 74.17% | 64.17% | 64.17% | 83.33% |
| ood_commutation | 89 | 445 | 89.44% | 81.80% | 83.37% | 100.00% |
| ood_goal_choice | 26 | 130 | 50.00% | 34.62% | 46.15% | 65.38% |
| ood_long_horizon | 25 | 125 | 63.20% | 62.40% | 62.40% | 72.00% |
| ood_operator_composition | 7 | 35 | 34.29% | 20.00% | 20.00% | 42.86% |

## operator_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CLOSE+OPEN+TRANSFER | 15 | 75 | 26.67% | 21.33% | 26.67% | 40.00% |
| CLOSE+TRANSFER | 2 | 10 | 50.00% | 50.00% | 50.00% | 50.00% |
| OPEN | 2 | 10 | 90.00% | 90.00% | 90.00% | 100.00% |
| OPEN+TOGGLE_ON+TRANSFER | 1 | 5 | 100.00% | 0.00% | 0.00% | 100.00% |
| OPEN+TRANSFER | 67 | 335 | 73.73% | 64.18% | 64.18% | 85.07% |
| TOGGLE_OFF | 3 | 15 | 33.33% | 33.33% | 33.33% | 33.33% |
| TOGGLE_ON | 2 | 10 | 80.00% | 80.00% | 80.00% | 100.00% |
| TOGGLE_ON+TRANSFER | 2 | 10 | 100.00% | 40.00% | 40.00% | 100.00% |
| TRANSFER | 77 | 385 | 86.75% | 80.26% | 84.94% | 97.40% |

## multiplicity_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 145 | 725 | 76.41% | 68.14% | 71.17% | 87.59% |
| single | 26 | 130 | 68.46% | 59.23% | 59.23% | 76.92% |

## length_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-3 | 62 | 310 | 83.55% | 76.13% | 76.13% | 90.32% |
| 4-6 | 70 | 350 | 78.86% | 68.86% | 71.71% | 91.43% |
| 7+ | 39 | 195 | 55.38% | 48.21% | 54.36% | 69.23% |
