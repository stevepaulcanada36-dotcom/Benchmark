"""Blinded listening test (MOS, S3 pronunciation check, S4 A/B preference) and its analysis."""
import csv
import itertools
import json
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from .generate import ROOT, audio_dir, items
from .stats import cluster_bootstrap, wilson

LT = ROOT / "listening_test"
RES = ROOT / "listening_results"


def make(cfg, n_mos=60, n_ab=40, pilot=False):
    d = audio_dir(pilot)
    clips = pd.DataFrame([json.loads(l) for l in open(d / "clips.jsonl")]).drop_duplicates("path", keep="last")
    by_uid = {it["uid"]: it for it in items()}
    rnd = random.Random(cfg["seed"])
    if LT.exists():
        shutil.rmtree(LT)
    (LT / "clips").mkdir(parents=True)
    key, tasks = {}, []

    def add_clip(path):
        cid = f"c{len(key):04d}"
        src = ROOT / path
        shutil.copy(src, LT / "clips" / f"{cid}{src.suffix}")
        return cid, f"clips/{cid}{src.suffix}"

    # MOS + pronunciation: run 0 only, stratified over models, suites S1/S3/S4
    pool = clips[(clips.run == 0) & clips.suite.isin(["S1", "S3", "S4"])]
    per_model = max(1, n_mos // max(1, pool.model_label.nunique()))
    pick = pd.concat([g.sample(min(len(g), per_model), random_state=cfg["seed"]) for _, g in pool.groupby("model_label")])
    for _, c in pick.sample(frac=1, random_state=cfg["seed"]).iterrows():
        cid, src = add_clip(c.path)
        it = by_uid[c.uid]
        key[cid] = dict(model=c.model_label, uid=c.uid, suite=c.suite)
        t = dict(kind="mos", id=cid, src=src, text=it["reference"])
        if c.suite == "S3":
            t["question"] = f"Was \"{it['target']}\" pronounced as: {it['reading']}?"
        tasks.append(t)

    # A/B on S4: every model pair for every item, then subsample; side randomized
    s4 = clips[(clips.suite == "S4") & (clips.run == 0)]
    pairs = []
    for uid, g in s4.groupby("uid"):
        for a, b in itertools.combinations(g.to_dict("records"), 2):
            pairs.append((a, b) if rnd.random() < 0.5 else (b, a))
    rnd.shuffle(pairs)
    for a, b in pairs[:n_ab]:
        ca, sa = add_clip(a["path"]); key[ca] = dict(model=a["model_label"], uid=a["uid"], suite="S4")
        cb, sb = add_clip(b["path"]); key[cb] = dict(model=b["model_label"], uid=b["uid"], suite="S4")
        tasks.append(dict(kind="ab", id=f"{ca}-{cb}", src_a=sa, src_b=sb, a=ca, b=cb,
                          text=by_uid[a["uid"]]["text"]))
    (ROOT / "listening_key.json").write_text(json.dumps(key, indent=1))
    (LT / "index.html").write_text(HTML.replace("__TASKS__", json.dumps(tasks)), encoding="utf-8")
    print(f"Wrote listening_test/ ({sum(t['kind']=='mos' for t in tasks)} MOS clips, "
          f"{sum(t['kind']=='ab' for t in tasks)} A/B pairs). Model identities are in listening_key.json; "
          "do not send that file to listeners.\nZip listening_test/ and send it; each listener opens index.html, "
          "rates everything, and clicks 'Download my answers'. Put the CSVs in listening_results/.")


def analyze(B=2000):
    key = json.loads((ROOT / "listening_key.json").read_text())
    files = sorted(RES.glob("*.csv"))
    if not files:
        raise SystemExit("Put listener CSVs in listening_results/ first.")
    rows = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    lines = ["# Listening test results", "", f"Listeners: {rows.rater.nunique()} ({', '.join(rows.rater.unique())})", ""]

    mos = rows[rows.task == "mos"].copy()
    if len(mos):
        mos["model"] = mos.id.map(lambda i: key[i]["model"])
        mos["score"] = mos.score.astype(float)
        lines += ["## MOS (1-5), 95% CI by bootstrap over clips", "", "| Model | MOS | 95% CI | Clips | Ratings |", "|---|---|---|---|---|"]
        for m, g in mos.groupby("model"):
            mat = g.pivot_table(index="id", columns="rater", values="score")
            mean, lo, hi = cluster_bootstrap(mat.values, B=B)
            lines.append(f"| {m} | {mean:.2f} | {lo:.2f}-{hi:.2f} | {mat.shape[0]} | {len(g)} |")
        wide = mos.pivot_table(index="id", columns="rater", values="score")
        if wide.shape[1] >= 2:
            cors = [wide[a].corr(wide[b], method="spearman") for a, b in itertools.combinations(wide.columns, 2)]
            lines += ["", f"Mean pairwise Spearman correlation between listeners: {np.nanmean(cors):.2f}"]
        pr = mos[mos.pron.notna() & (mos.pron != "")]
        if len(pr):
            lines += ["", "## S3 pronunciation correct (listener judgement)", "", "| Model | Correct | 95% Wilson CI | n |", "|---|---|---|---|"]
            for m, g in pr.groupby("model"):
                k, n = int((g.pron == "yes").sum()), len(g)
                lo, hi = wilson(k, n)
                lines.append(f"| {m} | {k/n:.0%} | {lo:.0%}-{hi:.0%} | {n} |")
        lines.append("")

    ab = rows[rows.task == "ab"].copy()
    if len(ab):
        ab["ma"] = ab.id.map(lambda i: key[i.split("-")[0]]["model"])
        ab["mb"] = ab.id.map(lambda i: key[i.split("-")[1]]["model"])
        ab = ab[ab.choice.isin(["A", "B", "tie"])]
        models = sorted(set(ab.ma) | set(ab.mb))
        theta = bradley_terry(ab, models)
        rng = np.random.default_rng(0)
        boots = np.array([bradley_terry(ab.iloc[rng.integers(0, len(ab), len(ab))], models) for _ in range(B // 4)])
        lines += ["## S4 expressiveness: Bradley-Terry on Elo scale (95% bootstrap CI)", "",
                  "| Model | Elo | 95% CI |", "|---|---|---|"]
        for i in np.argsort(-theta):
            lo, hi = np.percentile(boots[:, i], [2.5, 97.5])
            lines.append(f"| {models[i]} | {theta[i]:.0f} | {lo:.0f}-{hi:.0f} |")
        lines += ["", f"{len(ab)} judgements; ties count as half a win each."]
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "listening_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def bradley_terry(df, models, iters=200):
    """MM algorithm; returns Elo-scaled strengths (mean 1500)."""
    idx = {m: i for i, m in enumerate(models)}
    k = len(models)
    wins, n = np.zeros((k, k)), np.zeros((k, k))
    for _, r in df.iterrows():
        a, b = idx[r.ma], idx[r.mb]
        w = 1.0 if r.choice == "A" else 0.0 if r.choice == "B" else 0.5
        wins[a, b] += w; wins[b, a] += 1 - w
        n[a, b] += 1; n[b, a] += 1
    p = np.ones(k)
    W = wins.sum(axis=1) + 0.5          # light prior keeps unbeaten models finite
    for _ in range(iters):
        denom = np.array([sum(n[i, j] / (p[i] + p[j]) for j in range(k) if j != i and n[i, j]) + 1 / (p[i] + 1)
                          for i in range(k)])
        p = W / np.maximum(denom, 1e-12)
        p /= np.exp(np.mean(np.log(p)))
    return 1500 + 400 / np.log(10) * np.log(p)


HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Listening test</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:16px;background:#fafafa;color:#222}
.card{background:#fff;border:1px solid #ddd;border-radius:8px;padding:14px;margin:12px 0}
.text{color:#555;font-style:italic;margin:6px 0}label{margin-right:14px;white-space:nowrap}
button{font-size:16px;padding:8px 14px}audio{width:100%}.done{border-color:#4a4}
</style></head><body>
<h1>Listening test</h1>
<p>Use headphones in a quiet room. Rate each clip on its own. For A/B, pick the clip whose delivery fits the
script better (emotion, timing, naturalness). Clips are labelled with random codes.</p>
<p>Your name or initials: <input id="rater"></p>
<div id="tasks"></div>
<p id="progress"></p><button onclick="save()">Download my answers</button>
<script>
const T=__TASKS__; const ans={};
const box=document.getElementById('tasks');
const mosScale=[1,2,3,4,5].map(v=>v).join('');
T.forEach((t,i)=>{const d=document.createElement('div');d.className='card';d.id='t'+i;
 if(t.kind==='mos'){d.innerHTML=`<b>${i+1}. Clip ${t.id}</b><div class="text">"${t.text}"</div><audio controls preload="none" src="${t.src}"></audio>
 <div>Overall quality: ${[1,2,3,4,5].map(v=>`<label><input type=radio name=m${i} value=${v}> ${v}</label>`).join('')}
 <small>(1 bad, 5 excellent)</small></div>`+(t.question?`<div>${t.question} <label><input type=radio name=p${i} value=yes> yes</label><label><input type=radio name=p${i} value=no> no</label></div>`:'');}
 else{d.innerHTML=`<b>${i+1}. Compare</b><div class="text">Script: "${t.text}"</div>A <audio controls preload="none" src="${t.src_a}"></audio>
 B <audio controls preload="none" src="${t.src_b}"></audio><div>Better fit: <label><input type=radio name=c${i} value=A> A</label>
 <label><input type=radio name=c${i} value=B> B</label><label><input type=radio name=c${i} value=tie> about the same</label></div>`;}
 box.appendChild(d);});
box.addEventListener('change',e=>{const n=e.target.name,i=+n.slice(1);ans[i]=ans[i]||{};ans[i][n[0]]=e.target.value;
 const t=T[i],a=ans[i];const ok=t.kind==='ab'?a.c:(a.m&&(!t.question||a.p));document.getElementById('t'+i).classList.toggle('done',!!ok);
 document.getElementById('progress').textContent=Object.keys(ans).length+' / '+T.length+' answered';});
function save(){const r=document.getElementById('rater').value.trim();if(!r){alert('Enter your name first');return;}
 const rows=[['rater','task','id','score','pron','choice']];
 T.forEach((t,i)=>{const a=ans[i]||{};rows.push([r,t.kind,t.id,a.m||'',a.p||'',a.c||'']);});
 const csv=rows.map(x=>x.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\n');
 const b=new Blob([csv],{type:'text/csv'});const u=URL.createObjectURL(b);const l=document.createElement('a');
 l.href=u;l.download='listening_'+r.replace(/\W+/g,'_')+'.csv';l.click();}
</script></body></html>"""
