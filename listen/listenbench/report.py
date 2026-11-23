"""Deterministic grading against the known ground truth, then metrics with 95% CIs and paired tests."""
import itertools
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .build import WORK, manifest
from .systems import done

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "audio"))
from audiobench import stats  # noqa: E402
from audiobench.metrics import wer  # noqa: E402

RESULTS = WORK / "results"


# ---------------------------------------------------------------- grading one output
def _matches(text, keywords):
    t = text.lower()
    return any(k in t for k in keywords)


def diarization(words, turns):
    """Speaker count and share of words attributed to the right speaker (best label mapping)."""
    ids = sorted({w["speaker"] for w in words if w.get("speaker") is not None})
    if not words or not ids:
        return len(ids), np.nan
    truth = []
    for w in words:
        mid = ((w["start"] or 0) + (w["end"] or w["start"] or 0)) / 2
        best = min(turns, key=lambda t: 0 if t["start"] <= mid <= t["end"] else min(abs(mid - t["start"]), abs(mid - t["end"])))
        truth.append(best["speaker"])
    pred = [w.get("speaker") for w in words]
    best_acc = 0.0
    labels = sorted({t["speaker"] for t in turns})
    for perm in itertools.permutations(labels + [None] * max(0, len(ids) - len(labels)), len(ids)):
        mp = dict(zip(ids, perm))
        best_acc = max(best_acc, float(np.mean([mp.get(p) == t for p, t in zip(pred, truth)])))
    return len(ids), best_acc


def grade(clip, rec, cfg, tags_events=True):
    g = dict(uid=clip["uid"], suite=clip["suite"], item=clip["item"], condition=clip["condition"],
             system=rec["system"], run=rec["run"], text=rec.get("text", ""))
    words, events = rec.get("words", []), rec.get("events", [])
    timed = [w for w in words if w.get("start") is not None]
    if clip["reference"]:
        g["wer"] = wer(clip["reference"], rec.get("text", ""))
        if timed:
            g["onset_err"] = abs(timed[0]["start"] - clip["speech_start"])
            g["offset_err"] = abs((timed[-1]["end"] or timed[-1]["start"]) - clip["speech_end"])
            g["onset_ok"] = int(g["onset_err"] <= cfg["onset_tolerance_s"])
        gap = cfg["trailing_gap_s"]
        outside = [w for w in timed if w["start"] > clip["speech_end"] + gap or (w["end"] or w["start"]) < clip["speech_start"] - gap]
        if clip["suite"] == "L4":   # words placed on the sound event itself are hallucinated speech too
            e = clip["event"]
            outside += [w for w in timed if e["start"] - 0.2 <= w["start"] <= e["end"] + 0.2 and w not in outside]
        g["inserted_words"] = len(outside)
        g["any_insertion"] = int(bool(outside))
    else:   # L3: no speech at all
        g["halluc_words"] = len(words)
        g["hallucinated"] = int(bool(words))
    if clip["event"] and tags_events:
        e, win = clip["event"], cfg["event_window_s"]
        near = [ev for ev in events if ev.get("start") is not None and abs(ev["start"] - e["start"]) <= win]
        right = [ev for ev in near if _matches(ev["text"], e["keywords"])]
        g["event_any"] = int(bool(near))
        g["event_correct"] = int(bool(right))
        if right:
            g["event_time_err"] = abs(right[0]["start"] - e["start"])
    elif clip["suite"] == "L1" and clip["condition"] == "clean" and tags_events:
        g["false_event"] = int(bool(events))
    if clip["turns"]:
        n, acc = diarization(timed, clip["turns"])
        if any(w.get("speaker") is not None for w in timed):
            g["speakers_found"] = n
            g["speaker_count_ok"] = int(n == 2)
            g["speaker_attribution"] = acc
    return g


def graded(cfg, systems):
    man = {m["uid"]: m for m in manifest()}
    rows = []
    for s in systems:
        for (uid, run), rec in done(s).items():
            if rec.get("error") or uid not in man:
                continue
            rows.append(grade(man[uid], rec, cfg, s["kind"] == "scribe"))
    if not rows:
        raise SystemExit("No transcriptions yet. Run: python -m listenbench transcribe --pilot")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- aggregation
