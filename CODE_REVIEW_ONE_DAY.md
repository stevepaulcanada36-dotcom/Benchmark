# Code review and one-day changes

## Summary

The repository is a useful working base, but it is **not yet the full three-part benchmark** described in the research plan.

### What is present
- `audio/`: generation, WER/text-normalization metrics, reporting, and a listening-test workflow.
- `security/`: suites A–D, LLM judging for A–C, regex-based secret leakage checks for D, bootstrap statistics, and report generation.
- Security tests: **5 passed** in the review environment.
- Audio tests: collection was blocked in the review environment because `jiwer` was not installed. This is a missing dependency in the environment, not proof that the audio tests themselves fail. Install `requirements.txt` before re-running.

### Important gaps / caveats
1. **Scaffold benchmark is not implemented.** There is no scaffold/AgentDojo implementation in the uploaded repository; the README says it is “Coming next.” Do not claim it has been run.
2. **The README's original full-run schedule is too large for a one-day deadline.** Security suite C and repeated runs across A/B/C can require thousands of model and judge calls. Use a narrowed, disclosed scope.
3. **Audio confidence intervals depend on the number of independent items.** Running only two suites or a pilot reduces scope; report the actual sample sizes and do not overstate generalizability.
4. **Audio optional metrics need extra packages and compute.** UTMOS and speaker similarity are optional and can consume setup time. For a same-day submission, prioritize WER, normalization checks, latency/cost, and a clear limitation statement if optional metrics cannot run.
5. **Judge validation is not complete merely because judge outputs exist.** Human labels and the `agreement` workflow are needed before claiming the LLM judge has been validated.
6. **Provider IDs and costs are configuration assumptions.** Verify actual model IDs, API access, terms, and current ElevenLabs credit rates before full calls.

## Changes made
- Added a one-day execution section to the README with commands that use existing CLI capabilities and avoid pretending the missing scaffold benchmark exists.
- The original full benchmark configs were left unchanged, so the reduced run does not silently redefine the main experiment.

## Recommended reporting language

“This is a time-constrained, reduced-scope benchmark. We ran the specified audio suites and security suites on the models and settings listed in the released configuration. Results are reported with confidence intervals where supported by the implementation. The scaffold factorial and full human-validation study were not completed within the available time and are treated as limitations, not as completed results.”

## Validation performed during review
- `security/tests`: 5 tests passed.
- `audio/tests`: unable to collect because `jiwer` was missing from the active review environment. Install project dependencies and rerun.
- No live provider calls were made during this review.
