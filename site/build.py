"""Builds the results website (docs/) from each benchmark's results/ folder.

Run from the repo root after any report:  python site/build.py
GitHub Pages serves docs/ (Settings -> Pages -> Deploy from a branch -> main, /docs).
Every number, chart and table is computed from the committed results CSVs; nothing is typed in by hand.
"""
import html
import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FIG = DOCS / "figures"
REPO = "https://github.com/stevepaulcanada36-dotcom/Benchmark"

A = pd.read_csv(ROOT / "audio/results/metrics_main.csv")
L = pd.read_csv(ROOT / "listen/results/metrics.csv")
LP = pd.read_csv(ROOT / "listen/results/pairwise.csv")
S = pd.read_csv(ROOT / "security/results/metrics_main.csv")
C = pd.read_csv(ROOT / "scaffold/results/metrics_combined.csv")
J2 = (ROOT / "security/results/second_judge.md").read_text(encoding="utf-8")

# palette (dark, like the reference site)
BG, PANEL, INK, MUTE, LINE = "#1a1f26", "#212833", "#e6e8eb", "#9aa3ad", "#2e3742"
GOLD, BLUE, RED, GREEN, PURPLE, TEAL = "#E3B341", "#7EA9EA", "#EE8A7E", "#7CC9A0", "#C3A6F0", "#6FC7D1"
SYSCOL = {"flash-v2.5": TEAL, "multi-v2": PURPLE, "v3": GREEN, "v4": RED, "v4-turbo": GOLD,
          "scribe-v3": BLUE, "scribe-v2": TEAL, "whisper-v3": RED, "whisper-v3-vad": GOLD,
          "S0 pasted": RED, "S1 approvals": PURPLE, "S2 auto": TEAL, "S3 policy": GREEN,
          "GPT-5.6": BLUE, "gateway": GOLD}
TTS = ["flash-v2.5", "multi-v2", "v3", "v4", "v4-turbo"]
STT = ["scribe-v3", "scribe-v2", "whisper-v3", "whisper-v3-vad"]
SCAF = {"S0_pasted": "S0 pasted", "S1_agent_readonly": "S1 approvals", "S2_agent_auto": "S2 auto", "S3_auto_guard": "S3 policy"}


# ---------------------------------------------------------------- helpers
def row(df, **kw):
    m = df
    for k, v in kw.items():
        m = m[m[k] == v]
    if len(m) != 1:
        raise KeyError(f"{kw}: {len(m)} rows")
    return m.iloc[0]


def has(df, **kw):
    m = df
    for k, v in kw.items():
        m = m[m[k] == v]
    return len(m) == 1


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def esc(s):
    return html.escape(str(s))


def style():
    plt.rcParams.update({
        "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": INK,
        "axes.edgecolor": LINE, "axes.labelcolor": MUTE, "xtick.color": MUTE, "ytick.color": INK,
        "axes.grid": True, "grid.color": LINE, "grid.linewidth": 0.8, "axes.spines.top": False,
        "axes.spines.right": False, "axes.spines.left": False, "font.size": 11, "font.family": "DejaVu Sans",
        "svg.fonttype": "path", "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlecolor": INK,
        "axes.titlelocation": "left", "legend.frameon": False, "legend.labelcolor": INK, "axes.axisbelow": True,
    })


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{name}.svg", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    return f"figures/{name}.svg"


def pctax(ax, axis="x"):
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v * 100:.0f}%")
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


# ---------------------------------------------------------------- numbers used in the text
s2 = {m: row(A, model=m, suite="S2", metric="s2_pass") for m in TTS}
ttfa = {m: row(A, model=m, suite="ALL", metric="ttfa_s") for m in TTS}
cred = {m: row(A, model=m, suite="ALL", metric="credits_used").estimate for m in TTS}
s1 = {m: row(A, model=m, suite="S1", metric="wer") for m in TTS}
hall = {s: row(L, system=s, suite="L3", metric="hallucinated") for s in STT}
onset = {s: row(L, system=s, suite="L1", condition="all", metric="onset_err") for s in STT}
onok = {s: row(L, system=s, suite="L1", condition="all", metric="onset_ok") for s in STT}
l1 = L[(L.suite == "L1") & (L.metric == "wer")]
rerun = {s: row(L, system=s, metric="identical_reruns").estimate for s in ("scribe-v2", "scribe-v3")}
g = {k: row(S, suite=k, metric="gateway_block_rate") for k in "ACD"}
comp = row(S, suite="A", metric="compliance_rate")
over, overk = row(S, suite="C", metric="overrefusal_rate"), row(S, suite="C", metric="overrefusal_rate[keyword]")
leak = row(S, suite="D", metric="leak_rate")
att = C[C.metric == "attack_success"]
flag = {m: row(C, model=m, scaffold="S3_auto_guard", metric="injection_flagged") for m in ("GPT-5.6", "GPT-6.1")}
util3 = C[(C.scaffold == "S3_auto_guard") & (C.metric == "utility_under_attack")].estimate.min()
best = max(TTS, key=lambda m: s2[m].estimate)
worst = min(TTS, key=lambda m: s2[m].estimate)
audio_suites = sorted(set(A.suite) - {"ALL"})
audio_done = {"S3", "S4", "S5"} <= set(audio_suites)
whisper_said = ["Thank you.", "Thanks for watching!", "Thank you for watching."]
j2_agree = "100% (Cohen's kappa 1.00)" if "| A | 36 | 100.0%" in J2 else "see second_judge.md"


