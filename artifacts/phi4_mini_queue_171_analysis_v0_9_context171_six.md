# Frozen 171-task model analysis

Model: `microsoft/Phi-4-mini-instruct` at `cfbefacb99257ffa30c83adab238a50856ac3083`.

| Metric | Estimate | 95% task-bootstrap CI |
| --- | ---: | ---: |
| parse_success_rate | 20.58% | [16.84%, 24.68%] |
| executable_rate | 9.47% | [7.02%, 12.28%] |
| goal_valid_rate | 7.60% | [5.26%, 10.18%] |
| exact_match_rate | 6.90% | [4.68%, 9.36%] |
| partial_order_match_rate | 7.49% | [5.15%, 10.18%] |
| mean_normalized_cost_regret_among_valid | 0.22% | [0.00%, 0.77%] |
| mean_reference_family_coverage | 20.80% | [14.95%, 26.98%] |
| novel_valid_rate_among_valid | 1.54% | [0.00%, 5.36%] |
| valid_minus_exact | 0.70% | [0.12%, 1.64%] |
| single_reference_false_rejection_among_valid | 9.23% | [1.43%, 20.01%] |

| Diversity metric | Value |
| --- | ---: |
| First-sample goal validity | 7.02% |
| Any-of-5 goal validity | 23.39% |
| Any-of-5 exact match | 21.64% |
| Unique valid plans per task | 0.240 |
| Unique fraction among valid samples | 63.08% |
| Mean validated reference-family coverage | 20.80% |
| Novel valid outputs among valid | 1.54% |
| Mean normalized cost regret among valid | 0.002 |

| Failure category | Count |
| --- | ---: |
| length_cap | 12 |
| parse | 667 |
| precondition | 95 |
| goal_miss | 16 |
| valid_exact | 59 |
| valid_nonexact | 6 |

| Parse/format subtype | Count |
| --- | ---: |
| length_cap | 12 |
| unknown_action_id | 667 |

## structural_split

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| iid_core | 24 | 120 | 20.00% | 20.00% | 20.00% | 54.17% |
| ood_commutation | 89 | 445 | 3.82% | 3.60% | 3.82% | 12.36% |
| ood_goal_choice | 26 | 130 | 7.69% | 3.85% | 6.92% | 26.92% |
| ood_long_horizon | 25 | 125 | 11.20% | 11.20% | 11.20% | 36.00% |
| ood_operator_composition | 7 | 35 | 0.00% | 0.00% | 0.00% | 0.00% |

## operator_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| CLOSE+OPEN+TRANSFER | 15 | 75 | 0.00% | 0.00% | 0.00% | 0.00% |
| CLOSE+TRANSFER | 2 | 10 | 10.00% | 10.00% | 10.00% | 50.00% |
| OPEN | 2 | 10 | 0.00% | 0.00% | 0.00% | 0.00% |
| OPEN+TOGGLE_ON+TRANSFER | 1 | 5 | 0.00% | 0.00% | 0.00% | 0.00% |
| OPEN+TRANSFER | 67 | 335 | 9.85% | 9.55% | 9.55% | 32.84% |
| TOGGLE_OFF | 3 | 15 | 13.33% | 13.33% | 13.33% | 66.67% |
| TOGGLE_ON | 2 | 10 | 70.00% | 70.00% | 70.00% | 100.00% |
| TOGGLE_ON+TRANSFER | 2 | 10 | 60.00% | 30.00% | 60.00% | 100.00% |
| TRANSFER | 77 | 385 | 4.16% | 3.64% | 4.16% | 14.29% |

## multiplicity_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| multiple | 145 | 725 | 5.66% | 4.83% | 5.52% | 18.62% |
| single | 26 | 130 | 18.46% | 18.46% | 18.46% | 50.00% |

## length_stratum

| Stratum | Tasks | Samples | Goal valid | Exact | Partial order | Any-of-five valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-3 | 62 | 310 | 10.32% | 9.03% | 10.32% | 27.42% |
| 4-6 | 70 | 350 | 4.57% | 4.57% | 4.57% | 15.71% |
| 7+ | 39 | 195 | 8.72% | 7.69% | 8.21% | 30.77% |
