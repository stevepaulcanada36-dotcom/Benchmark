"""Aggregates automatic metrics per model with 95% CIs, pairwise WER tests and plots."""
import itertools
import json
from datetime import date

import numpy as np
import pandas as pd

from . import stats
from .generate import ROOT, audio_dir

RESULTS = ROOT / "results"


def _ci(df, col):
    mat = df.pivot_table(index="uid", columns="run", values=col, aggfunc="mean")
    if mat.empty:
        return (np.nan,) * 3 + (0, 0)
    m, lo, hi = stats.cluster_bootstrap(mat.values)
    if mat.shape[0] < 2:          # one item (S5): no between-item CI
        lo = hi = np.nan
    return m, lo, hi, mat.shape[0], mat.shape[1]


def write(cfg, pilot=False):
    d = audio_dir(pilot)
    p = d / "metrics.jsonl"
    if not p.exists():
        raise SystemExit("No metrics yet. Run: python -m audiobench score")
    df = pd.DataFrame([json.loads(l) for l in open(p)]).drop_duplicates("path", keep="last")
    sims = d / "speaker_similarity.json"
    if sims.exists():
        df["spk_sim"] = df.path.map(json.loads(sims.read_text()))
    RESULTS.mkdir(exist_ok=True)
    tag = "pilot" if pilot else "main"
    rows = []
    specs = [("S1", "wer", "WER, read-aloud (lower is better)"),
             ("S2", "s2_pass", "Normalization pass rate (higher is better)"),
             ("S3", "wer", "WER, homograph sentences (ASR cannot hear stress; see listening test)"),
             ("S4", "wer", "WER, expressive scripts with tags removed from reference"),
             ("S5", "wer", "WER, 2,000-character passage"),
             ("ALL", "utmos", "UTMOS predicted MOS (1-5, higher is better)"),
             ("ALL", "spk_sim", "Speaker similarity to reference centroid (higher = same voice)"),
             ("ALL", "sec_per_char", "Seconds of audio per character (speaking rate)"),
             ("ALL", "ttfa_s", "Time to first audio byte, seconds (streaming)")]
    for model, g in df.groupby("model_label"):
        for suite, col, desc in specs:
            sub = g if suite == "ALL" else g[g.suite == suite]
            if col not in sub or sub[col].dropna().empty:
                continue
            m, lo, hi, n, r = _ci(sub.dropna(subset=[col]), col)
            rows.append(dict(model=model, suite=suite, metric=col, description=desc, estimate=m, ci_low=lo,
                             ci_high=hi, n_items=n, runs=r))
        s5 = g[g.suite == "S5"]
        if "chunk_wer" in s5 and len(s5):
            ch = np.array([c for c in s5.chunk_wer if isinstance(c, list)])
            if len(ch):
                worst = ch.mean(axis=0)
                rows.append(dict(model=model, suite="S5", metric="worst_chunk_wer",
                                 description="Highest per-chunk WER in the long passage (drift / skipped text)",
                                 estimate=float(worst.max()), ci_low=np.nan, ci_high=np.nan, n_items=1, runs=len(ch)))
        rows.append(dict(model=model, suite="ALL", metric="credits_used", description="Estimated credits used",
                         estimate=float(g.credits_est.sum()), ci_low=np.nan, ci_high=np.nan,
                         n_items=g.uid.nunique(), runs=int(g.run.max()) + 1))
    m = pd.DataFrame(rows)
    m.to_csv(RESULTS / f"metrics_{tag}.csv", index=False)

    # pairwise WER on S1 (paired by item), Holm-adjusted
    pw = []
    s1 = df[df.suite == "S1"].pivot_table(index="uid", columns="model_label", values="wer", aggfunc="mean")
    for a, b in itertools.combinations(s1.columns, 2):
        dlt, lo, hi, pv = stats.paired_bootstrap_diff(s1[a], s1[b])
        pw.append(dict(model_a=a, model_b=b, wer_diff=dlt, ci_low=lo, ci_high=hi, p=pv))
    pw = pd.DataFrame(pw)
    if len(pw):
        pw["p_holm"] = stats.holm(pw.p.values)
        pw.to_csv(RESULTS / f"pairwise_wer_{tag}.csv", index=False)

    lines = [f"# audio-bench results ({tag})", "", f"Generated {date.today().isoformat()}. ASR: faster-whisper "
             f"{cfg['metrics']['asr_model']}, Whisper English normalizer. 95% CIs: cluster bootstrap over items, runs kept together.", "",
             "| Model | Suite | Metric | Estimate | 95% CI | Items x runs |", "|---|---|---|---|---|---|"]
    for _, r in m.sort_values(["metric", "suite", "model"]).iterrows():
        pct = r.metric in ("wer", "s2_pass", "worst_chunk_wer")
        f = (lambda x: "" if pd.isna(x) else f"{100*x:.1f}%") if pct else (lambda x: "" if pd.isna(x) else f"{x:,.3f}" if abs(x) < 100 else f"{x:,.0f}")
        ci = "" if pd.isna(r.ci_low) else f"{f(r.ci_low)} - {f(r.ci_high)}"
        lines.append(f"| {r.model} | {r.suite} | {r.metric} | {f(r.estimate)} | {ci} | {r.n_items} x {r.runs} |")
    if len(pw):
        lines += ["", "## Pairwise S1 WER differences (paired bootstrap, Holm)", "", "| A - B | Diff | 95% CI | p (Holm) |", "|---|---|---|---|"]
        for _, r in pw.iterrows():
            lines.append(f"| {r.model_a} - {r.model_b} | {100*r.wer_diff:+.2f} pts | {100*r.ci_low:+.2f} to {100*r.ci_high:+.2f} | {r.p_holm:.3f} |")
    fails = df[(df.suite == "S2") & (df.s2_pass == 0)] if "s2_pass" in df else pd.DataFrame()
    if len(fails):
        lines += ["", "## S2 failures to listen to (manual check)", "", "| Model | Item | Run | Transcript |", "|---|---|---|---|"]
        for _, r in fails.sort_values(["uid", "model_label"]).head(60).iterrows():
            lines.append(f"| {r.model_label} | {r.uid} | {r.run} | {r.transcript[:90]} |")
    (RESULTS / f"summary_{tag}.md").write_text("\n".join(lines), encoding="utf-8")
    _plot(m, tag)
    print("\n".join(lines))
    print(f"\nWrote results/summary_{tag}.md, metrics CSV and plot_{tag}.png")


def _plot(m, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    w = m[(m.metric == "wer") & m.suite.isin(["S1", "S3", "S4", "S5"])]
    if w.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    suites = sorted(w.suite.unique()); models = sorted(w.model.unique()); step = 0.8 / len(models)
    for i, mod in enumerate(models):
        s = w[w.model == mod].set_index("suite").reindex(suites)
        x = np.arange(len(suites)) + i * step
        ax.errorbar(x, 100 * s.estimate, yerr=[100 * (s.estimate - s.ci_low), 100 * (s.ci_high - s.estimate)],
                    fmt="o", capsize=3, label=mod)
    ax.set_xticks(np.arange(len(suites)) + step * (len(models) - 1) / 2); ax.set_xticklabels(suites)
    ax.set_ylabel("WER % (95% CI)"); ax.grid(axis="y", alpha=0.3); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(RESULTS / f"plot_{tag}.png", dpi=150)