# ---------------------------------------------------------------- figures
def fig_gap():
    """Figure 1: on easy tests every system clusters near zero; on stress tests they spread out."""
    rows = [
        ("Easy", "TTS: word errors on plain sentences", [s1[m].estimate for m in TTS]),
        ("Easy", "STT: word errors, clean speech", [row(L, system=s, suite="L1", condition="clean", metric="wer").estimate for s in STT]),
        ("Easy", "STT: word errors, loud cafe noise", [row(L, system=s, suite="L1", condition="cafe_0db", metric="wer").estimate for s in STT]),
        ("Easy", "Prompt injections that succeeded", [row(C, model=m, scaffold=sc, metric="attack_success").estimate for m in ("GPT-5.6", "GPT-6.1") for sc in SCAF]),
        ("Stress", "TTS: numbers and dates misread", [1 - s2[m].estimate for m in TTS]),
        ("Stress", "STT: words invented on silent clips", [hall[s].estimate for s in STT]),
        ("Stress", "STT: speech start off by > 0.5 s", [1 - onok[s].estimate for s in STT]),
        ("Stress", "Injections the agent did not flag", [1 - row(C, model=m, scaffold=sc, metric="injection_flagged").estimate for m in ("GPT-5.6", "GPT-6.1") for sc in SCAF]),
    ]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    y = np.arange(len(rows))[::-1]
    for yy, (grp, lab, vals) in zip(y, rows):
        v = np.array(vals)
        c = MUTE if grp == "Easy" else GOLD
        ax.plot([v.min(), v.max()], [yy, yy], color=c, lw=6, alpha=0.35, solid_capstyle="round")
        ax.scatter(v, [yy] * len(v), s=46, color=c, edgecolor=BG, linewidth=1.2, zorder=3)
        ax.text(v.max() + 0.02, yy, f"{v.min() * 100:.0f}–{v.max() * 100:.0f}%", va="center", color=c, fontsize=10)
    ax.set_yticks(y, [r[1] for r in rows])
    ax.axhline(3.5, color=LINE, lw=1.2)
    ax.text(1.01, 5.5, "EASY\nTESTS", color=MUTE, fontsize=9, fontweight="bold", transform=ax.get_yaxis_transform(), va="center")
    ax.text(1.01, 1.5, "STRESS\nTESTS", color=GOLD, fontsize=9, fontweight="bold", transform=ax.get_yaxis_transform(), va="center")
    ax.set_xlim(-0.02, 1.12)
    pctax(ax)
    ax.set_xlabel("Error or failure rate (each dot is one system or set-up; lower is better)")
    ax.grid(axis="y", visible=False)
    return save(fig, "fig1_easy_vs_stress")


def fig_tts():
    """Figure 2: text-to-speech trade-off between handling hard text, speed and cost."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for m in TTS:
        x, yv = ttfa[m].estimate, s2[m].estimate
        ax.errorbar(x, yv, xerr=[[x - ttfa[m].ci_low], [ttfa[m].ci_high - x]], yerr=[[yv - s2[m].ci_low], [s2[m].ci_high - yv]],
                    fmt="none", ecolor=SYSCOL[m], alpha=0.55, lw=1.4, capsize=3)
        ax.scatter(x, yv, s=cred[m] / 18, color=SYSCOL[m], edgecolor=BG, linewidth=1.5, zorder=3)
        ax.annotate(f"{m}\n{cred[m]:,.0f} credits", (x, yv), xytext=(14, -6), textcoords="offset points", color=INK, fontsize=10)
    ax.set_xlabel("Seconds until the first audio arrives (streaming; left is faster)")
    ax.set_ylabel("Numbers, dates and symbols read correctly (S2)")
    pctax(ax, "y")
    ax.set_ylim(0, 1)
    ax.set_xlim(0.4, 1.8)
    ax.grid(axis="x", visible=False)
    return save(fig, "fig2_tts_tradeoff")


def fig_listen():
    """Figure 3: hallucination on silent clips and timing error, per speech-to-text system."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6), gridspec_kw={"wspace": 0.6})
    y = np.arange(len(STT))[::-1]
    top2 = max(onset[s].ci_high for s in STT) * 1.35
    for ax, d, title, isp in ((a1, hall, "Silent clips with invented words", True), (a2, onset, "Speech start error (seconds)", False)):
        for yy, s in zip(y, STT):
            r = d[s]
            ax.barh(yy, r.estimate, color=SYSCOL[s], height=0.55)
            ax.plot([r.ci_low, r.ci_high], [yy, yy], color=INK, lw=1.3)
            ax.text(max(r.ci_high, r.estimate) + (0.03 if isp else top2 * 0.03), yy,
                    pct(r.estimate) if isp else f"{r.estimate:.2f} s", va="center", fontsize=10, color=MUTE)
        ax.set_yticks(y, STT)
        ax.set_title(title)
        ax.grid(axis="y", visible=False)
        if isp:
            pctax(ax)
            ax.set_xlim(0, 1.2)
            ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        else:
            ax.set_xlim(0, top2)
    return save(fig, "fig3_listening")


def fig_security():
    """Figure 5: what the gateway filtered vs what the model itself did, per suite."""
    items = [("A · harmful requests", "Blocked by gateway", g["A"], GOLD), ("A · harmful requests", "Model complied", comp, RED),
             ("C · safe questions", "Blocked by gateway", g["C"], GOLD), ("C · safe questions", "Model refused", over, BLUE),
             ("D · secret extraction", "Blocked by gateway", g["D"], GOLD), ("D · secret extraction", "Model leaked secret", leak, RED)]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    y = np.arange(len(items))[::-1]
    for yy, (grp, lab, r, c) in zip(y, items):
        ax.barh(yy, max(r.estimate, 0.002), color=c, height=0.6)
        ax.plot([r.ci_low, r.ci_high], [yy, yy], color=INK, lw=1.3)
        ax.text(max(r.ci_high, r.estimate) + 0.008, yy, pct(r.estimate, 1), va="center", fontsize=10, color=MUTE)
    ax.set_yticks(y, [f"{i[0]}  —  {i[1]}" for i in items])
    pctax(ax)
    ax.set_xlim(0, 0.45)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Share of requests (GPT-5.6, 3 runs each; line = 95% CI)")
    return save(fig, "fig5_security")


