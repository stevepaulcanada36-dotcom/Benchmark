# audio-bench results (main)

Generated 2026-11-21. ASR: faster-whisper large-v3, Whisper English normalizer. 95% CIs: cluster bootstrap over items, runs kept together.

| Model | Suite | Metric | Estimate | 95% CI | Items x runs |
|---|---|---|---|---|---|
| flash-v2.5 | ALL | credits_used | 4,618 |  | 55 x 3 |
| multi-v2 | ALL | credits_used | 9,237 |  | 55 x 3 |
| v3 | ALL | credits_used | 9,237 |  | 55 x 3 |
| v4 | ALL | credits_used | 9,237 |  | 55 x 3 |
| v4-turbo | ALL | credits_used | 4,618 |  | 55 x 3 |
| flash-v2.5 | S2 | s2_pass | 16.0% | 4.0% - 32.0% | 25 x 3 |
| multi-v2 | S2 | s2_pass | 20.0% | 4.0% - 36.0% | 25 x 3 |
| v3 | S2 | s2_pass | 57.3% | 40.0% - 74.7% | 25 x 3 |
| v4 | S2 | s2_pass | 68.0% | 49.3% - 85.3% | 25 x 3 |
| v4-turbo | S2 | s2_pass | 72.0% | 54.7% - 88.0% | 25 x 3 |
| flash-v2.5 | ALL | sec_per_char | 0.072 | 0.066 - 0.078 | 55 x 3 |
| multi-v2 | ALL | sec_per_char | 0.074 | 0.068 - 0.080 | 55 x 3 |
| v3 | ALL | sec_per_char | 0.080 | 0.072 - 0.089 | 55 x 3 |
| v4 | ALL | sec_per_char | 0.088 | 0.080 - 0.098 | 55 x 3 |
| v4-turbo | ALL | sec_per_char | 0.088 | 0.080 - 0.098 | 55 x 3 |
| flash-v2.5 | ALL | ttfa_s | 0.600 | 0.578 - 0.625 | 55 x 3 |
| multi-v2 | ALL | ttfa_s | 1.038 | 1.000 - 1.077 | 55 x 3 |
| v3 | ALL | ttfa_s | 0.959 | 0.929 - 0.991 | 55 x 3 |
| v4 | ALL | ttfa_s | 1.423 | 1.360 - 1.489 | 55 x 3 |
| v4-turbo | ALL | ttfa_s | 0.828 | 0.786 - 0.874 | 55 x 3 |
| flash-v2.5 | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| multi-v2 | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| v3 | S1 | wer | 0.6% | 0.0% - 1.8% | 30 x 3 |
| v4 | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |
| v4-turbo | S1 | wer | 0.0% | 0.0% - 0.0% | 30 x 3 |

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