SPECS = [  # (suite filter, condition filter, metric, label, percent?)
    ("L1", "clean", "wer", "WER, clean speech", True),
    ("L1", "cafe_10db", "wer", "WER, cafe noise 10 dB SNR", True),
    ("L1", "cafe_0db", "wer", "WER, cafe noise 0 dB SNR", True),
    ("L1", "street_0db", "wer", "WER, street noise 0 dB SNR", True),
    ("L3", None, "hallucinated", "No-speech clips with invented words (lower is better)", True),
    ("L3", None, "halluc_words", "Invented words per no-speech clip", False),
    ("L1", None, "any_insertion", "Speech clips with words invented in the silence/noise around speech", True),
    ("L1", None, "onset_ok", "Speech onset within tolerance", True),
    ("L1", None, "onset_err", "Speech onset error, seconds", False),
    ("L1", None, "offset_err", "Speech end error, seconds", False),
    ("L4", None, "event_correct", "Sound event tagged correctly, near the right time", True),
    ("L3", None, "event_correct", "Sound event tagged correctly (event-only clips)", True),
    ("L4", None, "event_time_err", "Sound event timing error, seconds", False),
    ("L4", None, "any_insertion", "Words invented on the sound event or in silence", True),
    ("L1", "clean", "false_event", "Clean speech clips with a sound event that was not there", True),
    ("L4", None, "wer", "WER, speech with a sound event", True),
    ("L5", None, "wer", "WER, two-speaker dialogue", True),
    ("L5", None, "speaker_count_ok", "Dialogues where exactly 2 speakers were found", True),
    ("L5", None, "speaker_attribution", "Words attributed to the right speaker", True),
]


def _cluster(sub, col):
    mat = sub.pivot_table(index="unit", columns="run", values=col, aggfunc="mean")
    if mat.empty:
        return (np.nan,) * 3 + (0, 0)
    m, lo, hi = stats.cluster_bootstrap(mat.values)
    return m, lo, hi, mat.shape[0], mat.shape[1]


def write(cfg, systems):
    df = graded(cfg, systems)
    df["unit"] = df["item"]          # L1: the sentence is the cluster (its 4 conditions + runs stay together)
    RESULTS.mkdir(exist_ok=True)
    df.drop(columns=["text"]).to_csv(RESULTS / "graded.csv", index=False)
    rows = []
    for sysname, g in df.groupby("system"):
        for suite, cond, col, label, pct in SPECS:
            sub = g[(g.suite == suite) & ((g.condition == cond) if cond else True)]
            if col not in sub or sub[col].dropna().empty:
                continue
            m, lo, hi, n, r = _cluster(sub.dropna(subset=[col]), col)
            rows.append(dict(system=sysname, suite=suite, condition=cond or "all", metric=col, description=label,
                             estimate=m, ci_low=lo, ci_high=hi, n_units=n, runs=r, percent=pct))
        l1 = g[g.suite == "L1"].pivot_table(index="item", columns="condition", values="wer", aggfunc="mean")
        for cond in ("cafe_10db", "cafe_0db", "street_0db"):
            if {"clean", cond} <= set(l1.columns):
                d, lo, hi, p = stats.paired_bootstrap_diff(l1[cond], l1["clean"])
                rows.append(dict(system=sysname, suite="L1", condition=cond, metric="noise_penalty",
                                 description=f"WER increase, {cond} minus clean (paired)", estimate=d, ci_low=lo,
                                 ci_high=hi, n_units=len(l1), runs=np.nan, percent=True))
        if g.run.nunique() > 1:   # run-to-run stability (same audio, same settings)
            t = g.pivot_table(index="uid", columns="run", values="text", aggfunc="first").dropna()
            if len(t):
                same = float(np.mean([len(set(r)) == 1 for r in t.values]))
                rows.append(dict(system=sysname, suite="ALL", condition="all", metric="identical_reruns",
                                 description="Clips transcribed identically in every run", estimate=same, ci_low=np.nan,
                                 ci_high=np.nan, n_units=len(t), runs=g.run.nunique(), percent=True))
    m = pd.DataFrame(rows)
    m.to_csv(RESULTS / "metrics.csv", index=False)

    # paired system comparisons on the same clips, Holm-adjusted
    pw = []
    comps = [("L1", "wer", "WER (all L1 conditions)"), ("L3", "hallucinated", "No-speech hallucination"),
             ("L1", "onset_err", "Onset error (s)"), ("L1", "any_insertion", "Invented words around speech")]
    for suite, col, label in comps:
        sub = df[df.suite == suite]
        if col not in sub:
            continue
        piv = sub.pivot_table(index="uid", columns="system", values=col, aggfunc="mean")
        unit = sub.groupby("uid")["item"].first()
        for a, b in itertools.combinations(sorted(piv.columns), 2):
            both = piv[[a, b]].dropna()
            if both.empty:
                continue
            per_unit = (both[a] - both[b]).groupby(unit.reindex(both.index)).mean()
            dlt, lo, hi, p = stats.paired_bootstrap_diff(per_unit.values, np.zeros(len(per_unit)))
            pw.append(dict(comparison=label, a=a, b=b, diff=dlt, ci_low=lo, ci_high=hi, p=p, n_units=len(per_unit)))
    pw = pd.DataFrame(pw)
    if len(pw):
        pw["p_holm"] = stats.holm(pw.p.values)
        pw.to_csv(RESULTS / "pairwise.csv", index=False)

    _markdown(df, m, pw, cfg)
    _plot(m)