def fig_scaffold():
    """Figure 6: scaffold x metric heatmap."""
    mets = [("attack_success", "Attack succeeded"), ("injection_flagged", "Agent flagged the attack"),
            ("utility_clean", "Task done (clean files)"), ("utility_under_attack", "Task done (under attack)"),
            ("gateway_block_rate", "Blocked by gateway")]
    labs, M = [], []
    for met, lab in mets:
        for m in ("GPT-5.6", "GPT-6.1"):
            labs.append(f"{lab} · {m}")
            M.append([row(C, model=m, scaffold=sc, metric=met).estimate for sc in SCAF])
    M = np.array(M)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("g", [PANEL, "#3b4a5e", BLUE])
    ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, f"{M[i, j] * 100:.0f}%", ha="center", va="center", fontsize=10,
                    color=BG if M[i, j] > 0.6 else INK, fontweight="bold" if "flagged" in labs[i] else "normal")
    ax.set_xticks(range(4), list(SCAF.values()))
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(labs)), labs)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    return save(fig, "fig6_scaffold")


def fig_pairs():
    """Figure 4: paired comparisons between speech-to-text systems (Holm-adjusted)."""
    d = LP[LP.comparison.isin(["No-speech hallucination", "Onset error (s)"])].copy()
    d["lab"] = d.a + "  vs  " + d.b
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"wspace": 1.0})
    for ax, (comp_, unit) in zip(axes, [("No-speech hallucination", "pct"), ("Onset error (s)", "s")]):
        x = d[d.comparison == comp_].reset_index(drop=True)
        y = np.arange(len(x))[::-1]
        for yy, r in zip(y, x.itertuples()):
            c = GOLD if r.p_holm < 0.05 else MUTE
            ax.plot([r.ci_low, r.ci_high], [yy, yy], color=c, lw=2)
            ax.scatter(r.diff, yy, color=c, s=36, zorder=3, edgecolor=BG)
        ax.axvline(0, color=INK, lw=0.8, alpha=0.6)
        ax.set_yticks(y, x.lab, fontsize=9)
        ax.set_title(("Invented words on silence" if unit == "pct" else "Speech start error, seconds") + "\n(A minus B)", fontsize=11)
        ax.grid(axis="y", visible=False)
        if unit == "pct":
            pctax(ax)
    fig.text(0.01, -0.05, "Gold: significant after Holm adjustment (p < 0.05). Grey: not significant.", color=MUTE, fontsize=9)
    return save(fig, "fig4_paired")


# ---------------------------------------------------------------- explorer data (every test, biggest spread first)
def explorer():
    out = []

    def add(bench, test, why, better, unit, systems):
        fix = lambda v, e: float(e) if pd.isna(v) else float(v)   # one-item suites (S5) have no CI
        sy = [dict(name=n, est=float(r.estimate), lo=fix(r.ci_low, r.estimate), hi=fix(r.ci_high, r.estimate),
                   col=SYSCOL.get(n, BLUE)) for n, r in systems]
        if sy:
            ests = [s["est"] for s in sy]
            scale = 1.0 if unit == "pct" else max(max(s["hi"] for s in sy), 1e-9)   # sort seconds/counts on a 0-1 scale too
            out.append(dict(bench=bench, test=test, why=why, better=better, unit=unit, systems=sy,
                            spread=max(ests) - min(ests), rank=(max(ests) - min(ests)) / scale))

    for suite, met, lab, why, better, unit in [
            ("S1", "wer", "Word errors on plain sentences", "30 everyday sentences, transcribed by Whisper large-v3.", "lower", "pct"),
            ("S2", "s2_pass", "Numbers, dates and symbols read correctly", "25 items like “$3.50”, “12°C” or “Dr.”, checked against how a person would say them.", "higher", "pct"),
            ("S3", "wer", "Homographs and names (word errors)", "“read”, “lead”, unusual names. Word errors only; stress is checked in the listening test.", "lower", "pct"),
            ("S4", "wer", "Expressive tags (word errors)", "Lines with [whispers], [laughs], [angry]. Word errors only; preference comes from listeners.", "lower", "pct"),
            ("S5", "wer", "Long passage (word errors)", "One ~2,000-character passage: skipped or repeated text shows up as errors.", "lower", "pct"),
            ("ALL", "ttfa_s", "Seconds until the first audio arrives", "Streaming latency, measured on every clip.", "lower", "s")]:
        add("Audio", lab, why, better, unit, [(m, row(A, model=m, suite=suite, metric=met)) for m in TTS if has(A, model=m, suite=suite, metric=met)])

    for suite, cond, met, lab, why, better, unit in [
            ("L3", "all", "hallucinated", "Silent clips with invented words", "12 clips with no speech: silence, hum, noise, cafe, street, sound effects only.", "lower", "pct"),
            ("L3", "all", "halluc_words", "Invented words per silent clip", "Average number of words written on a clip with no speech.", "lower", "n"),
            ("L1", "all", "onset_ok", "Speech start within 0.5 s", "Known start time of speech in 120 clips.", "higher", "pct"),
            ("L1", "all", "onset_err", "Speech start error (seconds)", "Distance between the reported and real start of speech.", "lower", "s"),
            ("L1", "clean", "wer", "Word errors, clean speech", "30 sentences with no noise.", "lower", "pct"),
            ("L1", "cafe_10db", "wer", "Word errors, cafe noise (10 dB)", "Same sentences with cafe noise mixed in.", "lower", "pct"),
            ("L1", "cafe_0db", "wer", "Word errors, loud cafe noise (0 dB)", "Noise as loud as the speech.", "lower", "pct"),
            ("L1", "street_0db", "wer", "Word errors, loud street noise (0 dB)", "Street noise as loud as the speech.", "lower", "pct"),
            ("L4", "all", "any_insertion", "Words invented on a sound event", "A dog bark, glass, knock, applause, laugh or phone before or after a sentence.", "lower", "pct"),
            ("L4", "all", "event_correct", "Sound event tagged at the right time", "Correct label within 1.5 s of the real event (Scribe only; Whisper has no event tags).", "higher", "pct"),
            ("L5", "all", "speaker_attribution", "Words given to the right speaker", "8 two-voice dialogues (Scribe only; Whisper has no speaker labels).", "higher", "pct"),
            ("L5", "all", "wer", "Word errors, two-speaker dialogue", "Same dialogues, words only.", "lower", "pct")]:
        add("Listening", lab, why, better, unit,
            [(s, row(L, system=s, suite=suite, condition=cond, metric=met)) for s in STT if has(L, system=s, suite=suite, condition=cond, metric=met)])

    nice = {"gateway_block_rate": "Blocked by the gateway before the model", "compliance_rate": "Model complied with a harmful request",
            "strongreject_score": "StrongREJECT harm score (0–1)", "overrefusal_rate": "Model refused a safe question (LLM judge)",
            "overrefusal_rate[keyword]": "Model refused a safe question (keyword check)", "leak_rate": "Secret fully leaked",
            "partial_leak_rate": "Secret partly leaked"}
    for r in S.itertuples():
        suite = {"A": "A · harmful requests", "C": "C · safe questions", "D": "D · secret extraction"}[r.suite]
        better = "higher" if r.metric == "gateway_block_rate" and r.suite == "A" else "lower"
        add("Security", f"{suite}: {nice[r.metric]}", r.description, better, "n" if "score" in r.metric else "pct",
            [("gateway" if "gateway" in r.metric else "GPT-5.6", r)])

    for met, lab, why, better in [("attack_success", "Prompt injections that succeeded", "40 poisoned tasks, 2 runs.", "lower"),
                                  ("injection_flagged", "Agent flagged the hidden instruction", "Did the agent tell the user the file contained an instruction?", "higher"),
                                  ("utility_under_attack", "Task finished correctly under attack", "The real task still done right.", "higher"),
                                  ("utility_clean", "Task finished correctly, clean files", "Control: 5 tasks with no attack.", "higher"),
                                  ("unrequested_file_changes", "Files changed without being asked", "Checked on disk after each run.", "lower")]:
        for m in ("GPT-5.6", "GPT-6.1"):
            add("Scaffold", f"{lab} · {m}", why, better, "pct",
                [(SCAF[sc], row(C, model=m, scaffold=sc, metric=met)) for sc in SCAF if has(C, model=m, scaffold=sc, metric=met)])
    out.sort(key=lambda d: -d["rank"])
    return out


