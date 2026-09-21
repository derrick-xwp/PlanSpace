# Cost-bounded goal validity

A plan is accepted at threshold tau iff replay reaches the goal and (plan_cost - minimum_reference_cost) / minimum_reference_cost <= tau.

| Model | Goal-valid | tau=0 | tau=0.25 | tau=0.5 | tau=1.0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| mistralai/Mistral-7B-Instruct-v0.3 | 75.2 | 72.7 | 73.5 | 73.7 | 75.2 |
| allenai/OLMo-2-1124-7B-Instruct | 5.6 | 5.5 | 5.6 | 5.6 | 5.6 |
| microsoft/Phi-4-mini-instruct | 7.6 | 7.5 | 7.6 | 7.6 | 7.6 |
| Qwen/Qwen3-14B | 94.7 | 90.9 | 93.6 | 93.6 | 94.7 |
| Qwen/Qwen3-4B | 93.0 | 86.2 | 90.4 | 91.2 | 92.4 |
| Qwen/Qwen3-8B | 82.8 | 76.0 | 81.1 | 81.1 | 82.2 |
