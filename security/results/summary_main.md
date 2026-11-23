# security-bench results (main)

Generated 2026-11-21. 95% CIs from a cluster bootstrap over items (runs kept together). Flip rate = share of items whose outcome changed between runs.

Models as reported by the API: GPT-5.6: agentrouter/gpt-5.6-sol via opencode

## Suite A

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| gateway_block_rate | GPT-5.6 | 23.5% | 9.8% - 39.5% | 27 x 3 | 8.0% | 0 |
| compliance_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 22 x 3 | 0.0% | 0 |
| strongreject_score | GPT-5.6 | 0.000 | 0.000-0.000 | 22 x 3 | 0.0% | 0 |

## Suite C

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| gateway_block_rate | GPT-5.6 | 8.2% | 3.1% - 14.3% | 98 x 3 | 0.0% | 0 |
| overrefusal_rate | GPT-5.6 | 0.9% | 0.0% - 2.4% | 90 x 3 | 1.2% | 0 |
| overrefusal_rate[keyword] | GPT-5.6 | 0.0% | 0.0% - 0.0% | 90 x 3 | 0.0% | 0 |

## Suite D

| Metric | Model | Estimate | 95% CI | Items x runs | Flip rate | Judge failures |
|---|---|---|---|---|---|---|
| gateway_block_rate | GPT-5.6 | 4.0% | 1.0% - 8.0% | 100 x 3 | 0.0% | 0 |
| leak_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 96 x 3 | 0.0% | 0 |
| partial_leak_rate | GPT-5.6 | 0.0% | 0.0% - 0.0% | 96 x 3 | 0.0% | 0 |

## Cost and errors

Token counts are blank when the client (opencode) does not report them; use the AgentRouter dashboard for spend.

| suite   | model_label   |   calls |   errors |   median_latency_s |   prompt_tokens |   completion_tokens |
|:--------|:--------------|--------:|---------:|-------------------:|----------------:|--------------------:|
| A       | GPT-5.6       |      90 |       13 |            11.83   |             nan |                 nan |
| C       | GPT-5.6       |     300 |       16 |             8.8375 |             nan |                 nan |
| D       | GPT-5.6       |     300 |        0 |             7.6045 |             nan |                 nan |
