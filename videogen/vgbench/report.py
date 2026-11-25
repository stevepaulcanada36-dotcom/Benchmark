"""Turns ratings (videogen/ratings/*.csv) and automatic measures into results/summary.md and results/metrics.csv.

95% CIs: cluster bootstrap over storyboards (a storyboard's shots, repeats, tasks and raters stay together).
Rater consistency: hidden repeat tasks, compared with the first rating of the same clip.
"""
import csv
import json
from datetime import date

import numpy as np
import pandas as pd

from .core import WORK, seeds_set
from .items import SB_BY_ID

B = 2000
TEXT_SHOTS = {"SB1-2", "SB1-3", "SB4-1", "SB4-2"}


def load():
    key = json.loads((WORK / "rating" / "key_DO_NOT_OPEN_BEFORE_RATING.json").read_text(encoding="utf-8"))
    files = sorted((WORK / "ratings").glob("*.csv"))
    if not files:
        raise SystemExit("No ratings yet: save the CSV from the rating page into videogen/ratings/.")
    r = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
    k = pd.DataFrame.from_dict(key, orient="index").reset_index(names="task")
    r = r.merge(k, on=["task", "type"], how="left")
    r["sb"] = r["sb"].fillna(r["cid"].str.split("-").str[0])
    return r


def boot(df, value, rng, stat=np.mean):
    """Estimate and 95% CI, resampling storyboards."""
    df = df.dropna(subset=[value])
    if df.empty:
        return np.nan, np.nan, np.nan
    groups = {g: d[value].to_numpy(float) for g, d in df.groupby("sb")}
    keys = list(groups)
    est = stat(np.concatenate(list(groups.values())))
    sims = []
    for _ in range(B):
        pick = rng.choice(len(keys), len(keys))
        sims.append(stat(np.concatenate([groups[keys[i]] for i in pick])))
    lo, hi = np.percentile(sims, [2.5, 97.5])
    return est, lo, hi


def qwk(a, b, k=5):
    """Quadratic-weighted Cohen's kappa for two lists of 1..k ratings."""
    a, b = np.asarray(a, int) - 1, np.asarray(b, int) - 1
    if len(a) < 2:
        return np.nan
    O = np.zeros((k, k))
    for x, y in zip(a, b):
        O[x, y] += 1
    W = np.array([[(i - j) ** 2 for j in range(k)] for i in range(k)]) / (k - 1) ** 2
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return 1 - (W * O).sum() / max((W * E).sum(), 1e-12)


