"""Builds synthetic audio-visual clips whose ground truth is known exactly, plus their questions.

Picture: coloured shapes on a grey background that appear, disappear or flash at known times.
Sound: the six sound effects from ListenBench (dog, glass, knock, applause, laugh, phone) at known times.
Conditions (the modality ablation):
  av          original picture + original sound
  video_only  no audio track at all
  shifted     sound moved later by `shift_s` seconds
  swapped     a different sound at the same times
Every question has a correct answer per condition, so answers can be graded by code.
"""
import json
import os
import random
import subprocess
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(os.getenv("VIDEOBENCH_HOME", ROOT))
FAKE = os.getenv("VIDEOBENCH_FAKE") == "1"
CLIPS = WORK / "clips"
W, H, SR = 640, 360, 16000

COLORS = {"red": (220, 40, 40), "blue": (40, 90, 230), "green": (40, 170, 70), "yellow": (240, 210, 40),
          "purple": (150, 60, 190)}
SHAPES = ["circle", "square", "triangle"]
LABELS = [f"{c} {s}" for c in COLORS for s in SHAPES]
SOUNDS = ["dog", "glass", "knock", "applause", "laugh", "phone"]
SOUND_NAME = {"dog": "dog barking", "glass": "glass breaking", "knock": "knocking", "applause": "applause",
              "laugh": "laughter", "phone": "phone ringing"}
SOURCE_VISIBLE = {"dog": "a dog", "glass": "a drinking glass", "knock": "a door", "applause": "people clapping",
                  "laugh": "a person", "phone": "a telephone"}
CONDITIONS = ["av", "video_only", "shifted", "swapped"]
SLOTS = [(80 + 96 * c, 70 + 110 * r) for r in range(3) for c in range(6)]


# ---------------------------------------------------------------- drawing
_yy, _xx = np.mgrid[0:H, 0:W]


def mask(shape, cx, cy, r=34):
    if shape == "circle":
        return (_xx - cx) ** 2 + (_yy - cy) ** 2 <= r * r
    if shape == "square":
        return (np.abs(_xx - cx) <= r * 0.85) & (np.abs(_yy - cy) <= r * 0.85)
    rel = (_yy - (cy - r)) / (2 * r)   # triangle pointing up
    return (rel >= 0) & (rel <= 1) & (np.abs(_xx - cx) <= rel * r)


def render(objects, duration, fps, out):
    """objects: dicts label, slot, start, end (None = until the end), flashes [times]. Writes a silent mp4."""
    ffmpeg = ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "23", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    masks = {id(o): mask(o["label"].split()[1], *SLOTS[o["slot"]]) for o in objects}
    for k in range(int(round(duration * fps))):
        t = k / fps
        frame = np.full((H, W, 3), 118, dtype=np.uint8)
        for o in objects:
            if o["start"] <= t and (o["end"] is None or t < o["end"]):
                flash = any(f <= t < f + 0.4 for f in o.get("flashes", []))
                frame[masks[id(o)]] = (255, 255, 255) if flash else COLORS[o["label"].split()[0]]
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg failed while rendering video.")


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


# ---------------------------------------------------------------- sound
def load_sounds(cfg):
    """Event sounds from ListenBench's assets (built there with ElevenLabs), trimmed and level-matched."""
    out = {}
    src = (ROOT / cfg["sounds_from"]).resolve()
    for key in SOUNDS:
        p = next((q for q in (src / f"{key}.mp3", src / f"{key}.wav") if q.exists()), None)
        if p is None or FAKE:
            t = np.arange(int(1.0 * SR)) / SR   # stand-in tone for tests only
            y = 0.3 * np.sin(2 * np.pi * (300 + 120 * SOUNDS.index(key)) * t) * np.exp(-3 * t)
            if p is None and not FAKE:
                raise SystemExit(f"Missing {key} sound. Build ListenBench first (cd ../listen; python -m listenbench build).")
        else:
            import librosa
            y, _ = librosa.load(str(p), sr=SR, mono=True)
            y, _ = librosa.effects.trim(y, top_db=40)
        y = y[: int(cfg["max_sound_s"] * SR)]
        fade = min(len(y), int(0.05 * SR))
        y[-fade:] *= np.linspace(1, 0, fade)
        out[key] = (0.2 * y / (np.sqrt(np.mean(y ** 2)) + 1e-9)).astype(np.float32)
    return out


