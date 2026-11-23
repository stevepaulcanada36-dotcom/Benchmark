"""Grades answers against the known ground truth by code, then metrics with 95% CIs and paired tests."""
import itertools
import re
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .run import done, parse
from .scenes import WORK, manifest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "audio"))
from audiobench import stats  # noqa: E402

RESULTS = WORK / "results"
ABSTAIN = {"no audio", "cannot tell", "none"}


def norm(x):
    s = str(x).lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"[^a-z0-9. ]", "", s)
    return " ".join(s.split()).strip(" .")


def number(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    m = re.search(r"-?\d+(?:\.\d+)?", str(x))
    return float(m.group(0)) if m else None


def grade_answer(qq, given):
    """Returns (correct 0/1, abs time error or None)."""
    truth = qq["truth"]
    if given is None:
        return 0, None
    if truth == "no_audio" or (isinstance(truth, str) and norm(truth) in ABSTAIN and qq["kind"] != "choice"):
        return int(norm(given) in ABSTAIN), None
    if qq["kind"] == "choice":
        ok = norm(given) == norm(truth) or norm(given) in {norm(a) for a in qq.get("accept", [])}
        if truth == "no_audio":
            ok = norm(given) in ABSTAIN
        return int(ok), None
    v = number(given)
    if v is None:
        return 0, None
    if qq["kind"] == "count":
        return int(round(v) == int(truth)), None
    err = abs(v - float(truth))
    return int(err <= qq["tol"]), err


def graded(cfg, systems):
    man = {m["uid"]: m for m in manifest()}
    rows = []
    for s in systems:
        for (uid, run), rec in done(s).items():
            if rec.get("error") or uid not in man:
                continue
            clip = man[uid]
            ans = rec.get("parsed") or parse(rec.get("raw")) or {}
            for qq in clip["questions"]:
                a = ans.get(qq["qid"]) if isinstance(ans, dict) else None
                a = a if isinstance(a, dict) else ({"answer": a} if a is not None else {})
                given = a.get("answer")
                ok, err = grade_answer(qq, given)
                conf = number(a.get("confidence")) if a.get("confidence") is not None else None
                conf = min(1.0, max(0.0, conf)) if conf is not None else None
                ts = number(a.get("time_s")) if a.get("time_s") is not None else None
                g = dict(system=s["name"], uid=uid, cid=clip["cid"], suite=clip["suite"], condition=clip["condition"],
                         run=run, qid=qq["qid"], tag=qq["tag"], kind=qq["kind"], truth=str(qq["truth"]), given=str(given),
                         correct=ok, time_err=err, valid=int(bool(ans)), confidence=conf, evidence=a.get("evidence"))
                if clip["condition"] == "video_only" and qq["tag"] in ("audio", "joint", "sync"):
                    g["invented_audio"] = int(given is not None and norm(given) not in ABSTAIN)
                if clip["suite"] == "halluc" and qq["qid"] in ("q1", "q3"):
                    g["false_visual_yes"] = int(norm(given) == "yes")
                if clip["suite"] == "sync" and qq["qid"] == "q2" and clip["condition"] == "shifted":
                    g["false_sync"] = int(norm(given) == "yes")
                if qq.get("time_truth") is not None and ok and clip["condition"] in ("av", "swapped"):
                    g["grounded"] = int(ts is not None and abs(ts - qq["time_truth"]) <= cfg["time_tolerance_s"] *
                                        (2 if clip["suite"].startswith("long") else 1))
                if conf is not None:
                    g["brier"] = (conf - ok) ** 2
                rows.append(g)
    if not rows:
        raise SystemExit("No answers yet. Run: python -m videobench run --pilot")
    return pd.DataFrame(rows)


def _cluster(sub, col):
    mat = sub.pivot_table(index="cid", columns="run", values=col, aggfunc="mean")
    if mat.empty:
        return (np.nan,) * 3 + (0, 0)
    m, lo, hi = stats.cluster_bootstrap(mat.values)
    return m, lo, hi, mat.shape[0], mat.shape[1]


def write(cfg, systems):
    df = graded(cfg, systems)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "graded.csv", index=False)
    short = df[~df.suite.str.startswith("long")]
    rows = []

    def add(sysname, label, sub, col="correct", group="", pct=True):
        if col not in sub or sub[col].dropna().empty:
            return
        m, lo, hi, n, r = _cluster(sub.dropna(subset=[col]), col)
        rows.append(dict(system=sysname, group=group, metric=label, estimate=m, ci_low=lo, ci_high=hi,
                         n_scenes=n, runs=r, percent=pct))

    for sname in sorted(df.system.unique()):
        g, gs = df[df.system == sname], short[short.system == sname]
        add(sname, "Accuracy, all questions", g, group="A. Overall")
        add(sname, "Answers in valid JSON", g, "valid", "A. Overall")
        for suite in ["temporal", "sync", "halluc"] + sorted(x for x in df.suite.unique() if x.startswith("long")):
            add(sname, f"Accuracy, {suite} (original audio+video)", g[(g.suite == suite) & (g.condition == "av")], group="B. Suites")
        for cond in ["av", "video_only", "shifted", "swapped"]:
            for tag in ["visual", "audio", "joint", "sync"]:
                add(sname, f"{tag} questions, {cond}", gs[(gs.condition == cond) & (gs.tag == tag)], group="C. Modality ablation")
        vis = gs[gs.tag == "visual"].pivot_table(index="cid", columns="condition", values="correct", aggfunc="mean")
        for cond in ("video_only", "swapped", "shifted"):
            if {"av", cond} <= set(vis.columns):
                d, lo, hi, _ = stats.paired_bootstrap_diff(vis["av"], vis[cond])
                rows.append(dict(system=sname, group="C. Modality ablation", metric=f"Visual accuracy change, av minus {cond} (paired)",
                                 estimate=d, ci_low=lo, ci_high=hi, n_scenes=len(vis), runs=np.nan, percent=True))
        add(sname, "Says there is a sound when the clip has NO audio track", gs, "invented_audio", "D. Hallucination")
        add(sname, "Says 'yes' to a thing that is not on screen", gs, "false_visual_yes", "D. Hallucination")
        h = gs[gs.suite == "halluc"]
        add(sname, "...same, with the matching sound playing (av)", h[h.condition == "av"], "false_visual_yes", "D. Hallucination")
        add(sname, "...same, with no audio (video_only)", h[h.condition == "video_only"], "false_visual_yes", "D. Hallucination")
        add(sname, "Calls shifted audio 'synchronized'", gs, "false_sync", "E. Sync")
        s2 = gs[(gs.suite == "sync") & (gs.qid == "q2")]
        add(sname, "Sync question correct, original", s2[s2.condition == "av"], group="E. Sync")
        add(sname, "Sync question correct, shifted by %.1f s" % cfg["shift_s"], s2[s2.condition == "shifted"], group="E. Sync")
        add(sname, "Names the swapped (different) sound correctly", gs[(gs.condition == "swapped") & (gs.tag == "audio") & (gs.kind == "choice")], group="E. Sync")
        add(sname, "Time answers: mean absolute error (s)", g, "time_err", "F. Time and evidence", pct=False)
        add(sname, "Right answer AND right timestamp (of right answers)", g, "grounded", "F. Time and evidence")
        add(sname, "Brier score of stated confidence (lower is better)", g, "brier", "G. Calibration", pct=False)
        add(sname, "Mean stated confidence", g, "confidence", "G. Calibration")
        if g.run.nunique() > 1:
            t = g.pivot_table(index=["uid", "qid"], columns="run", values="given", aggfunc="first").dropna()
            if len(t):
                rows.append(dict(system=sname, group="A. Overall", metric="Same answer in every run",
                                 estimate=float(np.mean([len(set(r)) == 1 for r in t.values])), ci_low=np.nan,
                                 ci_high=np.nan, n_scenes=len(t), runs=g.run.nunique(), percent=True))
    m = pd.DataFrame(rows)
    m.to_csv(RESULTS / "metrics.csv", index=False)

    pw = []
    for label, sub in [("Overall accuracy", df), ("Audio questions", short[short.tag.isin(["audio", "joint", "sync"])])]:
        piv = sub.groupby(["cid", "system"]).correct.mean().unstack()
        for a, b in itertools.combinations(sorted(piv.columns), 2):
            both = piv[[a, b]].dropna()
            if len(both):
                d, lo, hi, p = stats.paired_bootstrap_diff(both[a], both[b])
                pw.append(dict(comparison=label, a=a, b=b, diff=d, ci_low=lo, ci_high=hi, p=p, n_scenes=len(both)))
    pw = pd.DataFrame(pw)
    if len(pw):
        pw["p_holm"] = stats.holm(pw.p.values)
        pw.to_csv(RESULTS / "pairwise.csv", index=False)
    _markdown(df, m, pw, cfg)
    _plot(m)


