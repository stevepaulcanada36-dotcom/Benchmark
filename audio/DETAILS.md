# audio-bench

Text-to-speech benchmark for five ElevenLabs models, with automatic metrics, a blinded listening test,
and 95% CIs everywhere. Built for STA2453H.

| Suite | Items | What it tests | Automatic check | Manual check |
|---|---|---|---|---|
| S1 Read-aloud | 30 sentences | Intelligibility | Whisper transcript, then WER | MOS in the listening test |
| S2 Normalization | 25 | "$3.5M", "Dr. Smith ... Smith Dr.", dates, phone numbers, units, course codes | Pass if the transcript matches an accepted spoken form | Listen to the failures listed in the report |
| S3 Homographs and names | 15 | "read" (past/present), "lead", "Anantharaj", "Mississauga" | WER only (ASR can't hear stress) | Listeners answer "pronounced as X?" yes/no |
| S4 Expressive | 12 | `[whispers]`, `[laughs]`, `[angry]`... (tags dropped for models without tag support) | WER | A/B preference, then Bradley-Terry Elo |
| S5 Long-form | 1 x ~2,000 chars | Drift, skipped or repeated text | WER and WER per 200-character chunk | Listen to the worst chunk |
| All | | Quality, voice consistency, speed | UTMOS, ECAPA speaker similarity, time to first audio, seconds per character, credits | |

All text was written for this benchmark, so there are no copyright issues and nothing has been seen in training.
Transcription runs locally with Whisper. It costs no credits and is independent of ElevenLabs, so no vendor
grades its own audio.

## Credits

The default full run needs about **52,800 credits** (S1-S3 x 3 runs, S4-S5 x 1, five models). The pilot needs about
**1,050**. `max_credits: 110000` in `config.yaml` is a hard stop across everything this benchmark spends.
A `ledger.jsonl` tracks the spending, and the account balance is checked before each run.

`credits_per_char` assumes 1.0 for v4/v3/Multilingual v2 and 0.5 for v4 Turbo and Flash. **Check these against
your plan.** After each run the tool prints how much your account usage actually moved, so a wrong rate shows up
immediately. Each extra run of S1-S3 for all five models costs about 14,300 credits, so `runs: {S1: 5, S2: 5, S3: 5}`
fits your budget and narrows the CIs.

## Setup (once)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
pip install -r ../requirements-extra.txt   # optional: UTMOS + speaker similarity (PyTorch, ~2 GB)
cp ../.env.example ../.env                    # put your ElevenLabs key in it
python -m audiobench list-voices        # optional: choose voice_id for config.yaml
```

You also need `ffmpeg` installed so MP3 files can be decoded (`brew install ffmpeg` / `sudo apt install ffmpeg`
/ `winget install ffmpeg`). The first `score` downloads the Whisper model, about 3 GB for large-v3.
On a laptop without a GPU, try `--asr-model small` for the pilot. Use large-v3 for the final numbers and report which.

## Run order

```bash
python -m audiobench estimate --pilot       # ~1,050 credits, nothing spent
python -m audiobench run --pilot            # asks before spending
python -m audiobench score --pilot --asr-model small
python -m audiobench report --pilot         # results/summary_pilot.md
#   listen to a few clips in audio/pilot/ and read the transcripts in audio/pilot/metrics.jsonl first

python -m audiobench estimate               # ~52,800 credits
python -m audiobench run                    # resumes safely; never regenerates an existing clip
python -m audiobench score                  # large-v3
python -m audiobench report                 # results/summary_main.md, plot_main.png

python -m audiobench listening-test         # listening_test/ folder: zip it and send it to 3+ listeners
#   each listener opens index.html, rates 60 clips + 40 A/B pairs (~25 min), downloads a CSV
#   put the CSVs in listening_results/
python -m audiobench listening-analyze      # MOS with CIs, pronunciation accuracy, Elo with CIs
```

`--models v3 flash-v2.5` and `--suites S1 S2` restrict a command. `-y` skips the confirmation prompt.

## What gets reported

- WER per suite, S2 pass rate, UTMOS, speaker similarity, speaking rate and time to first audio. Each has a 95%
  CI from a cluster bootstrap over items (runs kept together).
- Pairwise S1 WER differences between models: paired bootstrap, Holm-adjusted.
- S2 failures with their transcripts, so you can listen and confirm. Some will be ASR errors rather than TTS errors.
- Listening test: MOS with CIs, listener agreement (Spearman), S3 pronunciation accuracy with Wilson CIs,
  and A/B Bradley-Terry scores on an Elo scale with bootstrap CIs.
- Credits used per model.

## Known limits (write these up)

- Whisper's errors count as TTS errors. The S2 failure list and the listening test exist to catch this.
- S5 has one passage, so there is no between-item CI. Treat it as a stability check, not a ranking.
- The `seed` makes generation repeatable on a best-effort basis only. The run-to-run spread is measured anyway.
- One voice. Results may not hold for other voices.

## Testing without spending

```bash
AUDIOBENCH_FAKE=1 python -m audiobench run --pilot -y   # tones instead of speech, fake transcripts
pytest -q
```
