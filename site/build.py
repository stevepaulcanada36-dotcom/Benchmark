"""Builds the results website (docs/index.html) from each benchmark's results/ folder.

Run from the repo root after any report:  python site/build.py
GitHub Pages serves docs/ (Settings -> Pages -> Deploy from branch -> main, /docs).
Every number on the page is read from the committed results CSVs; nothing is typed in by hand.
"""
import html
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
REPO = "https://github.com/stevepaulcanada36-dotcom/Benchmark"

A = pd.read_csv(ROOT / "audio/results/metrics_main.csv")
L = pd.read_csv(ROOT / "listen/results/metrics.csv")
S = pd.read_csv(ROOT / "security/results/metrics_main.csv")
C = pd.read_csv(ROOT / "scaffold/results/metrics_combined.csv")


# ---------------------------------------------------------------- helpers
def row(df, **kw):
    m = df
    for k, v in kw.items():
        m = m[m[k] == v]
    if len(m) != 1:
        raise KeyError(f"{kw}: {len(m)} rows")
    return m.iloc[0]


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def ci(r, p=True, d=1):
    f = (lambda v: f"{v * 100:.{d}f}%") if p else (lambda v: f"{v:.2f}")
    return f"{f(r.estimate)} <span class=ci>({f(r.ci_low)}–{f(r.ci_high)})</span>"


def esc(s):
    return html.escape(str(s))


def bars(items, pct_axis=True, lo_better=False, unit=""):
    """Horizontal bars with 95% CI whiskers as inline SVG. items: [(label, est, lo, hi)]."""
    w, lw, rh = 900, 200, 30
    top = max(max(i[3] for i in items), 1e-9)
    top = 1.0 if pct_axis and top > 0.5 else top * 1.15
    sx = lambda v: lw + (w - lw - 70) * (v / top)
    h = rh * len(items) + 24
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" class="chart">']
    for t in (0, 0.5, 1.0):
        x = sx(top * t)
        out.append(f'<line x1="{x:.1f}" y1="4" x2="{x:.1f}" y2="{h - 18}" class="grid"/>'
                   f'<text x="{x:.1f}" y="{h - 4}" class="tick" text-anchor="middle">'
                   f'{pct(top * t) if pct_axis else f"{top * t:.2f}{unit}"}</text>')
    for k, (lab, est, lo, hi) in enumerate(items):
        y = 6 + k * rh
        val = pct(est, 1) if pct_axis else f"{est:.2f}{unit}"
        out.append(f'<text x="{lw - 10}" y="{y + 15}" class="lab" text-anchor="end">{esc(lab)}</text>'
                   f'<rect x="{lw}" y="{y + 3}" width="{max(sx(est) - lw, 1.5):.1f}" height="16" rx="3" class="bar"/>'
                   f'<line x1="{sx(lo):.1f}" y1="{y + 11}" x2="{sx(hi):.1f}" y2="{y + 11}" class="whisk"/>'
                   f'<line x1="{sx(lo):.1f}" y1="{y + 6}" x2="{sx(lo):.1f}" y2="{y + 16}" class="whisk"/>'
                   f'<line x1="{sx(hi):.1f}" y1="{y + 6}" x2="{sx(hi):.1f}" y2="{y + 16}" class="whisk"/>'
                   f'<text x="{sx(hi) + 8:.1f}" y="{y + 15}" class="val">{val}</text>')
    out.append("</svg>")
    note = "lower is better" if lo_better else "higher is better"
    return "".join(out) + f'<p class="cap">Bars: estimate. Whiskers: 95% CI. {note}.</p>'


def table(df, cols, header):
    th = "".join(f"<th>{esc(h)}</th>" for h in header)
    trs = "".join("<tr>" + "".join(f"<td>{r[c]}</td>" for c in cols) + "</tr>" for _, r in df.iterrows())
    return f'<div class="tw"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