def _f(v, pct):
    return "" if pd.isna(v) else (f"{100 * v:.1f}%" if pct else f"{v:.2f}")


def _markdown(df, m, pw, cfg):
    systems = sorted(m.system.unique())
    lines = ["# VideoBench results", "",
             f"Generated {date.today().isoformat()}. Synthetic clips with exact ground truth; graded by code. "
             "Each cell: estimate (95% CI). CIs: cluster bootstrap over scenes (a scene's audio conditions, questions "
             "and runs stay together).", ""]
    for grp in sorted(m.group.unique()):
        lines += [f"## {grp}", "", "| Metric | " + " | ".join(systems) + " |", "|---|" + "---|" * len(systems)]
        sub = m[m.group == grp]
        for metric in dict.fromkeys(sub.metric):
            cells = []
            for s in systems:
                r = sub[(sub.system == s) & (sub.metric == metric)]
                if r.empty:
                    cells.append("n/a"); continue
                r = r.iloc[0]
                ci = "" if pd.isna(r.ci_low) else f" ({_f(r.ci_low, r.percent)}-{_f(r.ci_high, r.percent)})"
                cells.append(_f(r.estimate, r.percent) + ci)
            lines.append(f"| {metric} | " + " | ".join(cells) + " |")
        lines.append("")
    if len(pw):
        lines += ["## Paired model comparisons (same scenes; Holm-adjusted)", "", "| Comparison | A - B | Diff | 95% CI | p (Holm) |",
                  "|---|---|---|---|---|"]
        for _, r in pw.iterrows():
            lines.append(f"| {r.comparison} | {r.a} - {r.b} | {_f(r['diff'], True)} | {_f(r.ci_low, True)} to {_f(r.ci_high, True)} | {r.p_holm:.3f} |")
    inv = df[df.get("invented_audio", pd.Series(dtype=float)) == 1] if "invented_audio" in df else pd.DataFrame()
    if len(inv):
        lines += ["", "## Examples: sound answers given for clips with no audio track", "", "| System | Clip | Question | Answer |", "|---|---|---|---|"]
        for _, r in inv.head(25).iterrows():
            lines.append(f"| {r.system} | {r.uid} | {r.qid} | {r.given[:60]} |")
    (RESULTS / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("\nWrote video/results/summary.md, metrics.csv, pairwise.csv, graded.csv, plot.png")


def _plot(m):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    systems = sorted(m.system.unique())
    conds = ["av", "video_only", "shifted", "swapped"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, tag in zip(axes, ["visual", "audio"]):
        for i, s in enumerate(systems):
            r = m[(m.system == s)].set_index("metric").reindex([f"{tag} questions, {c}" for c in conds])
            x = np.arange(len(conds)) + (i - (len(systems) - 1) / 2) * 0.15
            ax.errorbar(x, 100 * r.estimate, yerr=[100 * (r.estimate - r.ci_low).fillna(0), 100 * (r.ci_high - r.estimate).fillna(0)],
                        fmt="o", capsize=3, label=s)
        ax.set_xticks(range(len(conds))); ax.set_xticklabels(conds); ax.set_ylim(0, 105)
        ax.set_title(f"{tag.capitalize()} questions by audio condition"); ax.set_ylabel("Accuracy % (95% CI)"); ax.grid(axis="y", alpha=0.3)
    axes[0].legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(RESULTS / "plot.png", dpi=150)