def write_wav(y, path):
    y = np.clip(y, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def mix(sounds, events, duration):
    y = np.zeros(int(duration * SR), dtype=np.float32)
    for key, t in events:
        s, i = sounds[key], int(t * SR)
        if 0 <= i < len(y):
            n = min(len(s), len(y) - i)
            y[i:i + n] += s[:n]
    return y


def mux(video, audio_wav, out):
    if audio_wav is None:
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(video), "-c", "copy", "-an", str(out)], check=True)
    else:
        subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio_wav), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "96k", "-shortest", str(out)], check=True)


# ---------------------------------------------------------------- question helpers
def q(qid, text, kind, truth, tag, options=None, tol=None, time_truth=None):
    """truth: {condition: answer}. kind: choice | number | count. tag: visual | audio | joint | sync."""
    return dict(qid=qid, text=text, kind=kind, truth=truth, tag=tag, options=options, tol=tol, time_truth=time_truth)


def same(v):
    return {c: v for c in CONDITIONS}


def nearest(objs, t, within=0.6):
    best = min(objs, key=lambda o: abs(o["start"] - t))
    return best["label"] if abs(best["start"] - t) <= within else "none"


# ---------------------------------------------------------------- clip designs
def design_temporal(rnd, i, cfg):
    labels = rnd.sample(LABELS, 4)
    slots = rnd.sample(range(len(SLOTS)), 4)
    t, objs = 1.0, []
    for lab, sl in zip(labels, slots):
        objs.append(dict(label=lab, slot=sl, start=round(t, 2), end=None))
        t += rnd.uniform(2.6, 3.4)
    gone = rnd.choice(objs[:3])
    gone["end"] = round(objs[-1]["start"] + rnd.uniform(2.0, 2.8), 2)
    dur = round(gone["end"] + 2.5, 1)
    k = rnd.choice(objs)
    snd, other = rnd.sample(SOUNDS, 2)
    ts = k["start"]
    b, a = rnd.sample(objs, 2)
    opts = labels + ["none", "no_audio", "cannot_tell"]
    qs = [
        q("q1", "Which shape appears first?", "choice", same(objs[0]["label"]), "visual", labels + ["cannot_tell"], time_truth=objs[0]["start"]),
        q("q2", f"At what second does the {b['label']} first appear?", "number", same(b["start"]), "visual", tol=cfg["time_tolerance_s"], time_truth=b["start"]),
        q("q3", "Which shape disappears before the end?", "choice", same(gone["label"]), "visual", labels + ["none", "cannot_tell"], time_truth=gone["end"]),
        q("q4", "How many shapes are visible in the last frame?", "count", same(3), "visual"),
        q("q5", f"Does the {a['label']} appear before or after the {b['label']}?", "choice",
          same("before" if a["start"] < b["start"] else "after"), "visual", ["before", "after", "cannot_tell"]),
        q("q6", "Which shape appears at the same moment as the sound?", "choice",
          dict(av=k["label"], video_only="no_audio", shifted=nearest(objs, ts + cfg["shift_s"]), swapped=k["label"]),
          "joint", opts, time_truth=ts),
        q("q7", "What sound is heard?", "choice",
          dict(av=SOUND_NAME[snd], video_only="no_audio", shifted=SOUND_NAME[snd], swapped=SOUND_NAME[other]),
          "audio", [SOUND_NAME[s] for s in SOUNDS] + ["no_audio", "cannot_tell"]),
    ]
    return dict(cid=f"T{i:02d}", suite="temporal", duration=dur, objects=objs,
                sound=dict(av=[(snd, ts)], shifted=[(snd, ts + cfg["shift_s"])], swapped=[(other, ts)]), questions=qs)


