# 6-model paired comparison

All values use the same 171 tasks and 5 samples per task.

| Model | Parse | Executable | Goal valid | Exact | Partial order | False rejection among valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-4B | 99.42% | 97.54% | 92.98% | 75.56% | 79.65% | 18.74% |
| microsoft/Phi-4-mini-instruct | 20.58% | 9.47% | 7.60% | 6.90% | 7.49% | 9.23% |
| mistralai/Mistral-7B-Instruct-v0.3 | 86.20% | 80.82% | 75.20% | 66.78% | 69.36% | 11.20% |
| allenai/OLMo-2-1124-7B-Instruct | 15.79% | 6.32% | 5.61% | 5.50% | 5.50% | 2.08% |
| Qwen/Qwen3-8B | 87.95% | 86.08% | 82.81% | 65.61% | 70.41% | 20.76% |
| Qwen/Qwen3-14B | 99.18% | 94.74% | 94.74% | 80.12% | 84.56% | 15.43% |

## Sampling diversity and cost

| Model | First-sample goal | Any-of-five goal | Family coverage | Mean cost regret |
| --- | ---: | ---: | ---: | ---: |
| Qwen/Qwen3-4B | 92.40% | 94.15% | 74.64% | 0.031 |
| microsoft/Phi-4-mini-instruct | 7.02% | 23.39% | 20.80% | 0.002 |
| mistralai/Mistral-7B-Instruct-v0.3 | 74.85% | 85.96% | 74.57% | 0.021 |
| allenai/OLMo-2-1124-7B-Instruct | 4.68% | 8.77% | 7.89% | 0.005 |
| Qwen/Qwen3-8B | 81.87% | 87.72% | 69.09% | 0.032 |
| Qwen/Qwen3-14B | 94.74% | 95.91% | 78.27% | 0.016 |

## Paired task-bootstrap differences

### Qwen/Qwen3-4B minus microsoft/Phi-4-mini-instruct

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +68.65% | [+62.22%, +74.74%] | 0.0015 |
| partial_order | +72.16% | [+65.73%, +78.36%] | 0.0015 |
| goal_valid | +85.38% | [+81.05%, +89.47%] | 0.0015 |

### Qwen/Qwen3-4B minus mistralai/Mistral-7B-Instruct-v0.3

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +8.77% | [+2.69%, +14.74%] | 0.0192 |
| partial_order | +10.29% | [+4.68%, +15.67%] | 0.0020 |
| goal_valid | +17.78% | [+12.28%, +23.39%] | 0.0015 |

### Qwen/Qwen3-4B minus allenai/OLMo-2-1124-7B-Instruct

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +70.06% | [+63.15%, +76.73%] | 0.0015 |
| partial_order | +74.15% | [+67.37%, +80.58%] | 0.0015 |
| goal_valid | +87.37% | [+82.46%, +91.93%] | 0.0015 |

### Qwen/Qwen3-4B minus Qwen/Qwen3-8B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +9.94% | [+4.21%, +15.91%] | 0.0050 |
| partial_order | +9.24% | [+3.63%, +15.20%] | 0.0068 |
| goal_valid | +10.18% | [+4.56%, +15.91%] | 0.0036 |

### Qwen/Qwen3-4B minus Qwen/Qwen3-14B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -4.56% | [-10.29%, +1.05%] | 0.3528 |
| partial_order | -4.91% | [-10.29%, +0.47%] | 0.2613 |
| goal_valid | -1.75% | [-5.73%, +2.22%] | 0.5123 |

### microsoft/Phi-4-mini-instruct minus mistralai/Mistral-7B-Instruct-v0.3

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -59.88% | [-66.55%, -53.22%] | 0.0015 |
| partial_order | -61.87% | [-68.30%, -55.32%] | 0.0015 |
| goal_valid | -67.60% | [-73.33%, -61.64%] | 0.0015 |