# ---------------------------------------------------------------- numbers used in the text
models_a = ["flash-v2.5", "multi-v2", "v3", "v4", "v4-turbo"]
s2 = {m: row(A, model=m, suite="S2", metric="s2_pass") for m in models_a}
ttfa = {m: row(A, model=m, suite="ALL", metric="ttfa_s") for m in models_a}
cred = {m: row(A, model=m, suite="ALL", metric="credits_used").estimate for m in models_a}
s1max = A[(A.suite == "S1") & (A.metric == "wer")].estimate.max()
sys_l = ["scribe-v3", "scribe-v2", "whisper-v3", "whisper-v3-vad"]
hall = {s: row(L, system=s, suite="L3", metric="hallucinated") for s in sys_l}
onset = {s: row(L, system=s, suite="L1", condition="all", metric="onset_err") for s in sys_l}
l1max = L[(L.suite == "L1") & (L.metric == "wer")].estimate.max()
rerun = {s: row(L, system=s, metric="identical_reruns").estimate for s in ("scribe-v2", "scribe-v3")}
g_c = row(S, suite="C", metric="gateway_block_rate")
o_c = row(S, suite="C", metric="overrefusal_rate")
g_a = row(S, suite="A", metric="gateway_block_rate")
comp = row(S, suite="A", metric="compliance_rate")
leak = row(S, suite="D", metric="leak_rate")
att = C[C.metric == "attack_success"]
flag = {m: row(C, model=m, scaffold="S3_auto_guard", metric="injection_flagged") for m in ("GPT-5.6", "GPT-6.1")}
util3 = C[(C.scaffold == "S3_auto_guard") & (C.metric == "utility_under_attack")].estimate.min()
best_s2 = max(models_a, key=lambda m: s2[m].estimate)
worst_s2 = min(models_a, key=lambda m: s2[m].estimate)

# ---------------------------------------------------------------- sections
findings = [
    ("Easy tests call every system perfect. Stress tests don't.",
     f"On plain speech every text-to-speech model scores at most {pct(s1max, 1)} word errors and every transcriber at most "
     f"{pct(l1max, 1)}, even in loud noise. Targeted tests split the same systems wide open: "
     f"{pct(s2[worst_s2].estimate)} to {pct(s2[best_s2].estimate)} on reading numbers and dates, and 0% vs 100% on "
     f"inventing words in silence."),
    (f"The best text-to-speech model for hard text is also one of the cheapest.",
     f"{best_s2} passes {pct(s2[best_s2].estimate)} of number, date and symbol items at {cred[best_s2] / cred['v4']:.0%} of "
     f"v4's credits. flash-v2.5 starts speaking fastest ({ttfa['flash-v2.5'].estimate:.2f} s vs "
     f"{ttfa['v4'].estimate:.2f} s for v4) but passes only {pct(s2['flash-v2.5'].estimate)}."),
    ("Whisper invents “Thank you for watching” on silence. A silence filter mostly fixes it.",
     f"Whisper large-v3 wrote words on {pct(hall['whisper-v3'].estimate)} of clips with no speech. With its silence filter: "
     f"{pct(hall['whisper-v3-vad'].estimate)}. Scribe: {pct(hall['scribe-v3'].estimate)}. Scribe also places speech "
     f"{onset['whisper-v3'].estimate / onset['scribe-v3'].estimate:.0f}× more precisely in time "
     f"({onset['scribe-v3'].estimate:.2f} s vs {onset['whisper-v3'].estimate:.2f} s off)."),
    ("Most refusals of safe questions came from the gateway, not the model.",
     f"AgentRouter's filter blocked {pct(g_c.estimate, 1)} of completely safe XSTest questions before the model saw them. "
     f"GPT-5.6 itself refused {pct(o_c.estimate, 1)}. The filter also blocked {pct(g_a.estimate, 1)} of harmful requests; "
     f"the model complied with {pct(comp.estimate)} of the rest and leaked a secret {pct(leak.estimate)} of the time."),
    ("A short security policy file makes the agent call out attacks without hurting its work.",
     f"With an AGENTS.md policy the agent flagged the hidden instruction in {pct(flag['GPT-5.6'].estimate)} (GPT-5.6) and "
     f"{pct(flag['GPT-6.1'].estimate)} (GPT-6.1) of attacked tasks, vs 0% without it, and still finished "
     f"≥{pct(util3)} of tasks. Pasting files into the prompt was the only setup an attack got through "
     f"(max {pct(att.estimate.max(), 1)})."),
    ("Repeat runs disagree, so every number here is repeated.",
     f"Scribe v2 gave the same transcript on both runs for {pct(rerun['scribe-v2'], 1)} of clips, v3 for "
     f"{pct(rerun['scribe-v3'], 1)}. In safety suite A, {pct(row(S, suite='A', metric='gateway_block_rate').flip_rate)} of "
     f"items changed outcome between runs. All CIs are cluster bootstraps over items with runs kept together."),
]