def report():
    rng = np.random.default_rng(2453)
    r = load()
    num = lambda s: pd.to_numeric(s, errors="coerce")
    clip = r[(r.type == "clip") & r.get("repeat_of", pd.Series(index=r.index)).isna()].copy()
    rep = r[(r.type == "clip") & r.get("repeat_of", pd.Series(index=r.index)).notna()].copy()
    sbt, pair = r[r.type == "storyboard"].copy(), r[r.type == "pair"].copy()
    for c in ("identity", "objects", "motion", "prompt"):
        clip[c] = num(clip[c])
    clip["within"] = clip[["identity", "objects", "motion"]].mean(axis=1)
    clip["sound_n"] = num(clip["sound"])
    clip["text_ok"] = clip["text"].map({"yes": 1.0, "partly": 0.5, "no": 0.0})
    clip.loc[~clip.cid.isin(TEXT_SHOTS), "text_ok"] = np.nan
    clip["demo_yes"] = (clip["demo"] == "yes").astype(float)
    for c in ("character", "style", "place", "story"):
        sbt[c] = num(sbt[c])
    sbt["state_ok"] = sbt["state"].map({"yes": 1.0, "partly": 0.5, "no": 0.0})
    pair["identical"] = (pair["similar"] == "nearly identical").astype(float)

    models = sorted(r.model.dropna().unique())
    rows = []

    def add(group, metric, df, col, pctg=False, filt=None):
        for m in models:
            d = df[df.model == m]
            if filt is not None:
                d = d[filt(d)]
            e, lo, hi = boot(d, col, rng)
            rows.append(dict(group=group, metric=metric, model=m, estimate=e, ci_low=lo, ci_high=hi,
                             n=int(d[col].notna().sum()), percent=pctg))

    shots = lambda d: d.kind.isin(["shot", "repeat", "reseed"]) if "kind" in d else d.cid.str.startswith("SB")
    clip["kind"] = np.where(clip.cid.str.startswith("C1"), "control", "shot")
    add("A. Within one clip (1-5)", "Same character start to end", clip, "identity", filt=lambda d: d.kind == "shot")
    add("A. Within one clip (1-5)", "Objects and background stay put", clip, "objects", filt=lambda d: d.kind == "shot")
    add("A. Within one clip (1-5)", "Smooth, flicker-free motion", clip, "motion", filt=lambda d: d.kind == "shot")
    add("A. Within one clip (1-5)", "Follows the prompt", clip, "prompt", filt=lambda d: d.kind == "shot")
    add("A. Within one clip (1-5)", "Sound fits the picture", clip, "sound_n", filt=lambda d: d.kind == "shot")
    add("A. Within one clip (1-5)", "Real-world control: within-clip consistency", clip, "within", filt=lambda d: d.kind == "control")
    add("A. Within one clip (1-5)", "Game-style shots: within-clip consistency", clip, "within", filt=lambda d: d.kind == "shot")
    add("B. Across the three shots (1-5)", "Same character", sbt, "character")
    add("B. Across the three shots (1-5)", "Same art style", sbt, "style")
    add("B. Across the three shots (1-5)", "Same place", sbt, "place")
    add("B. Across the three shots (1-5)", "Reads as one story", sbt, "story")
    add("B. Across the three shots (1-5)", "Story detail carries over (coins, boat, lanterns...)", sbt, "state_ok", True)
    add("C. Text and numbers", "Requested text or numbers correct", clip, "text_ok", True)
    add("D. Repeatability", "Same prompt + same seed looks nearly identical", pair, "identical", True, filt=lambda d: d.pair == "same seed")
    add("D. Repeatability", "Same prompt + new seed looks nearly identical", pair, "identical", True, filt=lambda d: d.pair == "new seed")
    add("E. Hackathon demo", "Clips rated usable in a 1-minute demo", clip, "demo_yes", True, filt=lambda d: d.kind == "shot")
    M = pd.DataFrame(rows)

    # rater consistency: hidden repeats vs first rating
    rc = []
    if not rep.empty:
        first = r[r.type == "clip"].set_index(["rater", "task"])
        for c in ("identity", "objects", "motion", "prompt"):
            a, b = [], []
            for _, x in rep.iterrows():
                if (x.rater, x.repeat_of) in first.index:
                    v0, v1 = num(pd.Series([first.loc[(x.rater, x.repeat_of), c], x[c]]))
                    if not (np.isnan(v0) or np.isnan(v1)):
                        a.append(v0), b.append(v1)
            if a:
                rc.append(dict(question=c, pairs=len(a), exact=np.mean(np.equal(a, b)),
                               within_1=np.mean(np.abs(np.subtract(a, b)) <= 1), qwk=qwk(a, b)))
    RC = pd.DataFrame(rc)

    # automatic measures vs human ratings
    ag = []
    auto_p = WORK / "results" / "auto.csv"
    if auto_p.exists():
        A = pd.read_csv(auto_p)
        j = clip.merge(A, on=["model", "cid"], how="inner", suffixes=("", "_a"))
        if len(j) > 3:
            ag.append(("Flicker (lower = steadier) vs 'smooth motion' rating", j["flicker"].corr(j["motion"], method="spearman"), len(j)))
            ag.append(("Pops vs 'objects stay put' rating", j["pops"].corr(j["objects"], method="spearman"), len(j)))
        sbA = A[A.kind == "shot"].groupby(["model", "sb"])["palette_within"].mean().reset_index()
        js = sbt.merge(sbA, on=["model", "sb"])
        if len(js) > 3:
            ag.append(("Colour difference between shots vs 'same art style' rating", js["palette_within"].corr(js["style"], method="spearman"), len(js)))
    out = WORK / "results"
    out.mkdir(exist_ok=True)
    M.to_csv(out / "metrics.csv", index=False)

    def cell(x):
        if np.isnan(x.estimate):
            return "n/a"
        f = (lambda v: f"{v * 100:.0f}%") if x.percent else (lambda v: f"{v:.2f}")
        return f"{f(x.estimate)} ({f(x.ci_low)}-{f(x.ci_high)})"

    L = [f"# VideoGenBench results", "",
         f"Generated {date.today()}. Raters: {', '.join(sorted(r.rater.dropna().unique()))}. "
         f"Each cell: estimate (95% CI, cluster bootstrap over storyboards). 1-5 scales: 5 = strongly agree.", ""]
    for g, d in M.groupby("group", sort=True):
        L += [f"## {g}", "", "| Metric | " + " | ".join(models) + " |", "|---|" + "---|" * len(models)]
        for met in dict.fromkeys(d.metric):
            L.append(f"| {met} | " + " | ".join(cell(d[(d.metric == met) & (d.model == m)].iloc[0]) for m in models) + " |")
        L.append("")
    noseed = [m for m in models if not seeds_set(m)]
    if noseed:
        L += [f"Note: seeds could not be set for {', '.join(noseed)} (clips made in the web app), so for "
              "that model the 'same seed' pair is just a second try with the same prompt, like the 'new seed' pair.", ""]
    L += ["## Storyboards, by hackathon judging criterion", "", "| Storyboard | Serves | Demo-usable shots | Cross-shot character |",
          "|---|---|---|---|"]
    for sid, sb in SB_BY_ID.items():
        d = clip[(clip.sb == sid) & (clip.kind == "shot")]
        s = sbt[sbt.sb == sid]
        L.append(f"| {sb['name']} | {', '.join(sb['criteria'])} | {d.demo_yes.mean() * 100:.0f}% | "
                 f"{s.character.mean():.1f} |" if len(d) else f"| {sb['name']} | {', '.join(sb['criteria'])} | n/a | n/a |")
    L += ["", "## Rater consistency (hidden repeats)", ""]
    if RC.empty:
        L.append("No repeat pairs rated yet.")
    else:
        L += ["| Question | Pairs | Same score | Within 1 point | Weighted kappa |", "|---|---|---|---|---|"]
        L += [f"| {x.question} | {x.pairs} | {x.exact * 100:.0f}% | {x.within_1 * 100:.0f}% | {x.qwk:.2f} |" for x in RC.itertuples()]
    L += ["", "## Do the automatic measures agree with the ratings?", ""]
    L += [f"- {a}: Spearman {c:.2f} (n = {n})" for a, c, n in ag] or ["Run `python -m vgbench auto` first."]
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("Wrote videogen/results/summary.md and metrics.csv")
