# audio-bench results (main)

Generated 2026-11-24. ASR: faster-whisper large-v3, Whisper English normalizer. 95% CIs: cluster bootstrap over items, runs kept together.

| Model | Suite | Metric | Estimate | 95% CI | Items x runs |
|---|---|---|---|---|---|
| flash-v2.5 | ALL | credits_used | 6,569 |  | 83 x 3 |
| multi-v2 | ALL | credits_used | 13,138 |  | 83 x 3 |
| v3 | ALL | credits_used | 13,249 |  | 83 x 3 |
| v4 | ALL | credits_used | 13,249 |  | 83 x 3 |
| v4-turbo | ALL | credits_used | 6,624 |  | 83 x 3 |
| flash-v2.5 | S2 | s2_pass | 16.0% | 4.0% - 32.0% | 25 x 3 |
| multi-v2 | S2 | s2_pass | 20.0% | 4.0% - 36.0% | 25 x 3 |
| v3 | S2 | s2_pass | 57.3% | 40.0% - 74.7% | 25 x 3 |
| v4 | S2 | s2_pass | 68.0% | 49.3% - 85.3% | 25 x 3 |
| v4-turbo | S2 | s2_pass | 72.0% | 54.7% - 88.0% | 25 x 3 |
| flash-v2.5 | ALL | sec_per_char | 0.067 | 0.063 - 0.072 | 83 x 3 |
| multi-v2 | ALL | sec_per_char | 0.069 | 0.065 - 0.074 | 83 x 3 |
| v3 | ALL | sec_per_char | 0.072 | 0.066 - 0.079 | 83 x 3 |
| v4 | ALL | sec_per_char | 0.081 | 0.075 - 0.088 | 83 x 3 |
| v4-turbo | ALL | sec_per_char | 0.081 | 0.075 - 0.088 | 83 x 3 |
| flash-v2.5 | ALL | ttfa_s | 0.540 | 0.515 - 0.565 | 83 x 3 |
| multi-v2 | ALL | ttfa_s | 0.916 | 0.865 - 0.964 | 83 x 3 |
| v3 | ALL | ttfa_s | 0.857 | 0.817 - 0.895 | 83 x 3 |
| v4 | ALL | ttfa_s | 1.255 | 1.188 - 1.325 | 83 x 3 |
| v4-turbo | ALL | ttfa_s | 0.696 | 0.645 - 0.746 | 83 x 3 |
| flash-v2.5 | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| multi-v2 | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| v3 | S1 | wer | 0.6% | 0.0% - 1.8% | 30 x 3 |
| v4 | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| v4-turbo | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| flash-v2.5 | S3 | wer | 0.0% | 0.0% - 0.0% | 15 x 3 |
| multi-v2 | S3 | wer | 1.5% | 0.0% - 4.4% | 15 x 3 |
| v3 | S3 | wer | 0.0% | 0.0% - 0.0% | 15 x 3 |
| v4 | S3 | wer | 0.4% | 0.0% - 1.1% | 15 x 3 |
| v4-turbo | S3 | wer | 2.1% | 0.0% - 5.2% | 15 x 3 |
| flash-v2.5 | S4 | wer | 0.0% | 0.0% - 0.0% | 12 x 1 |
| multi-v2 | S4 | wer | 0.0% | 0.0% - 0.0% | 12 x 1 |
| v3 | S4 | wer | 0.0% | 0.0% - 0.0% | 12 x 1 |
| v4 | S4 | wer | 0.0% | 0.0% - 0.0% | 12 x 1 |
| v4-turbo | S4 | wer | 0.0% | 0.0% - 0.0% | 12 x 1 |
| flash-v2.5 | S5 | wer | 0.0% |  | 1 x 1 |
| multi-v2 | S5 | wer | 0.6% |  | 1 x 1 |
| v3 | S5 | wer | 0.0% |  | 1 x 1 |
| v4 | S5 | wer | 1.3% |  | 1 x 1 |
| v4-turbo | S5 | wer | 1.6% |  | 1 x 1 |
| flash-v2.5 | S5 | worst_chunk_wer | 0.0% |  | 1 x 1 |
| multi-v2 | S5 | worst_chunk_wer | 7.4% |  | 1 x 1 |
| v3 | S5 | worst_chunk_wer | 0.0% |  | 1 x 1 |
| v4 | S5 | worst_chunk_wer | 7.4% |  | 1 x 1 |
| v4-turbo | S5 | worst_chunk_wer | 7.4% |  | 1 x 1 |

## Pairwise S1 WER differences (paired bootstrap, Holm)

| A - B | Diff | 95% CI | p (Holm) |
|---|---|---|---|
| flash-v2.5 - multi-v2 | +0.00 pts | +0.00 to +0.00 | 1.000 |
| flash-v2.5 - v3 | -0.62 pts | -1.81 to +0.00 | 1.000 |
| flash-v2.5 - v4 | +0.00 pts | +0.00 to +0.00 | 1.000 |
| flash-v2.5 - v4-turbo | +0.00 pts | +0.00 to +0.00 | 1.000 |
| multi-v2 - v3 | -0.62 pts | -1.81 to +0.00 | 1.000 |
| multi-v2 - v4 | +0.00 pts | +0.00 to +0.00 | 1.000 |
| multi-v2 - v4-turbo | +0.00 pts | +0.00 to +0.00 | 1.000 |
| v3 - v4 | +0.62 pts | +0.00 to +1.81 | 1.000 |
| v3 - v4-turbo | +0.62 pts | +0.00 to +1.81 | 1.000 |
| v4 - v4-turbo | +0.00 pts | +0.00 to +0.00 | 1.000 |