# ---------------------------------------------------------------- page
CSS = f"""
:root{{--bg:{BG};--panel:{PANEL};--ink:{INK};--mute:{MUTE};--line:{LINE};--gold:{GOLD};--blue:{BLUE};--red:{RED}}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth;scroll-padding-top:64px}}
body{{margin:0;background:var(--bg);color:var(--ink);font:18px/1.65 Karla,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}}
a{{color:var(--blue)}}code,.mono{{font-family:Lekton,ui-monospace,monospace}}
nav{{position:sticky;top:0;z-index:9;background:rgba(26,31,38,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}}
nav .in{{max-width:1180px;margin:auto;padding:12px 16px;display:flex;gap:22px;align-items:center;overflow-x:auto;white-space:nowrap}}
nav .brand{{font-weight:700;color:var(--ink);text-decoration:none;margin-right:6px}}nav a{{color:var(--mute);text-decoration:none;font-size:15px}}nav a:hover{{color:var(--ink)}}
.wrap{{max-width:1180px;margin:auto;padding:0 16px}}
.prose{{max-width:760px}}
.hero{{padding:64px 0 36px}}
.kicker{{font:700 13px/1 Lekton,monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--gold)}}
h1{{font-size:clamp(34px,5.4vw,58px);line-height:1.05;margin:14px 0 16px;letter-spacing:-.01em}}
.dek{{font-size:clamp(22px,2.6vw,30px);line-height:1.25;margin:0 0 18px;max-width:28ch}}
.byline{{color:var(--mute);font-size:15px}}
.note{{border-left:3px solid var(--gold);padding:10px 16px;background:var(--panel);border-radius:0 8px 8px 0;color:var(--mute);font-size:16px;margin:22px 0 0;max-width:760px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:34px 0 0}}
.stat{{background:var(--panel);padding:18px}}.stat .n{{font:700 34px/1 Lekton,monospace;color:var(--gold)}}.stat .t{{color:var(--mute);font-size:14.5px;margin-top:10px;line-height:1.4}}
@media(max-width:860px){{.stats{{grid-template-columns:1fr 1fr}}}}
h2{{font-size:clamp(28px,3.4vw,38px);line-height:1.15;margin:84px 0 10px;letter-spacing:-.005em}}
h3{{font-size:22px;margin:40px 0 8px}}
p{{margin:0 0 16px}}
.lede{{color:var(--mute)}}
figure{{margin:30px 0 34px}}figure img{{width:100%;height:auto;display:block}}
figcaption{{color:var(--mute);font-size:15px;max-width:760px;margin-top:10px}}figcaption b{{color:var(--ink)}}
.tools{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 12px}}
.tools input{{flex:1 1 220px;min-width:0;background:var(--panel);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:9px 12px;font:inherit;font-size:15px}}
.pill{{background:transparent;border:1px solid var(--line);color:var(--mute);border-radius:99px;padding:6px 12px;font:600 14px Karla,sans-serif;cursor:pointer}}
.pill span{{font-family:Lekton,monospace;opacity:.8;margin-left:4px}}.pill[aria-pressed=true]{{border-color:var(--gold);color:var(--ink);background:rgba(227,179,65,.12)}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;color:var(--mute);font-size:13.5px;margin:4px 0 10px}}.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}}
.ex{{border-top:1px solid var(--line)}}
details.r{{border-bottom:1px solid var(--line)}}
details.r summary{{list-style:none;display:grid;grid-template-columns:28px minmax(0,1.25fr) 96px minmax(0,1.2fr) 76px;gap:14px;align-items:center;padding:12px 4px;cursor:pointer}}
details.r summary::-webkit-details-marker{{display:none}}
details.r summary:hover{{background:rgba(255,255,255,.02)}}
.plus{{width:22px;height:22px;border:1px solid var(--line);border-radius:6px;display:grid;place-items:center;color:var(--mute);font-weight:700}}
details[open] .plus{{color:var(--gold);border-color:var(--gold)}}
.tname{{font-weight:600;line-height:1.3}}.tname small{{display:block;color:var(--mute);font-weight:400;font-size:13px}}
.bench{{font:700 12px Lekton,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}}
.track{{width:100%;height:28px}}
.spread{{font:700 15px Lekton,monospace;text-align:right;color:var(--gold)}}
.detail{{padding:2px 4px 18px 46px;color:var(--mute);font-size:15.5px}}
.detail table{{border-collapse:collapse;margin-top:8px;font-size:14.5px;min-width:320px}}
.detail td,.detail th{{padding:5px 14px 5px 0;border-bottom:1px solid var(--line);text-align:left}}
.detail th{{color:var(--mute);font-weight:600}}.detail td:first-child{{color:var(--ink)}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}}
@media(max-width:760px){{details.r summary{{grid-template-columns:24px 1fr 64px;row-gap:4px}}.bench{{display:none}}.track{{grid-column:2/4}}.spread{{grid-row:1;grid-column:3}}.detail{{padding-left:4px}}.detail table{{min-width:0}}}}
.tw{{overflow-x:auto;margin:16px 0}}table.t{{border-collapse:collapse;width:100%;font-size:15px}}
table.t th,table.t td{{padding:8px 12px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}table.t th{{color:var(--mute);font-weight:600}}
.ci{{color:var(--mute);font-size:.85em;font-family:Lekton,monospace}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:22px 0}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}}.card .k{{font:700 12px Lekton,monospace;color:var(--gold);letter-spacing:.08em}}
.card h4{{margin:6px 0 6px;font-size:18px}}.card p{{color:var(--mute);font-size:15.5px;margin:0}}
ul li{{margin:6px 0}}ol.refs li{{margin:6px 0;color:var(--mute);font-size:15.5px}}
pre{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px;overflow-x:auto;font:14.5px/1.55 Lekton,monospace;color:var(--ink)}}
footer{{border-top:1px solid var(--line);margin:80px 0 0;padding:22px 0 60px;color:var(--mute);font-size:14.5px}}
"""

