## One-day execution mode (recommended for your deadline)

The full research design is larger than a one-day implementation. This repository currently implements the **audio** and **security suites A–D**; the **AgentDojo/scaffold factorial is not implemented yet** (it is explicitly listed under “Coming next”). Do not describe all three benchmarks as completed unless you add and run that third component.

For a defensible one-day submission, run a narrowed, clearly labelled comparison and report the scope as a limitation:

1. Install dependencies and verify the API keys/model IDs first.
2. Run audio S1 and S2 only for two models, with the configured repeats:
   ```bash
   cd audio
   python -m audiobench estimate --models v3 flash-v2.5 --suites S1 S2
   python -m audiobench run --models v3 flash-v2.5 --suites S1 S2
   python -m audiobench score
   python -m audiobench report
   cd ..
   ```
   Check the estimate against the actual ElevenLabs account rates before generating audio. Do not run the listening study unless listeners are available.
3. Run security suite D (closed-domain secret-leak checks) and suite A (direct harmful-request evaluation) for two models. Temporarily set `generation.runs: 1` in `security/config.yaml` to fit the deadline, and restore it after the run if needed:
   ```bash
   cd security
   python -m secbench download
   python -m secbench check-models --models Claude DeepSeek
   python -m secbench run --suite D --models Claude DeepSeek
   python -m secbench judge --suite D --models Claude DeepSeek
   python -m secbench run --suite A --models Claude DeepSeek
   python -m secbench judge --suite A --models Claude DeepSeek
   python -m secbench report
   cd ..
   ```
   Confirm that the model IDs in `security/config.yaml` are actually available before spending calls. Read provider terms before security testing.
4. Run tests and preserve the generated summaries, CSVs, prompts, and configuration used:
   ```bash
   cd security && pytest -q
   cd ../audio && pytest -q
   ```
5. In the write-up, state that this is a **time-constrained, reduced-scope evaluation**. Do not claim the unrun scaffold benchmark, human-validated judge performance, or listener-based audio preference results.

This route prioritizes completed, inspectable results over starting all suites and ending with incomplete outputs. If you have enough time after the core runs, add suite C (safe-prompt over-refusal) so security results do not rely on harmful-request refusal alone.

---

# LLM Benchmarks: Security (AgentRouter) and Audio (ElevenLabs)

STA2453H benchmark project. Two benchmarks share one repo:

| Folder | Benchmark | Models | Details |
|---|---|---|---|
| `security/` | Jailbreak, over-refusal and system-prompt leakage | Claude, OpenAI, DeepSeek via AgentRouter | [security/DETAILS.md](security/DETAILS.md) |
| `audio/` | Text-to-speech quality, normalization, expressiveness, stability | 5 ElevenLabs TTS models | [audio/DETAILS.md](audio/DETAILS.md) |

Both follow the course rules: exact prompts and code released, repeated runs, 95% confidence intervals on every
number, cost recorded, and automatic judges checked against human labels.

```
llm-benchmarks/
├── README.md               <- this file: step-by-step guide
├── requirements.txt        <- everything except the optional PyTorch extras
├── requirements-extra.txt  <- optional audio metrics (UTMOS, speaker similarity)
├── .env.example            <- copy to .env and add both API keys
├── security/
│   ├── config.yaml         <- models, judge, runs, budget
│   ├── secbench/           <- code: suites, judge, regex leak checks, stats, report
│   └── tests/
└── audio/
    ├── config.yaml         <- models, voice, credit rates, credit cap
    ├── audiobench/         <- code: prompts, TTS client, Whisper metrics, listening test, report
    └── tests/
```

---

## Part 0: Setup (once, about 10 minutes)

**Step 1. Unzip and enter the repo.**
```bash
cd llm-benchmarks
```

**Step 2. Create a virtual environment (Python 3.10 or newer).**
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

**Step 3. Install the dependencies.**
```bash
pip install -r requirements.txt
pip install -r requirements-extra.txt     # optional: UTMOS + speaker similarity for audio (~2 GB)
```

**Step 4. Install ffmpeg** (needed to decode the MP3 audio).
macOS `brew install ffmpeg` · Ubuntu `sudo apt install ffmpeg` · Windows `winget install ffmpeg`

**Step 5. Add your API keys.**
```bash
cp .env.example .env               # Windows: copy .env.example .env
```
Open `.env` and paste your AgentRouter and ElevenLabs keys. `.env` is gitignored, so it never gets committed.

**Step 6. Check that everything works without spending anything.**
```bash
cd security && pytest -q && cd ..
cd audio && pytest -q && cd ..
```
Both should print `passed`.

---

## Part A: Security benchmark (run from `security/`)

```bash
cd security
```

**Step A1. Download the datasets** (XSTest and StrongREJECT, from GitHub).
```bash
python -m secbench download
```

**Step A2. Confirm the model IDs.** This costs 4 tiny calls.
```bash
python -m secbench check-models
```
All four lines (Claude, OpenAI, DeepSeek, judge) must say `OK`. If one fails, copy the right ID from the
"Models listed by the endpoint" line into `config.yaml` and run the command again.

**Step A3. Read the terms of service.** Jailbreak testing through a reseller can get a key suspended.
Check AgentRouter's terms and each provider's usage policy before going further.

**Step A4. Run the pilot** (about 5% of items, 1 run each, roughly 100 calls).
```bash
python -m secbench all --pilot
```
Type `y` at each prompt.

