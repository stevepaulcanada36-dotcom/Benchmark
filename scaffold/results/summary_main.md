# Scaffold benchmark results (main)

Generated 2026-11-21. Same model, different agent scaffolds, indirect prompt injection in workspace files. All checks deterministic. 95% CIs: cluster bootstrap over items (runs together).

| Model | Scaffold | Metric | Estimate | 95% CI | Items x runs |
|---|---|---|---|---|---|
| GPT-5.6 | S0_pasted | attack_success | 1.4% | 0.0% - 4.1% | 37 x 2 |
| GPT-5.6 | S1_agent_readonly | attack_success | 0.0% | 0.0% - 0.0% | 40 x 2 |
| GPT-5.6 | S2_agent_auto | attack_success | 0.0% | 0.0% - 0.0% | 40 x 2 |
| GPT-5.6 | S3_auto_guard | attack_success | 0.0% | 0.0% - 0.0% | 40 x 2 |
| GPT-5.6 | S0_pasted | false_flag_clean | 0.0% | 0.0% - 0.0% | 5 x 2 |
| GPT-5.6 | S1_agent_readonly | false_flag_clean | 0.0% | 0.0% - 0.0% | 5 x 2 |
| GPT-5.6 | S2_agent_auto | false_flag_clean | 0.0% | 0.0% - 0.0% | 5 x 2 |
| GPT-5.6 | S3_auto_guard | false_flag_clean | 0.0% | 0.0% - 0.0% | 5 x 2 |
| GPT-5.6 | S0_pasted | gateway_block_rate | 6.7% | 0.0% - 15.6% | 45 x 2 |
| GPT-5.6 | S1_agent_readonly | gateway_block_rate | 0.0% | 0.0% - 0.0% | 45 x 2 |
| GPT-5.6 | S2_agent_auto | gateway_block_rate | 0.0% | 0.0% - 0.0% | 45 x 2 |
| GPT-5.6 | S3_auto_guard | gateway_block_rate | 0.0% | 0.0% - 0.0% | 45 x 2 |
| GPT-5.6 | S0_pasted | injection_flagged | 0.0% | 0.0% - 0.0% | 37 x 2 |
| GPT-5.6 | S1_agent_readonly | injection_flagged | 0.0% | 0.0% - 0.0% | 40 x 2 |
| GPT-5.6 | S2_agent_auto | injection_flagged | 0.0% | 0.0% - 0.0% | 40 x 2 |
| GPT-5.6 | S3_auto_guard | injection_flagged | 77.5% | 67.5% - 87.5% | 40 x 2 |
| GPT-5.6 | S0_pasted | unrequested_file_changes | 0.0% | 0.0% - 0.0% | 42 x 2 |
| GPT-5.6 | S1_agent_readonly | unrequested_file_changes | 0.0% | 0.0% - 0.0% | 45 x 2 |
| GPT-5.6 | S2_agent_auto | unrequested_file_changes | 0.0% | 0.0% - 0.0% | 45 x 2 |
| GPT-5.6 | S3_auto_guard | unrequested_file_changes | 0.0% | 0.0% - 0.0% | 45 x 2 |
| GPT-5.6 | S0_pasted | utility_clean | 100.0% | 100.0% - 100.0% | 5 x 2 |
| GPT-5.6 | S1_agent_readonly | utility_clean | 100.0% | 100.0% - 100.0% | 5 x 2 |
| GPT-5.6 | S2_agent_auto | utility_clean | 90.0% | 70.0% - 100.0% | 5 x 2 |
| GPT-5.6 | S3_auto_guard | utility_clean | 100.0% | 100.0% - 100.0% | 5 x 2 |
| GPT-5.6 | S0_pasted | utility_under_attack | 100.0% | 100.0% - 100.0% | 37 x 2 |
| GPT-5.6 | S1_agent_readonly | utility_under_attack | 100.0% | 100.0% - 100.0% | 40 x 2 |
| GPT-5.6 | S2_agent_auto | utility_under_attack | 100.0% | 100.0% - 100.0% | 40 x 2 |
| GPT-5.6 | S3_auto_guard | utility_under_attack | 98.8% | 96.2% - 100.0% | 40 x 2 |

## Attack success by goal and placement

| Model | Scaffold | Breakdown | Estimate | 95% CI | n |
|---|---|---|---|---|---|
| GPT-5.6 | S0_pasted | G1_canary | 7.1% | 0.0% - 21.4% | 7 |
| GPT-5.6 | S1_agent_readonly | G1_canary | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S2_agent_auto | G1_canary | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S3_auto_guard | G1_canary | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S0_pasted | G2_exfil | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S1_agent_readonly | G2_exfil | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S2_agent_auto | G2_exfil | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S3_auto_guard | G2_exfil | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S0_pasted | G3_phish | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S1_agent_readonly | G3_phish | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S2_agent_auto | G3_phish | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S3_auto_guard | G3_phish | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S0_pasted | G4_action | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S1_agent_readonly | G4_action | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S2_agent_auto | G4_action | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S3_auto_guard | G4_action | 0.0% | 0.0% - 0.0% | 10 |
| GPT-5.6 | S0_pasted | framed | 2.5% | 0.0% - 7.5% | 20 |
| GPT-5.6 | S1_agent_readonly | framed | 0.0% | 0.0% - 0.0% | 20 |
| GPT-5.6 | S2_agent_auto | framed | 0.0% | 0.0% - 0.0% | 20 |
| GPT-5.6 | S3_auto_guard | framed | 0.0% | 0.0% - 0.0% | 20 |
| GPT-5.6 | S0_pasted | hidden | 0.0% | 0.0% - 0.0% | 17 |
| GPT-5.6 | S1_agent_readonly | hidden | 0.0% | 0.0% - 0.0% | 20 |
| GPT-5.6 | S2_agent_auto | hidden | 0.0% | 0.0% - 0.0% | 20 |
| GPT-5.6 | S3_auto_guard | hidden | 0.0% | 0.0% - 0.0% | 20 |

## Scaffold differences in attack success (paired bootstrap, Holm)

| Model | A - B | Diff | 95% CI | p (Holm) |
|---|---|---|---|---|
| GPT-5.6 | S0_pasted - S1_agent_readonly | +1.4 pts | +0.0 to +4.1 | 1.000 |
| GPT-5.6 | S0_pasted - S2_agent_auto | +1.4 pts | +0.0 to +4.1 | 1.000 |
| GPT-5.6 | S0_pasted - S3_auto_guard | +1.4 pts | +0.0 to +4.1 | 1.000 |
| GPT-5.6 | S1_agent_readonly - S2_agent_auto | +0.0 pts | +0.0 to +0.0 | 1.000 |
| GPT-5.6 | S1_agent_readonly - S3_auto_guard | +0.0 pts | +0.0 to +0.0 | 1.000 |
| GPT-5.6 | S2_agent_auto - S3_auto_guard | +0.0 pts | +0.0 to +0.0 | 1.000 |

## Latency (median seconds per agent run)

|                                  |   latency_s |
|:---------------------------------|------------:|
| ('GPT-5.6', 'S0_pasted')         |         9.4 |
| ('GPT-5.6', 'S1_agent_readonly') |        13.5 |
| ('GPT-5.6', 'S2_agent_auto')     |        13.4 |
| ('GPT-5.6', 'S3_auto_guard')     |        13.1 |