def design_sync(rnd, i, cfg):
    lab = rnd.choice(LABELS)
    flashes, t = [], rnd.uniform(1.5, 2.5)
    for _ in range(3):
        flashes.append(round(t, 2)); t += rnd.uniform(2.6, 3.4)
    dur = round(flashes[-1] + 3.0, 1)
    others = rnd.sample([l for l in LABELS if l != lab], 2)
    sl = rnd.sample(range(len(SLOTS)), 3)
    objs = [dict(label=lab, slot=sl[0], start=0.0, end=None, flashes=flashes)] + \
           [dict(label=o, slot=s, start=0.0, end=None) for o, s in zip(others, sl[1:])]
    snd, other = rnd.sample(["knock", "glass", "phone", "dog"], 2)
    qs = [
        q("q1", f"How many times does the {lab} flash white?", "count", same(3), "visual"),
        q("q2", f"Is the sound synchronized with the flashes of the {lab} (each sound starts when a flash starts)?", "choice",
          dict(av="yes", video_only="no_audio", shifted="no", swapped="yes"), "sync", ["yes", "no", "no_audio", "cannot_tell"]),
        q("q3", "What sound is heard?", "choice",
          dict(av=SOUND_NAME[snd], video_only="no_audio", shifted=SOUND_NAME[snd], swapped=SOUND_NAME[other]),
          "audio", [SOUND_NAME[s] for s in SOUNDS] + ["no_audio", "cannot_tell"]),
        q("q4", f"At what second does the {lab} flash for the first time?", "number", same(flashes[0]), "visual",
          tol=cfg["time_tolerance_s"], time_truth=flashes[0]),
        q("q5", "At what second is the sound first heard?", "number",
          dict(av=flashes[0], video_only="no_audio", shifted=round(flashes[0] + cfg["shift_s"], 2), swapped=flashes[0]),
          "audio", tol=cfg["time_tolerance_s"]),
    ]
    return dict(cid=f"S{i:02d}", suite="sync", duration=dur, objects=objs,
                sound=dict(av=[(snd, f) for f in flashes], shifted=[(snd, f + cfg["shift_s"]) for f in flashes],
                           swapped=[(other, f) for f in flashes]), questions=qs)


def design_halluc(rnd, i, cfg):
    labs = rnd.sample(LABELS, 4)
    present, absent = labs[:3], labs[3]
    sl = rnd.sample(range(len(SLOTS)), 3)
    objs = [dict(label=l, slot=s, start=0.0, end=None) for l, s in zip(present, sl)]
    snd, other = rnd.sample(SOUNDS, 2)
    ts = round(rnd.uniform(2.0, 6.0), 2)
    dur = 10.0
    heard = f"Is the sound of {SOUND_NAME[snd]} audible?"
    qs = [
        q("q1", f"Is {SOURCE_VISIBLE[snd]} visible in the video?", "choice", same("no"), "visual", ["yes", "no", "cannot_tell"]),
        q("q2", heard, "choice", dict(av="yes", video_only="no_audio", shifted="yes", swapped="no"), "audio",
          ["yes", "no", "no_audio", "cannot_tell"]),
        q("q3", f"Is a {absent} visible at any point?", "choice", same("no"), "visual", ["yes", "no", "cannot_tell"]),
        q("q4", f"Is a {present[0]} visible at any point?", "choice", same("yes"), "visual", ["yes", "no", "cannot_tell"]),
        q("q5", "At what second does the sound start?", "number",
          dict(av=ts, video_only="no_audio", shifted=round(ts + cfg["shift_s"], 2), swapped=ts), "audio", tol=cfg["time_tolerance_s"]),
        q("q6", "Which shape produces the sound?", "choice", same("cannot_tell"), "joint",
          present + ["none", "no_audio", "cannot_tell"]),
    ]
    q6 = qs[-1]
    q6["truth"]["video_only"] = "no_audio"
    q6["accept"] = {"av": ["none"], "shifted": ["none"], "swapped": ["none"]}   # no shape makes a sound
    return dict(cid=f"H{i:02d}", suite="halluc", duration=dur, objects=objs,
                sound=dict(av=[(snd, ts)], shifted=[(snd, ts + cfg["shift_s"])], swapped=[(other, ts)]), questions=qs)


