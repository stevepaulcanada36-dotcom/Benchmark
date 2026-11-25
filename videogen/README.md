# VideoGenBench (Benchmark 6): is AI-generated video consistent enough for a short game demo?

**The use case.** A solo developer has to make a demo video of under one minute for a game hackathon (here, Reddit's
Game of the Day hackathon on Devvit, judged on Delightful UX, Polish, Reddity and Daily Content). Can an AI video
model, here through ElevenLabs, produce intro shots, transitions and story beats that stay consistent enough to cut
together? A video where the hero changes colour between shots, or the coin counter reads "35" as "3S", looks
unpolished. This benchmark measures exactly those failures.

> **Hackathon rule to keep in mind:** the demo video "should include footage that shows the Project functioning".
> Generated clips can only be the intro, transitions or a story teaser around real gameplay footage, not a
> replacement for it. Check that your ElevenLabs plan lets you use the clips publicly.

## What is generated

Six **storyboards** of three shots each, all featuring the same invented character (Mira, a fox with a green scarf
and straw hat) in the same cozy 2D village style. Every shot repeats the character and style description word for
word, so any drift between shots comes from the model. Each storyboard has a built-in **story detail that must
carry over**, which is checked by the rater:

| Storyboard | What must stay consistent | Judging criterion it serves |
|---|---|---|
| Daily visit to the theatre | Coin sign reads 35, then 27; same red door | Delightful UX, Daily Content |
| Boat trip to the island | Same small blue boat with a white stripe | Delightful UX, Polish |
| Follow camera | Camera stays behind Mira; fountain and yellow-awning bakery stay put | Polish, Delightful UX |
| Today's challenge | Poster text "DAY 12" stays readable; same grey cat | Daily Content, Reddity |
| Community vote | Lantern count goes from 3 to 5; same bridge and villagers | Reddity, Daily Content |
| Same street, three times of day | Only the light changes; houses and lamp posts identical | Polish, Daily Content |

Plus, for every storyboard, shot 1 again with the **same seed** and with a **new seed** (is the model repeatable?),
and a **real-world control** (hands clapping three times on a table) to separate "bad at cartoons" from "bad at
consistency". That is 32 clips of 4 seconds per model.

## What is measured

**By you, on a blind rating page** (model names hidden, order shuffled; about 35 minutes per model):

| Task | Questions |
|---|---|
| One clip | Same character start to end; objects stay put (no melting or popping); smooth motion (no flicker); follows the prompt (actions, counts, colours), each 1-5. Text and numbers correct (yes / partly / no). Sound fits (1-5). **Would you use it in a 1-minute demo?** (yes / maybe / no) |
| Storyboard (3 shots side by side) | Same character; same art style; same place; reads as one story, each 1-5. Story detail carries over (yes / partly / no) |
| Pair (same prompt, twice) | Nearly identical / same scene with small differences / clearly different |

15% of single-clip tasks come back later under a new code. Comparing your two ratings of the same clip gives your
own **rater consistency** (same score, within 1 point, weighted kappa), so the report shows how much to trust a single
rater. More raters can rate the same page; their CSVs are combined automatically.

**Automatically, from the frames** (`auto`): flicker (frame-to-frame change), pops (sudden jumps), colour-palette
distance between the shots of a storyboard, pixel difference between same-seed repeats, duration and whether there is
an audio track. The report shows how well each one agrees with your ratings (Spearman), which tells you whether the
cheap automatic check could replace a person next time.

**Statistics**: 95% CIs from a cluster bootstrap over storyboards (a storyboard's shots, repeats and ratings stay
together), as in the other benchmarks.

## Run (from `videogen/`, venv active)

```powershell
python -m vgbench plan                     # writes prompts.csv: 32 prompts with file names and seeds
python -m vgbench generate                 # through the API: needs the ElevenLabs Pro plan; resumes; spending guard in config.yaml
#   or, without Pro: make each clip in the ElevenLabs web app from prompts.csv, save it as its file_name, then
python -m vgbench import C:\path\to\downloads --model veo-3.1-fast
python -m vgbench auto                     # automatic measures, free
python -m vgbench rate                     # builds rating/index.html: open it, rate, Download the CSV into ratings/
python -m vgbench report                   # results/summary.md and metrics.csv
```

To compare models, add them under `models:` in `config.yaml` (use the model id ElevenLabs shows) and generate each.
`pytest -q tests` runs the whole pipeline with fake clips and simulated ratings for free, in a temp folder.

**Cost.** Not measured yet: the API answered HTTP 402 ("requires a Pro plan or above") before any clip was made, and
failed generations are not charged. Measure it on one clip first with `python cost_probe.py`.

## Limitations

One invented character and style; real games look different. The rating is subjective, which is why the page is
blind and has hidden repeats. With one rater the results are that person's judgement. Six storyboards give wide
confidence intervals. The API request fields are the ones the probe used; the ElevenLabs documentation could not be
read automatically, so other options (for example a starting image taken from a real game screenshot, which would be
the most useful test of all) are not used.