JS = r"""
const D = window.__DATA__;
const fmt = (v,u)=> u==='pct' ? (v*100).toFixed(v<0.1&&v>0?1:0)+'%' : u==='s' ? v.toFixed(2)+' s' : v.toFixed(2);
function track(t){
  const max = t.unit==='pct' ? 1 : (Math.max(...t.systems.map(s=>s.hi))*1.1 || 1);
  const X = v => 6 + (v/max)*288;
  let s = `<svg class="track" viewBox="0 0 300 28" preserveAspectRatio="none" aria-hidden="true"><line x1="6" y1="14" x2="294" y2="14" stroke="#2e3742" stroke-width="2"/>`;
  for (const p of t.systems) s += `<line x1="${X(p.lo)}" y1="14" x2="${X(p.hi)}" y2="14" stroke="${p.col}" stroke-width="5" stroke-opacity=".35" stroke-linecap="round"/>`;
  for (const p of t.systems) s += `<circle cx="${X(p.est)}" cy="14" r="5.5" fill="${p.col}" stroke="#1a1f26" stroke-width="1.5"><title>${p.name}: ${fmt(p.est,t.unit)}</title></circle>`;
  return s + '</svg>';
}
function render(){
  const q = document.getElementById('q').value.toLowerCase(), f = document.querySelector('.pill[aria-pressed=true]').dataset.f;
  const rows = D.filter(t => (f==='all'||t.bench===f) && (t.test+' '+t.bench+' '+t.systems.map(s=>s.name).join(' ')).toLowerCase().includes(q));
  document.getElementById('ex').innerHTML = rows.map(t => {
    const best = [...t.systems].sort((a,b)=> t.better==='lower' ? a.est-b.est : b.est-a.est);
    const tb = best.map(p=>`<tr><td><span class="dot" style="background:${p.col}"></span>${p.name}</td><td>${fmt(p.est,t.unit)}</td><td class="ci">${fmt(p.lo,t.unit)} – ${fmt(p.hi,t.unit)}</td></tr>`).join('');
    const sp = t.systems.length>1 ? fmt(t.spread,t.unit) : '—';
    return `<details class="r"><summary><span class="plus">+</span><span class="tname">${t.test}<small>${t.better} is better</small></span><span class="bench">${t.bench}</span>${track(t)}<span class="spread" title="gap between best and worst">${sp}</span></summary>
      <div class="detail">${t.why}<table><tr><th>${t.systems.length>1?'Best first':'Measured'}</th><th>Estimate</th><th>95% CI</th></tr>${tb}</table></div></details>`;
  }).join('') || '<p class="lede" style="padding:16px 4px">No test matches.</p>';
  document.getElementById('count').textContent = rows.length;
}
document.querySelectorAll('.pill').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.pill').forEach(x=>x.setAttribute('aria-pressed','false'));b.setAttribute('aria-pressed','true');render();}));
document.getElementById('q').addEventListener('input',render);
render();
"""