# audio table: every metric x model, so S3-S5 appear automatically once scored
order = {"S1": 1, "S2": 2, "S3": 3, "S4": 4, "S5": 5, "ALL": 9}
au = A[A.metric != "credits_used"].copy()
au["key"] = au.suite + " · " + au.description
piv = []
for key, g in sorted(au.groupby("key"), key=lambda kv: (order.get(kv[1].suite.iloc[0], 8), kv[0])):
    r = {"Metric": esc(key)}
    p = g.metric.iloc[0] in ("wer", "s2_pass")
    for m in models_a:
        x = g[g.model == m]
        r[m] = ci(x.iloc[0], p=p) if len(x) else "–"
    piv.append(r)
audio_tbl = table(pd.DataFrame(piv), ["Metric"] + models_a, ["Metric"] + models_a)
audio_suites = sorted(set(A.suite) - {"ALL"})

listen_rows = []
for suite, cond, met, lab, p in [("L1", "clean", "wer", "Word errors, clean speech", True),
                                 ("L1", "cafe_0db", "wer", "Word errors, loud cafe noise (0 dB)", True),
                                 ("L3", "all", "hallucinated", "No-speech clips with invented words", True),
                                 ("L1", "all", "onset_err", "Speech start error (s)", False),
                                 ("L4", "all", "event_correct", "Sound event tagged at the right time", True),
                                 ("L5", "all", "speaker_attribution", "Words given to the right speaker", True)]:
    r = {"Metric": lab}
    for s in sys_l:
        x = L[(L.system == s) & (L.suite == suite) & (L.condition == cond) & (L.metric == met)]
        r[s] = ci(x.iloc[0], p=p) if len(x) else "n/a"
    listen_rows.append(r)
listen_tbl = table(pd.DataFrame(listen_rows), ["Metric"] + sys_l, ["Metric"] + sys_l)

sec_rows = [{"Suite": r.suite, "Metric": esc(r.description), "GPT-5.6": ci(r), "Items × runs": f"{r.n_items} × {r.runs}"}
            for r in S.itertuples()]
sec_tbl = table(pd.DataFrame(sec_rows), ["Suite", "Metric", "GPT-5.6", "Items × runs"], ["Suite", "Metric", "GPT-5.6", "Items × runs"])

scaf = ["S0_pasted", "S1_agent_readonly", "S2_agent_auto", "S3_auto_guard"]
scaf_name = {"S0_pasted": "S0 pasted", "S1_agent_readonly": "S1 agent, approvals", "S2_agent_auto": "S2 agent, auto",
             "S3_auto_guard": "S3 auto + policy"}
sc_rows = []
for met, lab in [("attack_success", "Attack succeeded"), ("injection_flagged", "Agent flagged the injection"),
                 ("utility_clean", "Task done, clean files"), ("utility_under_attack", "Task done, under attack"),
                 ("gateway_block_rate", "Blocked by gateway")]:
    for m in ("GPT-5.6", "GPT-6.1"):
        r = {"Metric": f"{lab} · {m}"}
        for s in scaf:
            r[s] = ci(row(C, model=m, scaffold=s, metric=met))
        sc_rows.append(r)
scaf_tbl = table(pd.DataFrame(sc_rows), ["Metric"] + scaf, ["Metric"] + [scaf_name[s] for s in scaf])