def _fmt(v, pct):
    if pd.isna(v):
        return ""
    return f"{100 * v:.1f}%" if pct else f"{v:.2f}"


def _markdown(df, m, pw, cfg):
    systems = sorted(m.system.unique())
    lines = ["# ListenBench results", "",
             f"Generated {date.today().isoformat()}. Every clip was built by us, so the ground truth is exact. "
             "Each cell: estimate (95% CI). CIs: cluster bootstrap over source items (a sentence's four noise "
             "conditions and its repeated runs stay together).", "",
             "| Metric | " + " | ".join(systems) + " |", "|---|" + "---|" * len(systems)]
    keys = m[["metric", "suite", "condition", "description", "percent"]].drop_duplicates(["metric", "suite", "condition"])
    for _, k in keys.iterrows():
        cells = []
        for s in systems:
            r = m[(m.system == s) & (m.metric == k.metric) & (m.suite == k.suite) & (m.condition == k.condition)]
            if r.empty:
                cells.append("n/a"); continue
            r = r.iloc[0]
            ci = "" if pd.isna(r.ci_low) else f" ({_fmt(r.ci_low, k.percent)}-{_fmt(r.ci_high, k.percent)})"
            cells.append(_fmt(r.estimate, k.percent) + ci)
        lines.append(f"| {k.description} [{k.suite}] | " + " | ".join(cells) + " |")
    lines += ["", "n/a: the system does not produce that output (Whisper has no speaker labels or sound-event tags).",
              f"Tolerances: onset {cfg['onset_tolerance_s']} s, event window {cfg['event_window_s']} s, "
              f"words more than {cfg['trailing_gap_s']} s outside the speech count as invented."]
    if len(pw):
        lines += ["", "## Paired comparisons (same clips; paired bootstrap; Holm-adjusted)", "",
                  "| Comparison | A - B | Diff | 95% CI | p (Holm) |", "|---|---|---|---|---|"]
        for _, r in pw.iterrows():
            pct = r.comparison != "Onset error (s)"
            lines.append(f"| {r.comparison} | {r.a} - {r.b} | {_fmt(r['diff'], pct)} | {_fmt(r.ci_low, pct)} to "
                         f"{_fmt(r.ci_high, pct)} | {r.p_holm:.3f} |")
    hal = df[(df.suite == "L3") & (df.get("hallucinated", 0) == 1)] if "hallucinated" in df else pd.DataFrame()
    if len(hal):
        lines += ["", "## What was invented on clips with no speech (check by listening)", "",
                  "| System | Clip | Run | Output |", "|---|---|---|---|"]
        for _, r in hal.sort_values(["system", "uid"]).head(60).iterrows():
            lines.append(f"| {r.system} | {r.uid} | {r.run} | {str(r.text)[:90]} |")
    (RESULTS / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("\nWrote listen/results/summary.md, metrics.csv, pairwise.csv, graded.csv, plot.png")


def _plot(m):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    w = m[(m.metric == "wer") & (m.suite == "L1")]
    conds = ["clean", "cafe_10db", "cafe_0db", "street_0db"]
    systems = sorted(m.system.unique())
    for i, s in enumerate(systems):
        r = w[w.system == s].set_index("condition").reindex(conds)
        x = np.arange(len(conds)) + (i - (len(systems) - 1) / 2) * 0.12
        axes[0].errorbar(x, 100 * r.estimate, yerr=[100 * (r.estimate - r.ci_low), 100 * (r.ci_high - r.estimate)],
                         fmt="o", capsize=3, label=s)
    axes[0].set_xticks(range(len(conds))); axes[0].set_xticklabels(conds); axes[0].set_ylabel("WER % (95% CI)")
    axes[0].set_title("Speech recognition under noise"); axes[0].legend(frameon=False, fontsize=8)
    h = m[m.metric == "hallucinated"].set_index("system").reindex(systems)
    axes[1].bar(systems, 100 * h.estimate, yerr=[100 * (h.estimate - h.ci_low).fillna(0), 100 * (h.ci_high - h.estimate).fillna(0)], capsize=3)
    axes[1].set_ylabel("% of no-speech clips (95% CI)"); axes[1].set_title("Words invented on clips with no speech")
    for ax in axes:
        ax.grid(axis="y", alpha=0.3)
    plt.setp(axes[1].get_xticklabels(), rotation=15)
    fig.tight_layout(); fig.savefig(RESULTS / "plot.png", dpi=150)