## S2 failures to listen to (manual check)

| Model | Item | Run | Transcript |
|---|---|---|---|
| flash-v2.5 | S2-00 | 0 | The startup raised 3.5 MEMS last year. |
| flash-v2.5 | S2-00 | 1 | The startup raised 3.5 MEMS last year. |
| flash-v2.5 | S2-00 | 2 | The startup raised 3.5 NEMs last year. |
| multi-v2 | S2-00 | 0 | The start-up raised 3.5 MAMINAS last year. |
| multi-v2 | S2-00 | 1 | The start-up raised 3.5 mammines last year. |
| multi-v2 | S2-00 | 2 | The start-up raised 3.5 mammas last year. |
| flash-v2.5 | S2-01 | 0 | Dr. Smith lives on Smith Doctor. |
| flash-v2.5 | S2-01 | 1 | Dr. Smith lives on Smith Doctor. |
| flash-v2.5 | S2-01 | 2 | Dr. Smith lives on Smith Doctor. |
| multi-v2 | S2-01 | 0 | Dr. Smith lives on Smith Doctor. |
| multi-v2 | S2-01 | 1 | Dr. Smith lives on Smith Doctor. |
| multi-v2 | S2-01 | 2 | Dr. Smith lives on Smith Doctor. |
| v3 | S2-01 | 0 | Dr. Smith lives on Smith Dried. |
| v3 | S2-01 | 1 | Dr. Smith lives on Smith Droid. |
| v3 | S2-01 | 2 | Dr. Smith lives on Smith Droid. |
| flash-v2.5 | S2-02 | 0 | The meeting is on 18-11-2026. |
| flash-v2.5 | S2-02 | 1 | The meeting is on 18-11-2026. |
| flash-v2.5 | S2-02 | 2 | The meeting is on 18-11-2026. |
| multi-v2 | S2-02 | 0 | The meeting is on 18-11-2026. |
| multi-v2 | S2-02 | 1 | The meeting is on 18-11-2026. |
| multi-v2 | S2-02 | 2 | The meeting is on 18-11-2026. |
| v3 | S2-02 | 0 | The meeting is on 18-11-2026. |
| v3 | S2-02 | 1 | The meeting is on 18th 11th 2026. |
| v3 | S2-02 | 2 | The meeting is on 18-11-2026. |
| flash-v2.5 | S2-03 | 0 | Call me at 465-555-0192. |
| flash-v2.5 | S2-03 | 1 | Call me at 465-555-0192. |
| flash-v2.5 | S2-03 | 2 | Call me at 465-555-0192. |
| multi-v2 | S2-03 | 0 | Call me at 465-550-192. |
| multi-v2 | S2-03 | 1 | call me at four six five five five zero one nine two |
| multi-v2 | S2-03 | 2 | Call me at 465-550-192. |
| v3 | S2-03 | 0 | call me at 416-555-0192. |
| v3 | S2-03 | 1 | Call me at 416-555-0192. |
| v3 | S2-03 | 2 | call me at 416-555-0192. |
| v4 | S2-03 | 0 | Call me at 416-555-0192. |
| v4 | S2-03 | 1 | Call me at 416-555-0192. |
| v4 | S2-03 | 2 | Call me at 416-555-0192. |
| v4-turbo | S2-03 | 0 | Call me at 416-555-0192. |
| v4-turbo | S2-03 | 1 | Call me at 416-555-0192. |
| v4-turbo | S2-03 | 2 | Call me at 416-555-0192. |
| flash-v2.5 | S2-04 | 0 | The temperature dropped to 12°C overnight. |
| flash-v2.5 | S2-04 | 1 | The temperature dropped to 12°C overnight. |
| flash-v2.5 | S2-04 | 2 | The temperature dropped to 12°C overnight. |
| multi-v2 | S2-04 | 0 | The temperature dropped to 12°C overnight. |
| multi-v2 | S2-04 | 1 | The temperature dropped to 12°C overnight. |
| multi-v2 | S2-04 | 2 | The temperature dropped to 12°C overnight. |
| flash-v2.5 | S2-05 | 0 | Chapter 14 begins on p. 212. |
| flash-v2.5 | S2-05 | 1 | Chapter 14 begins on p. 212. |
| flash-v2.5 | S2-05 | 2 | Chapter 14 begins on p. 212. |
| multi-v2 | S2-05 | 0 | Chapter 14 begins on p212. |
| multi-v2 | S2-05 | 1 | Chapter 14 begins on P212. |
| multi-v2 | S2-05 | 2 | Chapter 14 begins on P212. |
| flash-v2.5 | S2-06 | 0 | The flight leaves at 7.45am. |
| flash-v2.5 | S2-06 | 1 | The flight leaves at 7.45am. |
| flash-v2.5 | S2-06 | 2 | The flight leaves at 7.45am. |
| multi-v2 | S2-06 | 0 | The flight leaves at 7.45 a.m. |
| multi-v2 | S2-06 | 1 | The flight leaves at 7.45 a.m. |
| multi-v2 | S2-06 | 2 | The flight leaves at 7.45 a.m. |
| v3 | S2-06 | 0 | The flight leaves at 7.45 a.m. |
| v3 | S2-06 | 1 | The flight leaves at 7.45 a.m. |
| v3 | S2-06 | 2 | The flight leaves at 7.45 a.m. |