# ListenBench results

Generated 2026-11-23. Every clip was built by us, so the ground truth is exact. Each cell: estimate (95% CI). CIs: cluster bootstrap over source items (a sentence's four noise conditions and its repeated runs stay together).

| Metric | scribe-v2 | scribe-v3 | whisper-v3 | whisper-v3-vad |
|---|---|---|---|---|
| WER, clean speech [L1] | 1.0% (0.1%-2.6%) | 0.2% (0.0%-0.7%) | 0.6% (0.0%-1.7%) | 0.0% (0.0%-0.0%) |
| WER, cafe noise 10 dB SNR [L1] | 0.2% (0.0%-0.6%) | 0.2% (0.0%-0.7%) | 0.6% (0.0%-1.7%) | 0.0% (0.0%-0.0%) |
| WER, cafe noise 0 dB SNR [L1] | 0.4% (0.0%-1.1%) | 0.2% (0.0%-0.7%) | 1.0% (0.0%-2.4%) | 0.2% (0.0%-0.6%) |
| WER, street noise 0 dB SNR [L1] | 0.0% (0.0%-0.0%) | 0.2% (0.0%-0.7%) | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) |
| No-speech clips with invented words (lower is better) [L3] | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) | 100.0% (100.0%-100.0%) | 8.3% (0.0%-25.0%) |
| Invented words per no-speech clip [L3] | 0.00 (0.00-0.00) | 0.00 (0.00-0.00) | 2.42 (1.92-2.92) | 0.75 (0.00-2.25) |
| Speech clips with words invented in the silence/noise around speech [L1] | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) |
| Speech onset within tolerance [L1] | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | 47.5% (31.7%-63.3%) | 98.3% (95.8%-100.0%) |
| Speech onset error, seconds [L1] | 0.07 (0.06-0.08) | 0.07 (0.07-0.08) | 0.55 (0.48-0.62) | 0.34 (0.32-0.36) |
| Speech end error, seconds [L1] | 0.09 (0.08-0.10) | 0.08 (0.07-0.09) | 0.37 (0.35-0.40) | 0.38 (0.36-0.41) |
| Sound event tagged correctly, near the right time [L4] | 75.0% (50.0%-100.0%) | 100.0% (100.0%-100.0%) | n/a | n/a |
| Sound event tagged correctly (event-only clips) [L3] | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | n/a | n/a |
| Sound event timing error, seconds [L4] | 0.56 (0.30-0.77) | 0.54 (0.32-0.75) | n/a | n/a |
| Words invented on the sound event or in silence [L4] | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) | 33.3% (8.3%-58.3%) | 8.3% (0.0%-25.0%) |
| Clean speech clips with a sound event that was not there [L1] | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) | n/a | n/a |
| WER, speech with a sound event [L4] | 0.0% (0.0%-0.0%) | 0.6% (0.0%-1.8%) | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) |
| WER, two-speaker dialogue [L5] | 0.0% (0.0%-0.0%) | 1.4% (0.0%-3.1%) | 0.0% (0.0%-0.0%) | 0.5% (0.0%-1.5%) |
| Dialogues where exactly 2 speakers were found [L5] | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | n/a | n/a |
| Words attributed to the right speaker [L5] | 100.0% (100.0%-100.0%) | 100.0% (100.0%-100.0%) | n/a | n/a |
| WER increase, cafe_10db minus clean (paired) [L1] | -0.8% (-2.4%-0.3%) | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) | 0.0% (0.0%-0.0%) |
| WER increase, cafe_0db minus clean (paired) [L1] | -0.7% (-2.3%-0.7%) | 0.0% (0.0%-0.0%) | 0.4% (0.0%-1.1%) | 0.2% (0.0%-0.6%) |
| WER increase, street_0db minus clean (paired) [L1] | -1.0% (-2.6%--0.1%) | 0.0% (0.0%-0.0%) | -0.6% (-1.7%-0.0%) | 0.0% (0.0%-0.0%) |
| Clips transcribed identically in every run [ALL] | 87.5% | 98.7% | n/a | n/a |

n/a: the system does not produce that output (Whisper has no speaker labels or sound-event tags).
Tolerances: onset 0.5 s, event window 1.5 s, words more than 0.5 s outside the speech count as invented.

## Paired comparisons (same clips; paired bootstrap; Holm-adjusted)

