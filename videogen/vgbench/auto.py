"""Automatic measures, computed from the frames. They are cheap checks next to the human ratings, not a replacement:
the report shows how well each one agrees with the ratings.

- flicker: mean change between consecutive frames (0-1). High values mean shimmering or boiling textures.
- pops: frames where the change is more than 4x the clip's median change (objects appearing, cuts, glitches).
- palette distance: how different two clips' colours are (0 = same colour mix, 1 = nothing in common).
  Shots of one storyboard should be closer to each other than to other storyboards.
- repeat difference: mean pixel difference between a clip and its same-seed repeat (0 = identical).
"""
import csv

import numpy as np

from .core import WORK, clip_path
from .items import clips

SIZE = (64, 36)


def frames(path):
    import imageio_ffmpeg
    gen = imageio_ffmpeg.read_frames(str(path))
    meta = next(gen)
    w, h = meta["size"]
    ys, xs = np.linspace(0, h, SIZE[1] + 1).astype(int), np.linspace(0, w, SIZE[0] + 1).astype(int)
    fr = []
    for b in gen:                                    # shrink each frame to 64x36 by block averages as it is read
        f = np.frombuffer(b, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        f = np.add.reduceat(np.add.reduceat(f, ys[:-1], axis=0), xs[:-1], axis=1)
        fr.append(f / np.outer(np.diff(ys), np.diff(xs))[..., None])
    return np.stack(fr), meta


def hist(fr):
    q = (fr * 7.999).astype(int)                    # 8 levels per channel -> 512 bins
    idx = q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]
    h = np.bincount(idx.ravel(), minlength=512).astype(float)
    return h / h.sum()


def palette_distance(a, b):
    return float(1 - np.minimum(a, b).sum())       # 1 - histogram intersection


def run(cfg):
    rows, cache = [], {}
    for m in cfg["models"]:
        for c in clips(cfg):
            p = clip_path(m["name"], c["cid"])
            if not p.exists():
                continue
            fr, meta = frames(p)
            d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2, 3)) if len(fr) > 1 else np.zeros(1)
            cache[(m["name"], c["cid"])] = fr
            rows.append(dict(model=m["name"], cid=c["cid"], sb=c["sb"], kind=c["kind"], seconds=round(meta.get("duration", 0), 2),
                             fps=meta.get("fps"), has_audio=bool(meta.get("audio_codec")), flicker=round(float(d.mean()), 5),
                             pops=int((d > 4 * max(np.median(d), 1e-4)).sum()), hist=hist(fr)))
    # cross-shot palette distance: within a storyboard vs between storyboards
    for r in rows:
        r["palette_within"] = r["palette_between"] = r["repeat_diff"] = ""
    by = {(r["model"], r["cid"]): r for r in rows}
    for r in rows:
        if r["kind"] != "shot":
            continue
        same = [o for o in rows if o["model"] == r["model"] and o["kind"] == "shot" and o["sb"] == r["sb"] and o is not r]
        other = [o for o in rows if o["model"] == r["model"] and o["kind"] == "shot" and o["sb"] != r["sb"]]
        if same:
            r["palette_within"] = round(np.mean([palette_distance(r["hist"], o["hist"]) for o in same]), 4)
        if other:
            r["palette_between"] = round(np.mean([palette_distance(r["hist"], o["hist"]) for o in other]), 4)
        if r["cid"].endswith("-1"):
            rep = by.get((r["model"], r["cid"] + "r"))
            if rep is not None:
                a, b = cache[(r["model"], r["cid"])], cache[(r["model"], rep["cid"])]
                n = min(len(a), len(b))
                r["repeat_diff"] = round(float(np.abs(a[:n] - b[:n]).mean()), 5)
    out = WORK / "results"
    out.mkdir(exist_ok=True)
    keys = [k for k in rows[0] if k != "hist"] if rows else []
    with open(out / "auto.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote videogen/results/auto.csv ({len(rows)} clips).")
    return rows