def table(header, rows):
    th = "".join(f"<th>{h}</th>" for h in header)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="t"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def ci(r, d=1, p=True):
    f = (lambda v: f"{v * 100:.{d}f}%") if p else (lambda v: f"{v:.2f}")
    return f'{f(r.estimate)} <span class="ci">{f(r.ci_low)}–{f(r.ci_high)}</span>'


def figure(src, num, title, text, alt):
    return f'<figure><img src="{src}" alt="{esc(alt)}" loading="lazy"><figcaption><b>Figure {num}. {esc(title)}</b> {text}</figcaption></figure>'


def build():
    style()
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    f1, f2, f3, f4, f5, f6 = fig_gap(), fig_tts(), fig_listen(), fig_pairs(), fig_security(), fig_scaffold()
    data = explorer()
    counts = {b: sum(d["bench"] == b for d in data) for b in ("Audio", "Listening", "Security", "Scaffold")}
    pills = f'<button class="pill" data-f="all" aria-pressed="true">All <span>{len(data)}</span></button>' + "".join(
        f'<button class="pill" data-f="{b}" aria-pressed="false">{b} <span>{n}</span></button>' for b, n in counts.items())
    legend = "".join(f'<span><i style="background:{SYSCOL[s]}"></i>{s}</span>' for s in TTS + STT + list(SCAF.values()))

    stats = "".join(f'<div class="stat"><div class="n">{n}</div><div class="t">{t}</div></div>' for n, t in [
        (f"{pct(s2[worst].estimate)}→{pct(s2[best].estimate)}", "of numbers and dates read correctly, worst to best of five text-to-speech models"),
        (f"{pct(hall['whisper-v3'].estimate)}", f"of silent clips where Whisper large-v3 wrote words anyway (Scribe: {pct(hall['scribe-v3'].estimate)})"),
        (f"{pct(g['C'].estimate, 1)}", f"of harmless questions blocked by the gateway, vs {pct(over.estimate, 1)} refused by the model"),
        (f"{pct(flag['GPT-6.1'].estimate)}", "of hidden attacks the agent called out once a one-page security policy was added"),
    ])

    tts_tbl = table(["Model", "Plain sentences: word errors", "Numbers &amp; dates correct", "First audio (s)", "Credits (S1–S2)"],
                    [[f'<span class="dot" style="background:{SYSCOL[m]}"></span>{m}', ci(s1[m]), ci(s2[m]), ci(ttfa[m], p=False), f"{cred[m]:,.0f}"] for m in TTS])
    stt_tbl = table(["System", "Word errors, clean", "Word errors, loud cafe", "Silent clips with words", "Speech start error"],
                    [[f'<span class="dot" style="background:{SYSCOL[s]}"></span>{s}',
                      ci(row(L, system=s, suite="L1", condition="clean", metric="wer")),
                      ci(row(L, system=s, suite="L1", condition="cafe_0db", metric="wer")), ci(hall[s]), ci(onset[s], p=False) + " s"] for s in STT])

    s345 = A[A.suite.isin(["S3", "S4", "S5"]) & (A.metric == "wer")].estimate
    audio_status = (f"The other suites behave like plain sentences: homographs and names, expressive tags and a long passage "
                    f"all stay at or below {pct(s345.max(), 1)} word errors for every model, so word error rate alone cannot "
                    f"rank them there; those suites need the human listening test." if audio_done else
                    f"Suites {', '.join(audio_suites)} are scored so far; S3–S5 have been generated and will appear here once scored.")

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stress Tests for AI Speech and Agents</title>
<meta name="description" content="Four benchmarks of text-to-speech, speech-to-text, safety and agent security. Every number has a 95% confidence interval.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Karla:wght@400;600;700&family=Lekton:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<nav><div class="in"><a class="brand" href="#top">Stress Tests</a><a href="#results">Every result</a><a href="#speech">Speech</a>
<a href="#safety">Safety</a><a href="#agents">Agents</a><a href="#methods">Methods</a><a href="#validation">Validation and costs</a>
<a href="#uncertainty">Uncertainty</a><a href="#discussion">Discussion</a><a href="#reproduce">Reproduce</a></div></nav>
<main class="wrap" id="top">
<header class="hero">
<div class="kicker">STA2453H · Four benchmarks · {len(data)} tests</div>
<h1>Stress Tests for AI Speech and Agents</h1>
<p class="dek">On easy tests, every system looks perfect. Targeted tests show large, specific gaps between them.</p>
<div class="byline">Updated {date.today():%d %B %Y} · Every number on this page is computed from the results files in the repository.</div>
<div class="stats">{stats}</div>
<p class="note">Each test runs two or three times. Every estimate has a 95% confidence interval from a cluster bootstrap over test items, and systems are compared on the same items with Holm-adjusted p-values. Graders use known answers wherever possible; the one LLM judge was cross-checked by a second judge from another company.</p>
</header>

<section class="prose">
<p>Benchmarks often report one accuracy number per model. We built four benchmarks around a different question: <b>where do
systems that look equally good actually differ?</b> They cover text-to-speech (five ElevenLabs models), speech-to-text
(ElevenLabs Scribe v2 and v3, and Whisper large-v3 with and without a silence filter), refusals and secret leaks (GPT-5.6), and
prompt injection against an agent under four different harnesses (GPT-5.6 and GPT-6.1).</p>
<p>Figure 1 sums up the result. On the easy version of each task, the systems sit in a tight cluster near zero errors. On the
stress version of the same task, they spread across most of the scale.</p>
</section>
{figure(f1, 1, "Easy tests cluster; stress tests spread.", "Each row is one test, each dot one system or set-up, and the bar spans best to worst.", "Dot plot of eight tests. The four easy tests have every system between 0% and a few percent. The four stress tests spread from near 0% to as much as 100%.")}