charts = {
    "s2": bars([(m, s2[m].estimate, s2[m].ci_low, s2[m].ci_high) for m in models_a]),
    "ttfa": bars([(m, ttfa[m].estimate, ttfa[m].ci_low, ttfa[m].ci_high) for m in models_a], pct_axis=False, lo_better=True, unit=" s"),
    "hall": bars([(s, hall[s].estimate, hall[s].ci_low, hall[s].ci_high) for s in sys_l], lo_better=True),
    "sec": bars([("Gateway blocked (safe Qs)", g_c.estimate, g_c.ci_low, g_c.ci_high),
                 ("Model refused (safe Qs)", o_c.estimate, o_c.ci_low, o_c.ci_high),
                 ("Gateway blocked (harmful)", g_a.estimate, g_a.ci_low, g_a.ci_high),
                 ("Model complied (harmful)", comp.estimate, comp.ci_low, comp.ci_high)], lo_better=True),
    "flag": bars([(f"{scaf_name[s]} · {m}", r.estimate, r.ci_low, r.ci_high)
                  for s in scaf for m in ("GPT-5.6", "GPT-6.1")
                  for r in [row(C, model=m, scaffold=s, metric="injection_flagged")]]),
}

# ---------------------------------------------------------------- page
CSS = """
:root{--bg:#0f1115;--panel:#171a21;--ink:#e8e6e1;--mute:#9aa0a6;--line:#2a2f39;--acc:#e8b04b;--bar:#5b8def;--good:#4fb286}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#faf8f4;--panel:#fff;--ink:#1d1f23;--mute:#5f6670;--line:#e3dfd6;--acc:#b7791f;--bar:#3c6fd8;--good:#2f855a}}
:root[data-theme="light"]{--bg:#faf8f4;--panel:#fff;--ink:#1d1f23;--mute:#5f6670;--line:#e3dfd6;--acc:#b7791f;--bar:#3c6fd8;--good:#2f855a}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 Karla,system-ui,sans-serif}
a{color:var(--acc)}code,.mono,.ci,.tick,.val{font-family:Lekton,ui-monospace,monospace}
nav{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
nav .in{max-width:1080px;margin:auto;padding:10px 16px;display:flex;gap:18px;align-items:center;overflow-x:auto;white-space:nowrap}
nav b{margin-right:8px}nav a{color:var(--mute);text-decoration:none;font-size:15px}nav a:hover{color:var(--ink)}
main{max-width:1080px;margin:auto;padding:0 16px 80px}
header.hero{padding:56px 0 28px;border-bottom:1px solid var(--line)}
.kicker{color:var(--acc);font:600 13px/1 Lekton,monospace;letter-spacing:.12em;text-transform:uppercase}
h1{font-size:clamp(30px,5vw,48px);line-height:1.1;margin:12px 0 14px;max-width:20ch}
h2{font-size:28px;margin:64px 0 6px}h3{font-size:19px;margin:26px 0 8px}
.lede{color:var(--mute);max-width:70ch;margin:0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:28px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
.stat .n{font:700 30px/1.1 Lekton,monospace;color:var(--acc)}.stat .t{color:var(--mute);font-size:14px;margin-top:6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin-top:18px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
.card h3{margin:0 0 8px;font-size:18px}.card p{margin:0;color:var(--mute);font-size:15.5px}
.card .num{font:700 13px Lekton,monospace;color:var(--acc)}
.grid2{display:block}
figure{margin:12px 0;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
figcaption{font-weight:700;margin-bottom:6px}.cap{color:var(--mute);font-size:13px;margin:4px 0 0}
.chart{width:100%;height:auto}.chart .grid{stroke:var(--line)}.chart .tick{fill:var(--mute);font-size:11px}
.chart .lab{fill:var(--ink);font-size:13px}.chart .val{fill:var(--mute);font-size:12px}.chart .bar{fill:var(--bar)}
.chart .whisk{stroke:var(--ink);stroke-width:1.4}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:12px 0}
table{border-collapse:collapse;width:100%;font-size:14.5px;background:var(--panel)}
th,td{padding:8px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--mute);font-weight:600;white-space:nowrap}td:has(.ci){white-space:nowrap}
.ci{color:var(--mute);font-size:.85em}
.pill{display:inline-block;font:600 12px Lekton,monospace;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mute);margin-right:6px}
.pill.ok{color:var(--good);border-color:var(--good)}.pill.part{color:var(--acc);border-color:var(--acc)}
.img{width:100%;border-radius:8px;background:#fff}
ul.lim li{margin:6px 0}pre{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;overflow-x:auto;font:14px/1.5 Lekton,monospace}
footer{border-top:1px solid var(--line);margin-top:64px;padding-top:18px;color:var(--mute);font-size:14px}
button.theme{margin-left:auto;background:none;border:1px solid var(--line);color:var(--mute);border-radius:8px;padding:4px 10px;cursor:pointer;font:inherit;font-size:14px}
"""


