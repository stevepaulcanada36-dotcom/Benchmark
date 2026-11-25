"""Builds a blind rating page: videogen/rating/index.html. Open it in a browser (double-click), rate, download the CSV.

Three kinds of task, shuffled together:
- clip: one clip, judged on its own (within-shot consistency, prompt, text, sound, demo-ready?)
- storyboard: the three shots of one storyboard side by side (cross-shot consistency)
- pair: two clips made from the same prompt (one same-seed, one new-seed pair per storyboard), how alike are they?
Clips are copied under random codes so the model name is never visible. A share of clip tasks is shown a second
time under a new code, so the report can measure how consistent the rater is with themself.
"""
import json
import random
import shutil

from .core import WORK, clip_path
from .items import SB_BY_ID, clips

OUT = WORK / "rating"

CLIP_Q = [
    ("identity", "scale", "The character or subject looks the same from start to end."),
    ("objects", "scale", "Objects and background stay put: nothing melts, morphs, pops in or vanishes."),
    ("motion", "scale", "Motion is smooth and natural: no flicker, jitter or boiling textures."),
    ("prompt", "scale", "It shows what the prompt asks for: the actions, counts and colours."),
    ("text", "choice:yes,partly,no,none asked", "Any text or numbers the prompt asks for are readable and correct."),
    ("sound", "choice:1,2,3,4,5,no sound", "The sound fits what you see, and happens at the right moment."),
    ("demo", "choice:yes,maybe,no", "Would you put this clip in a 1-minute hackathon demo video?"),
]
SB_Q = [
    ("character", "scale", "It is clearly the same character in all three shots."),
    ("style", "scale", "The art style (colours, line, lighting) matches across the shots."),
    ("place", "scale", "It is clearly the same place: layout and landmarks match."),
    ("state", "choice:yes,partly,no", "The story detail carries over (see the check below)."),
    ("story", "scale", "Played in order, the three shots read as one short story."),
]
PAIR_Q = [("similar", "choice:nearly identical,same scene with small differences,clearly different",
           "These two clips were made from the same prompt. How alike are they?")]