def design_long(rnd, i, cfg, dur):
    n = max(8, int(dur / 7))
    labs = rnd.sample(LABELS, min(n, len(LABELS)))
    n = len(labs)
    times = sorted(round(x, 1) for x in np.linspace(2, dur - 6, n))
    objs, free = [], list(range(len(SLOTS)))
    rnd.shuffle(free)
    for lab, t in zip(labs, times):
        o = dict(label=lab, slot=free.pop(), start=t, end=None)
        objs.append(o)
        if len([x for x in objs if x["end"] is None or x["end"] > t]) > 4:   # keep at most 4 visible
            old = next(x for x in objs if x["end"] is None and x is not o)
            old["end"] = round(t - 0.5, 1)
            free.insert(0, old["slot"])
    k = rnd.randrange(1, max(2, n // 4))        # sound early in the clip, between two appearances
    ts = round((objs[k - 1]["start"] + objs[k]["start"]) / 2, 1)
    snd = rnd.choice(SOUNDS)
    qs = [
        q("q1", "Which shape appears first?", "choice", same(objs[0]["label"]), "visual", labs + ["cannot_tell"], time_truth=objs[0]["start"]),
        q("q2", "At what second is the sound heard?", "number", same(ts), "audio", tol=cfg["time_tolerance_s"] * 2, time_truth=ts),
        q("q3", "How many different shapes appear in total?", "count", same(n), "visual"),
        q("q4", "Which shape appears first after the sound?", "choice", same(objs[k]["label"]), "joint", labs + ["cannot_tell"], time_truth=objs[k]["start"]),
        q("q5", "Which shape appears last?", "choice", same(objs[-1]["label"]), "visual", labs + ["cannot_tell"], time_truth=objs[-1]["start"]),
    ]
    return dict(cid=f"L{i:02d}", suite=f"long_{int(dur)}s", duration=float(dur), objects=objs,
                sound=dict(av=[(snd, ts)]), questions=qs, conditions=["av"])


def designs(cfg):
    rnd = random.Random(cfg["seed"])
    n = cfg["clips_per_suite"]
    out = [design_temporal(rnd, i, cfg) for i in range(n)] + [design_sync(rnd, i, cfg) for i in range(n)] + \
          [design_halluc(rnd, i, cfg) for i in range(n)]
    for j, dur in enumerate(cfg["long_durations_s"]):
        for i in range(cfg["long_clips_per_duration"]):
            out.append(design_long(rnd, j * 10 + i, cfg, dur))
    return out


def build(cfg):
    CLIPS.mkdir(parents=True, exist_ok=True)
    sounds = load_sounds(cfg)
    man = []
    for d in designs(cfg):
        silent = CLIPS / f"{d['cid']}_silent.mp4"
        conds = d.get("conditions", CONDITIONS)
        if any(not (CLIPS / f"{d['cid']}-{c}.mp4").exists() for c in conds) and not silent.exists():
            render(d["objects"], d["duration"], cfg["render_fps"], silent)
        for cond in conds:
            uid = f"{d['cid']}-{cond}"
            out = CLIPS / f"{uid}.mp4"
            if not out.exists():
                wav = None
                if cond != "video_only":
                    wav = CLIPS / f"{uid}.wav"
                    write_wav(mix(sounds, d["sound"][cond], d["duration"]), wav)
                mux(silent, wav, out)
                if wav:
                    wav.unlink()
            man.append(dict(uid=uid, cid=d["cid"], suite=d["suite"], condition=cond, duration=d["duration"],
                            objects=d["objects"], sound=d["sound"].get(cond, []),
                            questions=[dict(qq, truth=qq["truth"][cond], accept=qq.get("accept", {}).get(cond, []))
                                       for qq in d["questions"]]))
        silent.unlink(missing_ok=True)
    with open(CLIPS / "manifest.jsonl", "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    (WORK / "results").mkdir(exist_ok=True)
    (WORK / "results" / "manifest.jsonl").write_text((CLIPS / "manifest.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Built {len(man)} clips from {len(set(m['cid'] for m in man))} scenes "
          f"({sum(m['duration'] for m in man) / 60:.1f} min) in video/clips/. Questions: {sum(len(m['questions']) for m in man)}.")
    return man


def manifest():
    p = CLIPS / "manifest.jsonl"
    if not p.exists():
        raise SystemExit("No clips yet. Run: python -m videobench build")
    return [json.loads(l) for l in open(p)]