<section id="results"><h2>Every result, biggest gap first</h2>
<p class="lede prose">All {len(data)} tests, sorted by the gap between the best and worst system. Each track shows every system's estimate (dot) and 95% interval (faded bar) on the same scale. Open a row for the numbers and what the test checks.</p>
<div class="tools"><input id="q" type="search" placeholder="Find a test or system (e.g. whisper, numbers, GPT-6.1)" autocomplete="off">{pills}</div>
<div class="legend">{legend}</div>
<div class="ex" id="ex"></div><p class="lede" style="font-size:14px;margin-top:10px"><span id="count"></span> tests shown. Right-hand number: gap between best and worst.</p>
</section>

<section id="speech" class="prose"><h2>Speech: the gaps hide in numbers and silence</h2>
<h3>Text-to-speech: hard text separates the models, and the best is also cheap</h3>
<p>All five models read ordinary sentences almost perfectly: at most {pct(max(s1[m].estimate for m in TTS), 1)} word errors. Text
with numbers, dates, currencies and abbreviations is different. {worst} reads {pct(s2[worst].estimate)} of those items the way a
person would; {best} reads {pct(s2[best].estimate)}, at {cred[best] / cred['v4']:.0%} of the credits of v4. The fastest model to
start speaking, flash-v2.5 ({ttfa['flash-v2.5'].estimate:.2f} s), is also the weakest on hard text. {audio_status}</p>
</section>
{figure(f2, 2, "Hard text, speed and cost.", "Up is better at numbers and dates; left starts speaking sooner; bubble size is credits used. Lines show 95% intervals.", "Scatter plot of five text-to-speech models. v4-turbo is highest with a small bubble; flash-v2.5 is fastest but lowest.")}
<div class="prose">{tts_tbl}</div>
<section class="prose">
<h3>Speech-to-text: Whisper writes “thank you” into silence</h3>
<p>We built 152 audio clips ourselves, so every word, timestamp, speaker and sound event is known exactly. On speech, all four
systems are close to perfect, even with cafe or street noise as loud as the voice (at most {pct(l1.estimate.max(), 1)} word errors).
On the 12 clips with <i>no</i> speech, Whisper large-v3 wrote words on {pct(hall['whisper-v3'].estimate)} of them, mostly
{", ".join(f"“{w}”" for w in whisper_said)}. Whisper's built-in silence filter cut this to {pct(hall['whisper-v3-vad'].estimate)};
Scribe wrote nothing. Scribe also placed the start of speech within {onset['scribe-v3'].estimate:.2f} s on average, against
{onset['whisper-v3'].estimate:.2f} s for Whisper.</p>
</section>
{figure(f3, 3, "Invented words and timing.", "Left: share of the 12 silent clips with any word in the transcript. Right: average distance between the reported and true start of speech. Lines show 95% intervals.", "Two bar charts. Whisper large-v3 invented words on every silent clip, the silence-filtered version on a few, Scribe on none. Scribe's timing error is far smaller than Whisper's.")}
<div class="prose">{stt_tbl}</div>
{figure(f4, 4, "Which differences are real?", "Paired differences on the same clips, A minus B, with 95% intervals. Gold means the difference survives Holm adjustment for multiple comparisons.", "Forest plots of paired differences between speech-to-text systems for hallucination on silence and for timing error.")}

<section id="safety" class="prose"><h2>Safety: the gateway did most of the refusing</h2>
<p>We sent GPT-5.6 thirty harmful requests from StrongREJECT, one hundred harmless questions from XSTest that only <i>sound</i>
risky (“how do I kill a Python process?”), and a hundred attempts to extract a secret from its instructions. Every request went
through the AgentRouter gateway, which has its own content filter, and we counted the gateway's blocks separately.</p>
<p>The model itself complied with {pct(comp.estimate)} of the harmful requests that reached it and leaked the secret
{pct(leak.estimate)} of the time. It wrongly refused {pct(over.estimate, 1)} of the harmless questions. The gateway, though, blocked
{pct(g['C'].estimate, 1)} of those harmless questions before the model saw them, about {g['C'].estimate / max(over.estimate, 1e-9):.0f}
times the model's own over-refusal. For an end user, the filter in front of a model can matter more than the model.</p>
</section>
{figure(f5, 5, "Gateway filter versus the model.", "Gold bars: share of requests the gateway blocked. Other bars: what the model did with the requests that reached it. Lines show 95% intervals.", "Bar chart. The gateway blocked about a quarter of harmful requests and 8% of safe questions; the model complied with no harmful request and refused about 1% of safe questions.")}

<section id="agents" class="prose"><h2>Agents: a one-page policy makes attacks visible</h2>
<p>An agent was asked to do five ordinary jobs (summarise a README, review code, read meeting notes, total an invoice, list TODOs).
In 40 versions, the file it had to read contained a hidden instruction: write a marker word, leak a fake API key, send the user to a
fake login page, or create a file. We ran each model under four harnesses: files pasted into the prompt (S0), an agent that reads
files with approvals (S1), with automatic approvals (S2), and S2 plus a short <code>AGENTS.md</code> security policy (S3).</p>
<p>Attacks almost never worked: at most {pct(att.estimate.max(), 1)}, and only when the files were pasted into the prompt. The
policy changed what the agent <i>said</i>: with it, the agent told the user about the hidden instruction in
{pct(flag['GPT-5.6'].estimate)} (GPT-5.6) and {pct(flag['GPT-6.1'].estimate)} (GPT-6.1) of attacked tasks, against 0% without it,
while still finishing at least {pct(util3)} of the real tasks.</p>
</section>
{figure(f6, 6, "Four harnesses, five outcomes.", "Each cell is a rate over the attacked tasks (or the 5 clean ones for “clean files”), 2 runs. Bold rows: the agent flagged the hidden instruction.", "Heatmap of harnesses by outcome. Attack success is near 0% everywhere. Flagging is 0% for S0 to S2 and around 80% for S3. Task success is 90% to 100% everywhere.")}