def build(cfg, rater_seed=None):
    rng = random.Random(rater_seed if rater_seed is not None else cfg["seed"])
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "v").mkdir(parents=True)
    codes = set()

    def code():
        while True:
            c = "".join(rng.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(6))
            if c not in codes:
                codes.add(c)
                return c

    def put(model, cid):
        c = code()
        shutil.copy(clip_path(model, cid), OUT / "v" / f"{c}.mp4")
        return c

    tasks, key = [], {}
    allc = clips(cfg)
    for m in cfg["models"]:
        have = {c["cid"]: c for c in allc if clip_path(m["name"], c["cid"]).exists()}
        clip_tasks = []
        for cid, c in have.items():
            t = dict(id=code(), type="clip", videos=[put(m["name"], cid)], prompt=c["prompt"])
            key[t["id"]] = dict(model=m["name"], cid=cid, type="clip")
            clip_tasks.append(t)
        for t in rng.sample(clip_tasks, round(len(clip_tasks) * cfg["repeat_share"])):
            k = key[t["id"]]
            t2 = dict(id=code(), type="clip", videos=[put(m["name"], k["cid"])], prompt=t["prompt"])
            key[t2["id"]] = dict(k, repeat_of=t["id"])
            clip_tasks.append(t2)
        tasks += clip_tasks
        for sb in SB_BY_ID.values():
            ids = [f"{sb['id']}-{s}" for s, _ in sb["shots"]]
            if all(i in have for i in ids):
                t = dict(id=code(), type="storyboard", videos=[put(m["name"], i) for i in ids],
                         prompt=" | ".join(f"Shot {s}: {x}" for s, x in sb["shots"]), check=sb["carry"])
                key[t["id"]] = dict(model=m["name"], sb=sb["id"], type="storyboard")
                tasks.append(t)
            for suffix, kind in (("1r", "same seed"), ("1s", "new seed")):
                a, b = f"{sb['id']}-1", f"{sb['id']}-{suffix}"
                if a in have and b in have:
                    pair = [a, b] if rng.random() < 0.5 else [b, a]
                    t = dict(id=code(), type="pair", videos=[put(m["name"], i) for i in pair], prompt=have[a]["prompt"])
                    key[t["id"]] = dict(model=m["name"], sb=sb["id"], type="pair", pair=kind)
                    tasks.append(t)
    rng.shuffle(tasks)
    (OUT / "key_DO_NOT_OPEN_BEFORE_RATING.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    page = PAGE.replace("__TASKS__", json.dumps(tasks)).replace("__Q__", json.dumps(dict(clip=CLIP_Q, storyboard=SB_Q, pair=PAIR_Q)))
    (OUT / "index.html").write_text(page, encoding="utf-8")
    n = {k: sum(t["type"] == k for t in tasks) for k in ("clip", "storyboard", "pair")}
    print(f"Wrote videogen/rating/index.html: {n['clip']} clip, {n['storyboard']} storyboard and {n['pair']} pair tasks "
          f"(about {round((n['clip'] * 40 + n['storyboard'] * 60 + n['pair'] * 25) / 60)} minutes). "
          "Open it in a browser; when done, click Download and save the CSV into videogen/ratings/.")


PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video Consistency Rating</title><style>
:root{--bg:#14181e;--panel:#1d232b;--ink:#e8eaed;--mute:#9aa3ad;--line:#2e3742;--acc:#E3B341}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,Segoe UI,Arial,sans-serif}
.wrap{max-width:1100px;margin:auto;padding:16px}header{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
input,textarea{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px;font:inherit}
button{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}
button.on{border-color:var(--acc);background:rgba(227,179,65,.18)}button.main{background:var(--acc);color:#14181e;border:0;font-weight:700}
.vids{display:grid;gap:8px;margin:12px 0}.vids.n1{grid-template-columns:1fr}.vids.n2{grid-template-columns:1fr 1fr}.vids.n3{grid-template-columns:1fr 1fr 1fr}
@media(max-width:700px){.vids.n2,.vids.n3{grid-template-columns:1fr}}
video{width:100%;border-radius:8px;background:#000}.lab{color:var(--mute);font-size:13px}
.prompt{background:var(--panel);border-radius:8px;padding:10px 12px;color:#cfd3d8;font-size:14.5px}
.check{border-left:3px solid var(--acc);padding:6px 10px;margin:8px 0;background:var(--panel)}
.q{padding:10px 0;border-bottom:1px solid var(--line)}.q p{margin:0 0 6px}.opts{display:flex;gap:6px;flex-wrap:wrap}
.bar{height:6px;background:var(--line);border-radius:3px;overflow:hidden;flex:1;min-width:120px}.bar i{display:block;height:100%;background:var(--acc)}
.nav{display:flex;gap:8px;margin:16px 0;flex-wrap:wrap}.scale-help{color:var(--mute);font-size:13px}
</style></head><body><div class="wrap">
<header><b>Video consistency rating</b><input id="rater" placeholder="Your name or initials"><div class="bar"><i id="prog"></i></div><span id="count" class="lab"></span>
<button id="dl">Download ratings CSV</button></header>
<p class="scale-help">Scale: 1 = strongly disagree, 3 = neither, 5 = strongly agree. Watch each video at least twice. Model names are hidden on purpose. Your answers are saved in this browser as you go.</p>
<div id="task"></div>
<div class="nav"><button id="prev">← Previous</button><button class="main" id="next">Save and next →</button><button id="skip">Next unrated</button></div>
</div><script>
const T=__TASKS__,Q=__Q__,KEY='vgrate-v1';let S={};try{S=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
let i=0;const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const rater=document.getElementById('rater');rater.value=S.__rater||'';rater.oninput=()=>{S.__rater=rater.value;save()};
const done=t=>{const a=S[t.id]||{};return Q[t.type].every(q=>a[q[0]]!==undefined)};
function opts(t,q){const a=S[t.id]||{};const vals=q[1]==='scale'?['1','2','3','4','5']:q[1].slice(7).split(',');
 return '<div class="opts">'+vals.map(v=>`<button data-q="${q[0]}" data-v="${v}" class="${a[q[0]]===v?'on':''}">${v}</button>`).join('')+'</div>'}
function show(){const t=T[i],a=S[t.id]||{};const what={clip:'One clip',storyboard:'Three shots of one storyboard, in order',pair:'Two clips from the same prompt'}[t.type];
 document.getElementById('task').innerHTML=`<p class="lab">Task ${i+1} of ${T.length} · ${what} · code ${t.id}</p>
 <div class="vids n${t.videos.length}">${t.videos.map((v,k)=>`<div><video src="v/${v}.mp4" controls loop playsinline preload="metadata"></video><div class="lab">${t.type==='storyboard'?'Shot '+(k+1):t.type==='pair'?'Clip '+'AB'[k]:''}</div></div>`).join('')}</div>
 <div class="prompt"><span class="lab">Prompt</span><br>${t.prompt}</div>${t.check?`<div class="check"><b>Check:</b> ${t.check}</div>`:''}
 ${Q[t.type].map(q=>`<div class="q"><p>${q[2]}</p>${opts(t,q)}</div>`).join('')}
 <div class="q"><p class="lab">Notes (optional): what went wrong?</p><textarea id="note" rows="2" style="width:100%">${a.note||''}</textarea></div>`;
 document.querySelectorAll('#task [data-q]').forEach(b=>b.onclick=()=>{S[t.id]=S[t.id]||{};S[t.id][b.dataset.q]=b.dataset.v;save();show()});
 document.getElementById('note').oninput=e=>{S[t.id]=S[t.id]||{};S[t.id].note=e.target.value;save()};
 const n=T.filter(done).length;document.getElementById('count').textContent=n+' / '+T.length+' rated';document.getElementById('prog').style.width=(100*n/T.length)+'%';}
document.getElementById('next').onclick=()=>{if(i<T.length-1){i++;show();scrollTo(0,0)}};
document.getElementById('prev').onclick=()=>{if(i>0){i--;show();scrollTo(0,0)}};
document.getElementById('skip').onclick=()=>{const k=T.findIndex(t=>!done(t));if(k>=0){i=k;show();scrollTo(0,0)}};
document.getElementById('dl').onclick=()=>{const cols=['rater','task','type',...new Set(Object.values(Q).flat().map(q=>q[0])),'note'];
 const esc=v=>'"'+String(v??'').replace(/"/g,'""')+'"';
 const rows=T.filter(t=>S[t.id]).map(t=>cols.map(c=>esc(c==='rater'?S.__rater:c==='task'?t.id:c==='type'?t.type:S[t.id][c])).join(','));
 const b=new Blob([cols.join(',')+'\n'+rows.join('\n')],{type:'text/csv'});const u=URL.createObjectURL(b);const l=document.createElement('a');
 l.href=u;l.download='ratings_'+(S.__rater||'rater').replace(/\W+/g,'_')+'.csv';l.click();};
show();
</script></body></html>"""