| Comparison | A - B | Diff | 95% CI | p (Holm) |
|---|---|---|---|---|
| WER (all L1 conditions) | scribe-v2 - scribe-v3 | 0.2% | -0.5% to 0.7% | 1.000 |
| WER (all L1 conditions) | scribe-v2 - whisper-v3 | -0.1% | -1.2% to 0.6% | 1.000 |
| WER (all L1 conditions) | scribe-v2 - whisper-v3-vad | 0.3% | 0.0% to 0.8% | 0.602 |
| WER (all L1 conditions) | scribe-v3 - whisper-v3 | -0.3% | -1.4% to 0.6% | 1.000 |
| WER (all L1 conditions) | scribe-v3 - whisper-v3-vad | 0.2% | -0.2% to 0.7% | 1.000 |
| WER (all L1 conditions) | whisper-v3 - whisper-v3-vad | 0.5% | -0.1% to 1.4% | 1.000 |
| No-speech hallucination | scribe-v2 - scribe-v3 | 0.0% | 0.0% to 0.0% | 1.000 |
| No-speech hallucination | scribe-v2 - whisper-v3 | -100.0% | -100.0% to -100.0% | 0.000 |
| No-speech hallucination | scribe-v2 - whisper-v3-vad | -8.3% | -25.0% to 0.0% | 1.000 |
| No-speech hallucination | scribe-v3 - whisper-v3 | -100.0% | -100.0% to -100.0% | 0.000 |
| No-speech hallucination | scribe-v3 - whisper-v3-vad | -8.3% | -25.0% to 0.0% | 1.000 |
| No-speech hallucination | whisper-v3 - whisper-v3-vad | 91.7% | 75.0% to 100.0% | 0.000 |
| Onset error (s) | scribe-v2 - scribe-v3 | -0.00 | -0.00 to 0.00 | 1.000 |
| Onset error (s) | scribe-v2 - whisper-v3 | -0.48 | -0.56 to -0.41 | 0.000 |
| Onset error (s) | scribe-v2 - whisper-v3-vad | -0.26 | -0.29 to -0.24 | 0.000 |
| Onset error (s) | scribe-v3 - whisper-v3 | -0.47 | -0.56 to -0.41 | 0.000 |
| Onset error (s) | scribe-v3 - whisper-v3-vad | -0.26 | -0.29 to -0.24 | 0.000 |
| Onset error (s) | whisper-v3 - whisper-v3-vad | 0.21 | 0.15 to 0.29 | 0.000 |
| Invented words around speech | scribe-v2 - scribe-v3 | 0.0% | 0.0% to 0.0% | 1.000 |
| Invented words around speech | scribe-v2 - whisper-v3 | 0.0% | 0.0% to 0.0% | 1.000 |
| Invented words around speech | scribe-v2 - whisper-v3-vad | 0.0% | 0.0% to 0.0% | 1.000 |
| Invented words around speech | scribe-v3 - whisper-v3 | 0.0% | 0.0% to 0.0% | 1.000 |
| Invented words around speech | scribe-v3 - whisper-v3-vad | 0.0% | 0.0% to 0.0% | 1.000 |
| Invented words around speech | whisper-v3 - whisper-v3-vad | 0.0% | 0.0% to 0.0% | 1.000 |

## What was invented on clips with no speech (check by listening)

| System | Clip | Run | Output |
|---|---|---|---|
| whisper-v3 | L3-applause_only | 0 | Thank you. |
| whisper-v3 | L3-cafe_10s | 0 | Thank you. |
| whisper-v3 | L3-dog_only | 0 | Go! |
| whisper-v3 | L3-glass_only | 0 | Thank you for watching. |
| whisper-v3 | L3-hum_10s | 0 | Thanks for watching! |
| whisper-v3 | L3-knock_only | 0 | Thank you for watching. |
| whisper-v3 | L3-laugh_only | 0 | Thank you. |
| whisper-v3 | L3-phone_only | 0 | Thanks for watching! |
| whisper-v3 | L3-silence_15s | 0 | Thank you. |
| whisper-v3 | L3-silence_5s | 0 | Thank you. |
| whisper-v3 | L3-street_10s | 0 | Thank you. |
| whisper-v3 | L3-white_10s | 0 | Thank you. |
| whisper-v3-vad | L3-laugh_only | 0 | Ha, ha, ha, ha, ha, ha, ha, ha, ha. |