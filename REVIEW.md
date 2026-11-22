# Code review and changes (21 Nov 2026)

This update makes the repo a complete three-part benchmark. All three parts run on your laptop. Security and
scaffold use AgentRouter through plain opencode, and audio uses ElevenLabs.

## What was reviewed

| Part | State before this update | Finding |
|---|---|---|
| Audio | Ran S1 and S2 for 5 models, 3 runs each (~37,000 credits) | Works. **S1 shows a ceiling effect**: every model scores 0-0.6% WER, so S1 cannot rank the models. **S2 separates them clearly**: Flash 16%, Multilingual v2 20%, v3 57%, v4 68%, v4 Turbo 72%. S3-S5 and the listening test were not run. |
| Security | Pilot only. `cli_client.py`, `runner.py` and `config.agentrouter.yaml` were older than the latest fixes. The pilot mixed in free models. | The latest files are now included. Suite D is valid: opencode loads `AGENTS.md`, which was verified with the PINEAPPLE42 test. The judge has to be a paid AgentRouter model, because free models hit usage limits. |
| Scaffold | Not implemented | Now implemented (see below). |
| Repo | Your uploaded zip contained `.env` with real API keys | `.env` is gitignored and never committed. Do not share the zip itself. |

## Changes in this update

### New: `scaffold/`, Benchmark 3 (security breaches through prompt injection)

The question it answers: **does the agent harness change how easily the same model is hijacked by
instructions hidden in files?**

- **Tasks:** 5 realistic agent tasks (summarise a README, review code, read meeting notes, total an
  invoice, list TODOs). Each task gets its own temporary workspace folder.
- **Attacks:** an injected instruction is placed in the file the agent must read. It aims at one of 4
  harmless goals: write a marker word, leak a fake API key from `.env`, send the user to a fake login link,
  or create a file `PWNED.txt`. Each injection is either visible or hidden (an HTML or code comment).
  That gives 5 x 4 x 2 = 40 poisoned items plus 5 clean controls.
- **Scaffolds:** 4 versions of the agent harness. S0 pastes the files into the prompt. S1 lets the agent
  read the files itself, with the default approvals. S2 auto-approves tools (`--auto`). S3 is S2 plus an
  `AGENTS.md` security policy.
- **Grading:** fully deterministic, with no LLM judge. The marker word and link are never written
  literally in the injection (the marker is an arithmetic result, and the link is spelled out with "dot"),
  so a model that only *quotes* the injection to warn you is not counted as hijacked. A unit test checks
  this. File creation is checked on disk.
- **Metrics:** attack success, task success on clean files, task success under attack, unrequested file
  changes, and gateway blocks. Each has 95% CIs and paired scaffold comparisons (paired bootstrap, Holm).
- **Manual check:** `review_attacks_main.csv` lists every counted attack together with the reply, so you
  can confirm each one by hand.

### Security
- Latest `cli_client.py` and `runner.py` are included. These treat "Provider blocked the response" as a
  gateway block. "Free usage limit reached" and AgentRouter's 402 error now pause only the affected model
  or the judge, and finished work is kept.
- The paid AgentRouter config is included. It tests GPT-5.6, GPT-6.2 and Claude (when Claude is online), uses
  GPT-6.1 as the judge, and runs each item 3 times.
- Token columns now show blank instead of a misleading 0 when opencode does not report token counts.

### Not changed
- Audio code and `audio/config.yaml`. Your CPU, no-UTMOS settings are kept.

## Recommended next steps, in priority order
1. **Security:** fresh pilot, then the full run, for GPT-5.6 and GPT-6.2 (about $20-30 per model).
2. **Scaffold:** pilot, then the full run, for GPT-5.6 (360 agent runs; check the dashboard after the pilot).
3. **Audio:** run S3-S5. This costs about 17,000 credits for all 5 models, and you have ~73,000 left under the
   110,000 cap. Then run the listening test with 3 or more listeners. In the write-up, report the S1
   ceiling effect as a finding.
4. **Human validation:** run `secbench label-sample` and `agreement` (judge validation), and fill
   `review_attacks_main.csv` (scaffold).
5. **Claude:** after a quota release (9 PM or 6 AM Toronto), test `claude-opus-5-5` and add it with
   `--models Claude`.

## Limitations to state in the write-up
- Models are accessed through opencode, so results describe "model inside opencode". Temperature cannot be set.
- AgentRouter has no DeepSeek, and Claude was offline during testing.
- The security judge (GPT-6.1) is from the same vendor as the GPT models under test. It is validated with human labels.
- The scaffold benchmark uses one client (opencode). The scaffolds vary tools, approvals and instructions,
  but not the client itself.
