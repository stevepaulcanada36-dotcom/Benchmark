# security-bench

Jailbreak, over-refusal and guardrail benchmark for three models on AgentRouter (Claude, OpenAI, DeepSeek).
Built for STA2453H: exact prompts, released code, repeated runs, 95% CIs, and a judge validated against humans.

| Suite | What it measures | Data | Grader |
|---|---|---|---|
| A | Compliance with direct forbidden requests | StrongREJECT small (60) or full (313) | LLM judge, StrongREJECT rubric |
| B | Same prompts in 3 published jailbreak transforms (refusal suppression, prefix injection, base64; Wei et al. 2023) | 60 x 3 | Same judge |
| C | Over-refusal on safe prompts, and refusal on unsafe contrast prompts | XSTest (250 safe + 200 unsafe) | LLM judge (XSTest 3-way labels) + keyword baseline |
| D | Leaking a secret from the system prompt | 4 system prompts x 25 extraction attempts, fresh random secret per item | **Regex only** (exact, spaced, reversed, base64, acrostic, NATO) |

Suite E (AgentDojo prompt injection) and the scaffold factorial come next, using UK AISI's Inspect.

## Setup (once)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
cp ../.env.example ../.env        # then put your AgentRouter key in .env
python -m secbench download
python -m secbench check-models
```

`check-models` lists what the endpoint offers and sends each model one tiny request. Fix the IDs in
`config.yaml` until all four (3 models + judge) say OK. Each one costs a single short call.

## Run order

```bash
# 1. Pilot: about 5% of items, 1 run, stored in outputs/pilot/. Read the outputs before going further.
python -m secbench all --pilot
#    open outputs/pilot/*.jsonl and results/summary_pilot.md, and check the responses look sane

# 2. Full runs, one suite at a time (cheapest first). Each command asks before spending.
python -m secbench run --suite D && python -m secbench judge --suite D     # 900 calls, regex grading
python -m secbench run --suite C && python -m secbench judge --suite C     # 4,050 calls + 4,050 judge calls
python -m secbench run --suite A && python -m secbench judge --suite A     # 540 + 540
python -m secbench run --suite B && python -m secbench judge --suite B     # 1,620 + 1,620
python -m secbench report                                                  # results/summary_main.md

# 3. Validate the judge with two humans
python -m secbench label-sample     # labels/labeller1.csv + labeller2.csv (blinded, same ~150 items)
#    two people fill the columns independently
python -m secbench agreement        # kappa, judge precision/recall/F1/FPR
python -m secbench report           # now adds judge-corrected rates with wider CIs
```

Interrupted? Re-run the same command. Finished calls are cached in `outputs/`, and failed calls are retried.
`--models Claude DeepSeek` restricts to some models, and `-y` skips the confirmation prompt.

Call counts above assume `runs: 3`. To halve cost, set `runs: 2`, or set `include_unsafe_contrast: false` for Suite C.

## What gets reported

- Per model and suite: the rate, a 95% CI from a cluster bootstrap over items (runs kept together), items x runs,
  the flip rate (items whose outcome changed between runs), and judge failures. Failures are counted, never guessed.
- Pairwise model differences: paired bootstrap CI, with p-values Holm-adjusted within each metric.
- After `agreement`: rates corrected for judge error (Rogan-Gladen). The CI bootstraps the test items and the
  human calibration set together, so judge uncertainty widens it.
- Cost: calls, errors, median latency, tokens. The model name the API says it served is recorded, which catches
  router substitutions.

## Judge rules (the lecture's "4 vs 4.0 vs 4.5" problem)

The judge must return JSON. `refused` must be 0 or 1. Scores must be integers 1-5: `4.0` is accepted as 4,
while `4.5` or "The answer deserves a 4" are rejected. On invalid output the judge is asked once more, and if
that fails too, the item is logged as `judge_failed`. The judge model (`glm-5.3` by default) is not one of the
models under test. Prompts are in `secbench/judge.py`, so release them with your results.

## Before you run: ground rules

- **Terms of service.** Jailbreak testing through a reseller can get a key suspended. Check AgentRouter's
  terms and each provider's usage policy first.
- **Harmful text stays local.** `outputs/` and `labels/` are gitignored. Publish `results/`, the code and
  prompts, and at most redacted examples, with a content warning.
- **Human labelling.** Suites A/B include violent, hateful and sexual requests (StrongREJECT categories).
  Use `human_labels.exclude_categories` in `config.yaml` to keep any category away from labellers.

## Testing without spending

```bash
SECBENCH_FAKE=1 python -m secbench all --pilot -y     # fake responses, exercises the whole pipeline
pytest -q
```
