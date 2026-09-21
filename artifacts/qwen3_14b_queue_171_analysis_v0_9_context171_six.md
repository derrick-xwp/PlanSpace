# Frozen 171-task model analysis

Model: `Qwen/Qwen3-14B` at `40c069824f4251a91eefaf281ebe4c544efd3e18`.

| Metric | Estimate | 95% task-bootstrap CI |
| --- | ---: | ---: |
| parse_success_rate | 99.18% | [97.78%, 100.00%] |
| executable_rate | 94.74% | [91.35%, 97.66%] |
| goal_valid_rate | 94.74% | [91.35%, 97.66%] |
| exact_match_rate | 80.12% | [73.92%, 85.96%] |
| partial_order_match_rate | 84.56% | [79.06%, 89.82%] |
| mean_normalized_cost_regret_among_valid | 1.55% | [0.31%, 3.28%] |
| mean_reference_family_coverage | 78.27% | [72.45%, 83.99%] |
| novel_valid_rate_among_valid | 10.74% | [6.27%, 15.38%] |
| valid_minus_exact | 14.62% | [9.59%, 19.88%] |
| single_reference_false_rejection_among_valid | 15.43% | [10.15%, 21.05%] |

| Diversity metric | Value |
| --- | ---: |
| First-sample goal validity | 94.74% |
| Any-of-5 goal validity | 95.91% |
| Any-of-5 exact match | 80.70% |
| Unique valid plans per task | 0.971 |
| Unique fraction among valid samples | 20.49% |
| Mean validated reference-family coverage | 78.27% |
| Novel valid outputs among valid | 10.74% |
| Mean normalized cost regret among valid | 0.016 |

| Failure category | Count |
| --- | ---: |
| length_cap | 0 |
| parse | 7 |
| precondition | 38 |
| goal_miss | 0 |
| valid_exact | 685 |
| valid_nonexact | 125 |

| Parse/format subtype | Count |
| --- | ---: |
| unknown_action_id | 7 |

## structural_split

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iid_core | 24 | 120 | 100.00% | 95.83% | 95.83% | 100.00% |
| ood_commutation | 89 | 445 | 99.55% | 91.01% | 93.26% | 100.00% |
| ood_goal_choice | 26 | 130 | 86.92% | 57.69% | 65.38% | 88.46% |
| ood_long_horizon | 25 | 125 | 90.40% | 59.20% | 73.60% | 92.00% |
| ood_operator_composition | 7 | 35 | 60.00% | 45.71% | 45.71% | 71.43% |

## operator_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CLOSE+OPEN+TRANSFER | 15 | 75 | 57.33% | 41.33% | 41.33% | 66.67% |
| CLOSE+TRANSFER | 2 | 10 | 100.00% | 50.00% | 80.00% | 100.00% |
| OPEN | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| OPEN+TOGGLE_ON+TRANSFER | 1 | 5 | 100.00% | 0.00% | 0.00% | 100.00% |
| OPEN+TRANSFER | 67 | 335 | 96.12% | 78.81% | 80.30% | 97.01% |
| TOGGLE_OFF | 3 | 15 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| TOGGLE_ON+TRANSFER | 2 | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| TRANSFER | 77 | 385 | 100.00% | 88.31% | 96.10% | 100.00% |

## multiplicity_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 145 | 725 | 94.34% | 77.79% | 83.03% | 95.17% |
| single | 26 | 130 | 96.92% | 93.08% | 93.08% | 100.00% |

## length_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-3 | 62 | 310 | 98.71% | 95.48% | 95.48% | 100.00% |
| 4-6 | 70 | 350 | 95.14% | 81.43% | 84.29% | 95.71% |
| 7+ | 39 | 195 | 87.69% | 53.33% | 67.69% | 89.74% |
