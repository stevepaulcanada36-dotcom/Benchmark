# Running the security benchmark on AgentRouter (via opencode)

AgentRouter only serves supported coding clients, so the benchmark runs every prompt through **plain opencode**
(`opencode run`). opencode is on AgentRouter's supported list. Do not install the `opencode-agentrouter`
plugin: it fakes client identity headers, which AgentRouter treats as bypassing its restrictions (a ban reason).

Config: `config.agentrouter.yaml`. It uses low-usage settings: 1 run, Suite D 100 items, Suite C 100 safe
prompts, Suite A 30 prompts, and Suite B off. That is about 1,100 model calls plus about 400 judge calls.

## Step by step (PowerShell, from `llm-benchmarks\security`)

**1. Check that opencode reaches AgentRouter.**
```powershell
opencode models agentrouter
opencode run --model agentrouter/deepseek-v4-flash "Reply with the single word: ready"
```
If the provider is not called `agentrouter` in your opencode config, change `client.provider` in
`config.agentrouter.yaml`. If `opencode run --help` shows a different model flag, change `client.command`.

**2. Fix the model names.** Copy the exact IDs from `opencode models agentrouter` into `models:` and `judge:`
in `config.agentrouter.yaml`.

**3. Check when quotas reset.**
```powershell
python -m secbench quota-times
```
Claude and GPT quotas are released at 02:00 and 11:00 UTC (10:00 and 19:00 Beijing), which is
**9:00 PM and 6:00 AM Toronto time** in winter. They are first come, first served. DeepSeek and gpt-6.1-sol
are announced as unlimited, and Claude Opus 5.5 was announced as temporarily offline.

**4. Check every model.** This costs 4 tiny calls.
```powershell
python -m secbench check-models --config config.agentrouter.yaml
```
All 4 lines must say OK. If Claude fails because it is offline or out of quota, either wait for a release
or run without it (`--models OpenAI DeepSeek`) and report that as a limitation.

**5. Pilot** (about 5% of items, roughly 30 calls), then read `results\summary_pilot.md` and `outputs\pilot\*.jsonl`.
```powershell
python -m secbench all --pilot --config config.agentrouter.yaml
```

**6. Full (lite) run.** Use the same command without `--pilot`. It asks before spending.
```powershell
python -m secbench all --config config.agentrouter.yaml
```
- **Quota runs out for one model:** that model is paused and the others keep going. Run the same
  command again after the next release (step 3). Finished calls are never repeated.
- **401 / unauthorized:** everything stops at once. Fix access in opencode first.
- **400 content-blocked:** recorded as `gateway_block_rate`, not as a model refusal, and left out of the
  model comparisons.

**7. Results** are in `results\summary_main.md`, the CSVs and `plot_main.png`. Commit and push them.

## What to write in the report

- Models were accessed through AgentRouter using opencode in non-interactive mode. Results describe
  "model inside opencode": the client adds its own system prompt, and temperature cannot be set.
- Suite D puts the secret in an `AGENTS.md` instruction file in an empty folder, which is a realistic leak
  scenario for coding agents.
- Gateway blocks are reported separately. Quota limits and model availability on AgentRouter are limitations.
- Report the reduced scope (1 run; item caps; Suite B off) and the dates of the runs.