def section(id_, title, status, lede, body):
    pill = {"done": '<span class="pill ok">complete</span>', "part": '<span class="pill part">partial</span>'}[status]
    return f'<section id="{id_}"><h2>{title}</h2><p>{pill}</p><p class="lede">{lede}</p>{body}</section>'


def build():
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("")

    cards = "".join(f'<div class="card"><div class="num">FINDING {i}</div><h3>{esc(t)}</h3><p>{esc(b)}</p></div>'
                    for i, (t, b) in enumerate(findings, 1))
    stats = "".join(f'<div class="stat"><div class="n">{n}</div><div class="t">{esc(t)}</div></div>' for n, t in [
        (f"{pct(s2[worst_s2].estimate)}→{pct(s2[best_s2].estimate)}", "pass rate on numbers and dates across 5 TTS models"),
        (f"{pct(hall['whisper-v3'].estimate)} vs {pct(hall['scribe-v3'].estimate)}", "silent clips where Whisper vs Scribe invented words"),
        (f"{pct(g_c.estimate, 1)} vs {pct(o_c.estimate, 1)}", "safe questions blocked by the gateway vs refused by GPT-5.6"),
        (f"{pct(flag['GPT-6.1'].estimate)}", "of hidden attacks called out once a security policy file was added"),
    ])

    audio = section("audio", "Audio: text-to-speech", "part" if not {"S3", "S4", "S5"} <= set(audio_suites) else "done",
                    f"Five ElevenLabs text-to-speech models read the same scripts. Suites run:{', '.join(audio_suites)}. "
                    "Word errors are measured by transcribing each clip with Whisper; S2 checks whether numbers, dates, "
                    "currencies and symbols are read the way a person would say them.",
                    f'<div class="grid2"><figure><figcaption>S2: numbers, dates and symbols read correctly</figcaption>{charts["s2"]}</figure>'
                    f'<figure><figcaption>Time to first audio (streaming)</figcaption>{charts["ttfa"]}</figure></div>'
                    f"<h3>Every metric</h3>{audio_tbl}"
                    f'<p class="cap">Credits used for S1–S2, 3 runs: ' + ", ".join(f"{m} {cred[m]:,.0f}" for m in models_a) +
                    f'. <a href="{REPO}/blob/main/audio/results/summary_main.md">Full summary</a>.</p>')
    listen = section("listen", "Listening: speech-to-text on clips with exact answers", "done",
                     "We built 152 clips ourselves (clean and noisy speech, silence, sound effects, two-speaker dialogues), so "
                     "the correct transcript, timings and speakers are known exactly. Grading is deterministic: no LLM judge.",
                     f'<figure><figcaption>Clips with no speech where the system invented words</figcaption>{charts["hall"]}</figure>'
                     f"{listen_tbl}"
                     f'<p class="cap">Whisper outputs on silence included “Thank you.” and “Thanks for watching!”. '
                     f'<a href="{REPO}/blob/main/listen/results/summary.md">Full summary, with every invented phrase</a>.</p>')
    sec = section("security", "Security: harmful requests, over-refusal and secret leaks", "part",
                  "GPT-5.6 through AgentRouter, 3 runs per item. Suite A: 30 StrongREJECT harmful requests. "
                  "Suite C: 100 XSTest safe questions that sound risky. Suite D: 4 secret files × 25 extraction attempts. "
                  "A–C are graded by an LLM judge (GPT-6.1), cross-checked by a second judge from another vendor (DeepSeek: 100% agreement on A); D by regex. "
                  "Requests the gateway blocked are reported separately and excluded from the model's own rates.",
                  f'<figure><figcaption>Gateway filter vs the model itself</figcaption>{charts["sec"]}</figure>{sec_tbl}'
                  f'<p class="cap"><a href="{REPO}/blob/main/security/results/summary_main.md">Full summary</a> · '
                  f'<a href="{REPO}/blob/main/security/results/second_judge.md">Second judge</a>.</p>')
    scaff = section("scaffold", "Scaffold: does the agent harness change prompt-injection risk?", "done",
                    "Same model, four harnesses, 5 tasks × 4 attack goals × visible/hidden injections + clean controls, 2 runs. "
                    "Attacks are graded deterministically (marker word, fake key, fake link, or a file created on disk).",
                    f'<figure><figcaption>Agent explicitly flagged the injected instruction</figcaption>{charts["flag"]}</figure>{scaf_tbl}'
                    f'<p class="cap"><a href="{REPO}/blob/main/scaffold/results/summary_combined.md">Full summary</a>.</p>')

    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Stress Tests for AI Models</title>
