# security-bench results (pilot)

Generated 2026-11-21. 95% CIs from a cluster bootstrap over items (runs kept together). Flip rate = share of items whose outcome changed between runs.

Models as reported by the API: GPT-5.6: agentrouter/gpt-5.6-sol via opencode

## Suite A

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| compliance_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 3 x 1 |  | 0 |
| strongreject_score | GPT-5.6 | 0.000 | 0.000-0.000 | 3 x 1 |  | 0 |

## Suite C

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| gateway_block_rate | GPT-5.6 | 20.0% | 0.0% - 60.0% | 5 x 1 |  | 0 |
| overrefusal_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 4 x 1 |  | 0 |
| overrefusal_rate[keyword] | GPT-5.6 | 0.0% | 0.0% - 0.0% | 4 x 1 |  | 0 |

## Suite D

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| leak_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |
| partial_leak_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 5 x 1 |  | 0 |

## Cost and errors

Token counts are blank when the client (opencode) does not report them; use the AgentRouter dashboard for spend.

| suite   | model_label   |   calls |   errors |   median_latency_s |   prompt_tokens |   completion_tokens |
|:--------|:--------------|--------:|---------:|-------------------:|----------------:|--------------------:|
| A       | GPT-5.6       |       3 |        0 |              9.177 |             nan |                 nan |
| C       | GPT-5.6       |       5 |        0 |              7.051 |             nan |                 nan |
| D       | GPT-5.6       |       5 |        0 |              8.727 |             nan |                 nan |
