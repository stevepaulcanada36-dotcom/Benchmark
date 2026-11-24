# LLM Benchmarks: Audio, Security, Scaffolds, Listening and Video (STA2453H)

**Website:** [stevepaulcanada36-dotcom.github.io/Benchmark](https://stevepaulcanada36-dotcom.github.io/Benchmark/) (built from the `results/` folders by `python site/build.py`)

This repo holds five benchmarks. Each releases its code and exact prompts, repeats every run, reports 95%
confidence intervals on every number, records cost, and checks its automatic graders against human labels.

| Folder | Benchmark | Models | Grading |
|---|---|---|---|
| `audio/` | Text-to-speech: intelligibility, text normalization, homographs, expressiveness, long-form | 5 ElevenLabs models | Whisper WER, pass/fail checks, listening test |
| `security/` | Harmful-request compliance, over-refusal, system-prompt secret leakage | GPT-5.6, GPT-6.2, Claude (AgentRouter) | Regex (leaks), LLM judge GPT-6.1 + human labels |
| `scaffold/` | Prompt injection: does the agent harness change how easily a model is hijacked? | Same model, 4 scaffolds (AgentRouter) | Deterministic checks + manual review of every hit |
| `listen/` | Audio understanding on clips we build (exact ground truth): noise, timestamps, hallucination on silence, sound events, speakers | Scribe v3, Scribe v2, Whisper large-v3 (+VAD) | Deterministic, against known ground truth |
| `video/` | Audio-visual reasoning on videos we generate: event order, sync, cross-modal hallucination, long clips, modality ablation | Gemini 3.8 Flash, 3.5/3.1 Flash-Lite (free tier) | Deterministic, against known ground truth |

Security and scaffold run through **plain opencode**, which is a client AgentRouter supports. Do not install
the `opencode-agentrouter` plugin: it fakes client headers, which AgentRouter treats as a ban reason.
See [REVIEW.md](REVIEW.md) for the code review, what changed, and the limitations.

---

## Setup (once)

```powershell
cd C:\Users\Steve\Downloads\llm-benchmarks\llm-benchmarks
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # add ELEVENLABS_API_KEY (audio). AgentRouter access is through opencode.
```

**opencode:** your opencode config (`notepad $HOME\.config\opencode\opencode.json`) needs these models under
`agentrouter`: `gpt-5.6-sol`, `gpt-6.1-sol`, `gpt-6.2-sol` and `claude-opus-5-5`. To add one, copy the
`gpt-5.6-sol` block and rename the copy. Test each model:
```powershell
opencode run -m agentrouter/gpt-6.1-sol "Reply with the single word: ready"
```

**AgentRouter timing (Toronto):** Claude and GPT quota batches are released at **9:00 PM and 6:00 AM**
(`python -m secbench quota-times` prints them). gpt-6.1-sol is announced as unlimited. If a model runs out of
quota during a run, only that model pauses; run the same command again later and it continues.

**Check that nothing is broken (free):** run `pytest -q` inside `security`, `scaffold` and `audio`.

---

## Part A: Audio (`cd audio`)

S1 and S2 are done (results in `audio/results/`). Remaining steps:
```powershell
python -m audiobench estimate --suites S3 S4 S5        # ~17,000 credits for all 5 models
python -m audiobench run --suites S3 S4 S5
python -m audiobench score
python -m audiobench report
python -m audiobench listening-test                    # send listening_test/ (NOT listening_key.json) to 3+ listeners
python -m audiobench listening-analyze                 # after their CSVs are in listening_results/
```
Details: [audio/DETAILS.md](audio/DETAILS.md).

## Part B: Security (`cd security`, AgentRouter)

```powershell
python -m secbench download
python -m secbench check-models --models GPT-5.6 GPT-6.2 --config config.agentrouter.yaml
Remove-Item -Recurse -Force outputs\pilot, results -ErrorAction SilentlyContinue
python -m secbench all --pilot --models GPT-5.6 GPT-6.2 --config config.agentrouter.yaml
#   read results\summary_pilot.md, then:
python -m secbench all --models GPT-5.6 GPT-6.2 --config config.agentrouter.yaml   # ~$20-30 per model
python -m secbench all --models Claude --config config.agentrouter.yaml            # once claude-opus-5-5 answers
python -m secbench label-sample        # two people fill labels\labeller1.csv and labeller2.csv
python -m secbench agreement           # kappa, judge precision/recall
python -m secbench report --config config.agentrouter.yaml
```
Suites:
- **A:** 30 StrongREJECT prompts.
- **C:** 100 XSTest safe prompts.
- **D:** 4 secret files x 25 extraction attempts, graded by regex.
- **B** (jailbreak transforms) is off by default because of the ban risk. Set `B.max_items` in the config to enable it.

Details: [security/AGENTROUTER.md](security/AGENTROUTER.md), [security/DETAILS.md](security/DETAILS.md).

## Part C: Scaffold (`cd scaffold`, AgentRouter)

```powershell
python -m scaffbench show                     # see the items and an example poisoned file (no calls)
python -m scaffbench check
python -m scaffbench run --pilot --models GPT-5.6
python -m scaffbench report --pilot
python -m scaffbench run --models GPT-5.6     # 360 agent runs; resumable
python -m scaffbench report                   # then fill results\review_attacks_main.csv (manual check)
```
Details: [scaffold/DETAILS.md](scaffold/DETAILS.md).

## Part E: Listening (`cd listen`, ElevenLabs credits only)

```powershell
python -m listenbench build                  # ~2,000 credits; reuses audio S1 clips
python -m listenbench transcribe --pilot     # prints the real Scribe credits per minute -> config.yaml
python -m listenbench transcribe
python -m listenbench report                 # listen\results\summary.md
```
Details: [listen/README.md](listen/README.md).

## Part F: Video (`cd video`, Gemini free tier, $0)

Needs `GEMINI_API_KEY` in `.env` (free from aistudio.google.com/apikey) and ListenBench built first.
```powershell
pip install google-genai imageio-ffmpeg
python -m videobench build
python -m videobench check-models
python -m videobench run --pilot
python -m videobench run
python -m videobench report                  # video\results\summary.md
```
Details: [video/README.md](video/README.md).

## Part D: Save and push

```powershell
cd C:\Users\Steve\Downloads\llm-benchmarks\llm-benchmarks
git add -A
git commit -m "Results: audio S3-S5, security (AgentRouter), scaffold injection benchmark"
git push origin main
```
Raw outputs, labels, audio clips and `.env` are gitignored. The `results/` folders are committed.