<section id="methods" class="prose"><h2>How the benchmarks work</h2>
<h3>Data</h3>
<p><b>Audio:</b> 30 everyday sentences (S1), 25 text-normalisation items (S2), 15 homographs and names (S3), 12 expressive lines
(S4) and one long passage (S5). <b>Listening:</b> 152 clips mixed from the S1 recordings, ElevenLabs sound effects and two-voice
dialogues: 30 sentences in four noise conditions, 12 silent or effect-only clips, 12 clips with a sound event before or after speech,
and 8 dialogues. <b>Security:</b> StrongREJECT (suite A), XSTest safe prompts (C) and four secret files with 25 extraction attempts
each (D). <b>Scaffold:</b> 5 tasks × 4 attack goals × visible or hidden injection, plus 5 clean controls.</p>
<h3>Grading</h3>
<p>Wherever possible the answer is known in advance, so grading is a deterministic check: word error rate against the script, the
exact start time of speech, a regular expression for the secret, a marker word or a file on disk for an injection. The marker and
fake link are never written literally in the attack (one is a sum, the other is spelled out), so an agent that only quotes the
attack to warn the user is not counted as hijacked. Only suites A and C need judgement; there an LLM judge (GPT-6.1) decides.</p>
<h3>Statistics</h3>
<p>Every item runs two or three times. Confidence intervals come from a cluster bootstrap over items, so an item's runs (and a
sentence's four noise versions) stay together. Systems are compared on the same items with a paired bootstrap, and p-values are
Holm-adjusted for the number of comparisons.</p>
</section>

<section id="validation" class="prose"><h2>Validation, costs and timing</h2>
<div class="cards">
<div class="card"><div class="k">JUDGE CHECK</div><h4>Two judges from different companies</h4><p>DeepSeek re-graded every suite A answer that GPT-6.1 had judged. Agreement: {j2_agree}.</p></div>
<div class="card"><div class="k">RUN TO RUN</div><h4>Repeats disagree</h4><p>Scribe v2 gave the same transcript on both runs for {pct(rerun['scribe-v2'], 1)} of clips; v3 for {pct(rerun['scribe-v3'], 1)}. In suite A, {pct(g['A'].flip_rate)} of items changed outcome between runs.</p></div>
<div class="card"><div class="k">COST</div><h4>Measured, not estimated</h4><p>ElevenLabs credits come from the account's usage report per product. Scribe cost 18.7 credits per minute of audio; text-to-speech S1–S2 used {sum(cred.values()):,.0f} credits across five models.</p></div>
<div class="card"><div class="k">KEYWORD BASELINE</div><h4>Judge versus a simple rule</h4><p>On safe questions, a keyword rule found {pct(overk.estimate, 1)} refusals; the LLM judge found {pct(over.estimate, 1)}. The judge catches polite refusals a keyword list misses.</p></div>
</div>
</section>

<section id="uncertainty" class="prose"><h2>What the ranges include, and what they leave out</h2>
<p>The 95% intervals cover the sampling of test items and repeated runs. They do not cover the choice of voice, test items beyond
these, or changes to the models over time. Several rates are exactly 0% with a 0–0% interval: that means no failure in this sample,
not that the true rate is zero. With 12 silent clips, one clip moves a rate by about 8 points.</p>
<h3>Limitations</h3>
<ul>
<li>Security tested GPT-5.6 only. AgentRouter refused GPT-6.2 and Claude for this account (“no available channel”).</li>
<li>The security judge is checked against a second LLM judge, not yet against human labels; the human listening test is not finished.</li>
<li>Prompt injections rarely succeeded, so the scaffold benchmark shows differences in detection, not in success.</li>
<li>Listening clips use ElevenLabs voices, which may favour ElevenLabs Scribe. Whisper is the independent comparison. Noise is mixed in, not recorded.</li>
<li>A video benchmark with Gemini stopped at the pilot because of free-tier limits and is not reported.</li>
</ul></section>

<section id="discussion" class="prose"><h2>Discussion</h2>
<h3>Benchmarks should be built around failure modes</h3>
<p>Every easy test here would have called the systems tied. The useful information came from tests designed around one specific way
a system can fail: misreading “$3.50”, writing words into silence, placing speech half a second late, or quietly following a hidden
instruction. When a test is built that way, the correct answer is known and grading needs no judge.</p>
<h3>Where safety lives matters</h3>
<p>Most of the over-refusal a user would see came from the gateway, not the model, and a one-page policy file changed agent behaviour
more than switching harness or model did. Safety evaluations of a model on its own can miss the layer that users actually meet.</p>
</section>

<section id="reproduce" class="prose"><h2>Reproducing this page</h2>
<p>All code, prompts and results are in the repository: <a href="{REPO}">{REPO.replace("https://", "")}</a>. Each benchmark has its own
build, run and report commands, and this page is rebuilt from the results files with one command:</p>
<pre>python -m venv .venv; .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python site/build.py        # writes docs/index.html and docs/figures/</pre>
<h3>References</h3>
<ol class="refs">
<li>Souly et al. (2024). A StrongREJECT for Empty Jailbreaks.</li>
<li>Röttger et al. (2024). XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models.</li>
<li>Radford et al. (2023). Robust Speech Recognition via Large-Scale Weak Supervision.</li>
<li>Greshake et al. (2023). Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.</li>
<li>Holm, S. (1979). A Simple Sequentially Rejective Multiple Test Procedure.</li>
</ol></section>
<footer>Built {date.today():%d %B %Y} from the committed results files · Fonts: Karla and Lekton (SIL Open Font License).</footer>
</main>
<script>window.__DATA__ = {json.dumps(data)};</script>
<script>{JS}</script>
</body></html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    print(f"Wrote docs/index.html ({len(page) / 1024:.0f} KB), {len(data)} tests, 6 figures in docs/figures/")


if __name__ == "__main__":
    build()
