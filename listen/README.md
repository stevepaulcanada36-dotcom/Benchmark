# ListenBench (Benchmark 4): does a speech system report only what is in the audio?

A simplified, audio-only version of the AV-ReasonBench idea. **We build every clip ourselves**, so the ground truth
is exact to the sample: what was said, when speech starts and ends, which sound event happens and when, who speaks
each turn, and which clips contain no speech at all. Grading is deterministic. There is no LLM judge.

| Suite | Clips | Question | Metric |
|---|---|---|---|
| L1 Noise ablation | 30 sentences x 4 conditions (clean, cafe 10 dB, cafe 0 dB, street 0 dB) | How much does background noise hurt? | WER per condition; paired "noise penalty" vs clean |
| L2 Timing (on L1 clips) | same 120 | Are timestamps right? | Onset/end error in seconds; % within 0.5 s |
| L3 Hallucination | 12 clips with **no speech** (silence, hum, white noise, cafe, street, sound effects only) | Does it invent words? | % of clips with any word; words per clip; the invented text is listed |
| L1/L4 Insertions | all speech clips | Does it invent words in the silence or noise around speech, or on a sound event? | % of clips with invented words |
| L4 Sound events | 6 events (dog, glass, knock, applause, laugh, phone) x before/after a sentence | Is the event tagged with the right label at the right time? | Correct tag within 1.5 s; timing error; false events on clean speech |
| L5 Speakers | 8 two-voice dialogues, 4 turns each | Who said what? | Exactly 2 speakers found; % of words attributed to the right speaker; WER |

**Systems:** ElevenLabs Scribe v3 and Scribe v2 (2 runs each, to measure run-to-run stability) and local
Whisper large-v3 with and without its silence filter (VAD). Whisper is free and deterministic, so it runs once.
The VAD pair is an ablation: does a simple silence filter remove the hallucinations?

**Statistics:** as in the other benchmarks. The 95% CIs come from a cluster bootstrap over source items: a
sentence's four noise conditions and its repeated runs stay together. Systems are compared on the same clips with
a paired bootstrap, and the p-values are Holm-adjusted.

**Cost:** about 2,000 credits to build (the 30 sentences reuse the audio benchmark's S1 clips; only the dialogues
and 8 sound effects are new). Scribe is billed per minute of audio, and there are about 22.5 minutes per run. The
pilot measures the real credits per minute and tells you what to put in `config.yaml`. `max_credits: 30000` is a
hard stop.

## Run (from the repo root, venv active)

```powershell
cd listen
python -m listenbench build                  # asks first; then mixes 152 clips locally
python -m listenbench transcribe --pilot     # ~10% of clips; prints the real Scribe credits/minute
#   put that number in config.yaml as stt_credits_per_minute, then:
python -m listenbench estimate
python -m listenbench transcribe             # the rest; Whisper large-v3 on CPU takes roughly 30-60 min
python -m listenbench report                 # results/summary.md, metrics.csv, pairwise.csv, plot.png
```
`--systems scribe-v3 whisper-v3` restricts a command. Finished calls are never repeated. `pytest -q` tests the
graders and runs the whole pipeline in fake mode, in a temporary folder, without spending anything.

## Manual check

Listen to every clip listed under "What was invented on clips with no speech" in `results/summary.md`, and to a few
L4 clips. The sound effects are generated, so one might not sound like its label. If one doesn't, say so in the
write-up, or regenerate it (delete `assets/sfx/<name>.mp3` and run `build` again).

## Limitations

There is one synthetic voice per speaker, and the noise is mixed in, not recorded in real rooms. The test is
English only. Scribe is an ElevenLabs product, and the clean speech is ElevenLabs TTS, which may favour Scribe;
Whisper is the independent comparison. Sound-event labels are matched by keywords, so "(dog barking)" counts
for dog.