### microsoft/Phi-4-mini-instruct minus allenai/OLMo-2-1124-7B-Instruct

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +1.40% | [-1.99%, +4.56%] | 0.9133 |
| partial_order | +1.99% | [-1.17%, +5.15%] | 0.5023 |
| goal_valid | +1.99% | [-1.29%, +5.03%] | 0.5123 |

### microsoft/Phi-4-mini-instruct minus Qwen/Qwen3-8B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -58.71% | [-65.38%, -51.93%] | 0.0015 |
| partial_order | -62.92% | [-69.36%, -56.26%] | 0.0015 |
| goal_valid | -75.20% | [-80.70%, -69.36%] | 0.0015 |

### microsoft/Phi-4-mini-instruct minus Qwen/Qwen3-14B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -73.22% | [-78.95%, -67.37%] | 0.0015 |
| partial_order | -77.08% | [-82.11%, -71.46%] | 0.0015 |
| goal_valid | -87.13% | [-90.76%, -83.16%] | 0.0015 |

### mistralai/Mistral-7B-Instruct-v0.3 minus allenai/OLMo-2-1124-7B-Instruct

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +61.29% | [+54.15%, +68.19%] | 0.0015 |
| partial_order | +63.86% | [+56.84%, +70.53%] | 0.0015 |
| goal_valid | +69.59% | [+62.81%, +75.79%] | 0.0015 |

### mistralai/Mistral-7B-Instruct-v0.3 minus Qwen/Qwen3-8B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | +1.17% | [-6.08%, +8.65%] | 0.9133 |
| partial_order | -1.05% | [-8.07%, +6.08%] | 0.8021 |
| goal_valid | -7.60% | [-15.09%, -0.23%] | 0.1554 |

### mistralai/Mistral-7B-Instruct-v0.3 minus Qwen/Qwen3-14B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -13.33% | [-19.18%, -7.49%] | 0.0015 |
| partial_order | -15.20% | [-20.58%, -10.06%] | 0.0015 |
| goal_valid | -19.53% | [-24.91%, -14.39%] | 0.0015 |

### allenai/OLMo-2-1124-7B-Instruct minus Qwen/Qwen3-8B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -60.12% | [-67.14%, -52.75%] | 0.0015 |
| partial_order | -64.91% | [-71.70%, -57.89%] | 0.0015 |
| goal_valid | -77.19% | [-83.04%, -70.88%] | 0.0015 |

### allenai/OLMo-2-1124-7B-Instruct minus Qwen/Qwen3-14B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -74.62% | [-80.94%, -68.19%] | 0.0015 |
| partial_order | -79.06% | [-84.91%, -73.10%] | 0.0015 |
| goal_valid | -89.12% | [-93.22%, -84.68%] | 0.0015 |

### Qwen/Qwen3-8B minus Qwen/Qwen3-14B

| Metric | Difference | 95% CI | Holm p |
| --- | ---: | ---: | ---: |
| exact | -14.50% | [-21.17%, -7.84%] | 0.0015 |
| partial_order | -14.15% | [-20.82%, -7.84%] | 0.0015 |
| goal_valid | -11.93% | [-17.89%, -5.96%] | 0.0015 |

## Rankings

- exact: Qwen/Qwen3-14B > Qwen/Qwen3-4B > mistralai/Mistral-7B-Instruct-v0.3 > Qwen/Qwen3-8B > microsoft/Phi-4-mini-instruct > allenai/OLMo-2-1124-7B-Instruct
- partial_order: Qwen/Qwen3-14B > Qwen/Qwen3-4B > Qwen/Qwen3-8B > mistralai/Mistral-7B-Instruct-v0.3 > microsoft/Phi-4-mini-instruct > allenai/OLMo-2-1124-7B-Instruct
- goal_valid: Qwen/Qwen3-14B > Qwen/Qwen3-4B > Qwen/Qwen3-8B > mistralai/Mistral-7B-Instruct-v0.3 > microsoft/Phi-4-mini-instruct > allenai/OLMo-2-1124-7B-Instruct
