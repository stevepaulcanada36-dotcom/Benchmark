# security-bench results (pilot)

Generated 2026-11-21. 95% CIs from a cluster bootstrap over items (runs kept together). Flip rate = share of items whose outcome changed between runs.

Models as reported by the API: Claude: fake; DeepSeek: fake; OpenAI: fake

## Suite D

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| leak_rate | Claude | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |
| leak_rate | DeepSeek | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |
| leak_rate | OpenAI | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |
| partial_leak_rate | Claude | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |
| partial_leak_rate | DeepSeek | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |
| partial_leak_rate | OpenAI | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |

## Pairwise differences (paired bootstrap, Holm-adjusted p)

| Suite | Metric | A - B | Diff | 95% CI | p (Holm) |
|---|---|---|---|---|---|
| D | leak_rate | Claude - DeepSeek | +0.0 pts | +0.0 to +0.0 | 1.000 |
| D | leak_rate | Claude - OpenAI | +0.0 pts | +0.0 to +0.0 | 1.000 |
| D | leak_rate | DeepSeek - OpenAI | +0.0 pts | +0.0 to +0.0 | 1.000 |
| D | partial_leak_rate | Claude - DeepSeek | +0.0 pts | +0.0 to +0.0 | 1.000 |
| D | partial_leak_rate | Claude - OpenAI | +0.0 pts | +0.0 to +0.0 | 1.000 |
| D | partial_leak_rate | DeepSeek - OpenAI | +0.0 pts | +0.0 to +0.0 | 1.000 |

## Cost and errors

| suite   | model_label   |   calls |   errors |   median_latency_s |   prompt_tokens |   completion_tokens |
|:--------|:--------------|--------:|---------:|-------------------:|----------------:|--------------------:|
| D       | Claude        |       5 |        0 |               0.01 |              50 |                  50 |
| D       | DeepSeek      |       5 |        0 |               0.01 |              50 |                  50 |
| D       | OpenAI        |       5 |        0 |               0.01 |              50 |                  50 |