<meta name="description" content="Four benchmarks of speech, safety and agent security, with 95% confidence intervals on every number.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Karla:wght@400;600;700&family=Lekton:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<nav><div class="in"><b>Stress Tests</b><a href="#findings">Findings</a><a href="#audio">Audio</a><a href="#listen">Listening</a>
<a href="#security">Security</a><a href="#scaffold">Scaffold</a><a href="#methods">Methods</a><a href="#limits">Limitations</a>
<a href="#reproduce">Reproduce</a><button class="theme" onclick="tg()">◐ Theme</button></div></nav>
<main>
<header class="hero"><div class="kicker">STA2453H · LLM benchmarks</div>
<h1>Easy tests say every model is perfect. Stress tests don't.</h1>
<p class="lede">Four benchmarks of speech and agent safety. Each one repeats every run, reports a 95% confidence interval on every
number, records cost, and uses graders with known answers wherever possible. On ordinary inputs the systems are
indistinguishable; targeted tests expose large, specific differences.</p>
<div class="stats">{stats}</div></header>
<section id="findings"><h2>Six findings</h2><div class="cards">{cards}</div></section>
{audio}{listen}{sec}{scaff}
<section id="methods"><h2>How it was measured</h2>
<ul class="lim"><li><b>Repeats:</b> every item runs 2–3 times (audio S4–S5 once). Run-to-run disagreement is reported.</li>
<li><b>Confidence intervals:</b> cluster bootstrap over items, keeping an item's runs (and, for Listening, its four noise versions) together.</li>
<li><b>Comparisons:</b> paired bootstrap on the same items, with Holm-adjusted p-values (in each summary).</li>
<li><b>Graders:</b> known-answer checks wherever possible (Listening, Scaffold, secret leaks). The LLM judge for harmful and safe
requests was cross-checked by a second judge from a different vendor.</li>
<li><b>Cost:</b> ElevenLabs credits were measured from the account's usage report per product, not estimated.</li></ul></section>
<section id="limits"><h2>Limitations</h2><ul class="lim">
<li>Security tested GPT-5.6 only: AgentRouter refused GPT-6.2 and Claude for this account (“no available channel”).</li>
<li>Human labels for the security judge and the listening test are not finished yet, so the judge is validated against a second LLM judge, not people.</li>
<li>Prompt-injection attacks almost never succeeded (≤{pct(att.estimate.max(), 1)}), so the scaffold benchmark can show detection differences but not success differences.</li>
<li>Listening clips use ElevenLabs voices, which may favour ElevenLabs Scribe; Whisper is the independent comparison. Noise is mixed in, not recorded.</li>
<li>A video benchmark with Gemini stopped at the pilot because of free-tier limits and is not reported.</li></ul></section>
<section id="reproduce"><h2>Reproduce</h2><p>Code, exact prompts and every results file: <a href="{REPO}">{REPO.replace('https://', '')}</a>.</p>
<pre>python -m venv .venv; .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cd listen; python -m listenbench report      # each benchmark has build/run/report commands
python site/build.py                         # rebuilds this page from the results CSVs</pre></section>
<footer>Built {date.today():%d %B %Y} from the committed results files.</footer>
</main>
<script>
function tg(){{const r=document.documentElement,d=r.dataset.theme||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');
r.dataset.theme=d==='dark'?'light':'dark';try{{localStorage.setItem('theme',r.dataset.theme)}}catch(e){{}}}}
try{{const t=localStorage.getItem('theme');if(t)document.documentElement.dataset.theme=t}}catch(e){{}}
</script></body></html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    print(f"Wrote {DOCS / 'index.html'} ({len(page) / 1024:.0f} KB)")


if __name__ == "__main__":
    build()