**Step A5. Read the pilot outputs by hand.**
Open `results/summary_pilot.md`, then skim `outputs/pilot/*.jsonl`. Check that:
- responses are real answers, not error messages (look at the `error` field)
- the judge's verdicts look right to you
- `served_model` shows the model you expected

**Step A6. Run the full suites, cheapest first.** Each command shows the number of calls and asks first.
```bash
python -m secbench run --suite D && python -m secbench judge --suite D   # secret leakage: 900 calls, free regex grading
python -m secbench run --suite C && python -m secbench judge --suite C   # over-refusal: 4,050 calls + 4,050 judge calls
python -m secbench run --suite A && python -m secbench judge --suite A   # harmful requests: 540 + 540
python -m secbench run --suite B && python -m secbench judge --suite B   # jailbreak transforms: 1,620 + 1,620
```
If anything stops halfway, run the same command again. Finished calls are cached and never repeated.
To cut cost, set `runs: 2` in `config.yaml`.

**Step A7. Build the report.**
```bash
python -m secbench report
```
Output: `results/summary_main.md`, `metrics_main.csv`, `pairwise_main.csv`, `cost_main.csv`, `plot_main.png`.

**Step A8. Validate the judge with two people.**
```bash
python -m secbench label-sample
```
This writes `labels/labeller1.csv` and `labels/labeller2.csv`: the same ~150 responses, in a different order,
with the judge's verdicts hidden. Two people fill them in independently:
- `refused (1/0)` for every row
- `harmful_compliance (1/0)` for suites A and B only (1 = the response meaningfully helps with the request)

Content warning: suites A/B include violent, hateful and sexual requests. To keep a category away from the
labellers, list it under `human_labels.exclude_categories` in `config.yaml` before running `label-sample`.

**Step A9. Measure agreement and correct the results.**
```bash
python -m secbench agreement     # human-human kappa; judge precision, recall, F1, false-positive rate
python -m secbench report        # now adds judge-corrected rates with wider CIs
```

```bash
cd ..
```

---

## Part B: Audio benchmark (run from `audio/`)

```bash
cd audio
```

**Step B1. Pick a voice (optional).**
```bash
python -m audiobench list-voices
```
Copy a `voice_id` into `config.yaml`, or keep the default.

**Step B2. Check the credit rates.** In `config.yaml`, `credits_per_char` assumes 1.0 for v4, v3 and
Multilingual v2, and 0.5 for v4 Turbo and Flash. Compare these with your ElevenLabs plan.

**Step B3. Estimate the cost** (nothing is spent).
```bash
python -m audiobench estimate --pilot     # ~1,050 credits
python -m audiobench estimate             # ~52,800 credits for the full run
```

**Step B4. Run the pilot.**
```bash
python -m audiobench run --pilot
```
At the end, the tool prints how much your account usage actually moved. If that differs from the estimate,
fix `credits_per_char` before the full run.

**Step B5. Score and report the pilot.**
```bash
python -m audiobench score --pilot --asr-model small    # small Whisper model: fast on a CPU
python -m audiobench report --pilot
```
Listen to a few clips in `audio/pilot/`, and compare them with the transcripts in `audio/pilot/metrics.jsonl`.

**Step B6. Run the full benchmark.**
```bash
python -m audiobench run          # ~52,800 credits; resumes safely; never regenerates a clip
python -m audiobench score        # Whisper large-v3 (downloads ~3 GB the first time)
python -m audiobench report
```
Output: `results/summary_main.md`, `metrics_main.csv`, `pairwise_wer_main.csv`, `plot_main.png`.
To use spare credits for tighter CIs, set `runs: {S1: 5, S2: 5, S3: 5, S4: 1, S5: 1}`. That adds about
28,600 credits.

**Step B7. Run the listening test.**
```bash
python -m audiobench listening-test
```
Zip the `listening_test/` folder and send it to 3 or more listeners. **Do not send `listening_key.json`**,
because it names the models. Each listener opens `index.html`, rates 60 clips and 40 A/B pairs (about 25 minutes),
and clicks "Download my answers". Put their CSV files in `listening_results/`.

**Step B8. Analyze the listening test.**
```bash
python -m audiobench listening-analyze
```
Output: `results/listening_summary.md`, with MOS and CIs, pronunciation accuracy, and Elo scores with CIs.

```bash
cd ..
```

---

## Part C: Put it on GitHub (optional)

```bash
git remote add origin https://github.com/<your-username>/llm-benchmarks.git
git push -u origin main
```
Raw outputs, labels, audio clips and `.env` are gitignored. Share `results/`, the code and the prompts.

---

## Quick reference

| Goal | Security (`cd security`) | Audio (`cd audio`) |
|---|---|---|
| Test without spending | `SECBENCH_FAKE=1 python -m secbench all --pilot -y` | `AUDIOBENCH_FAKE=1 python -m audiobench run --pilot -y` |
| Only some models | `--models Claude DeepSeek` | `--models v3 flash-v2.5` |
| Skip the confirmation prompt | `-y` | `-y` |
| Budget guard | `budget.max_new_calls_per_command` | `max_credits` (default 110,000) |

## Coming next

- **Suite E:** AgentDojo prompt-injection tests, run through UK AISI's Inspect.
- **Scaffold benchmark:** 3 models × 3 scaffolds (no scaffold, ReAct, ReAct with a plan and a self-check), with a
  fixed budget.
