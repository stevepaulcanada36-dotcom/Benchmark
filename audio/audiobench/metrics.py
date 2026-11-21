"""Automatic audio metrics: Whisper WER, S2 pass/fail, S5 chunk drift, UTMOS, speaker similarity, duration.
Transcription runs locally, so it is free and independent of ElevenLabs (no vendor judging itself)."""
import json
import os

import jiwer
import numpy as np

from .generate import FAKE, ROOT, audio_dir, items

_norm = None


def normalize(s):
    global _norm
    if _norm is None:
        from whisper_normalizer.english import EnglishTextNormalizer
        _norm = EnglishTextNormalizer()
    return " ".join(_norm(s).split())


def wer(ref, hyp):
    r, h = normalize(ref), normalize(hyp)
    if not r:
        return np.nan
    return jiwer.wer(r, h) if h else 1.0


def s2_check(accepted, hyp):
    best = min(wer(a, hyp) for a in accepted)
    return int(best == 0), best


def chunk_wer(ref, hyp, chunk_chars=200):
    """Splits the reference into ~chunk_chars word ranges and counts aligned errors per range."""
    r_words, h = normalize(ref).split(), normalize(hyp)
    bounds, cur, start = [], 0, 0
    for i, w in enumerate(r_words):
        cur += len(w) + 1
        if cur >= chunk_chars:
            bounds.append((start, i + 1)); start, cur = i + 1, 0
    if start < len(r_words):
        bounds.append((start, len(r_words)))
    out = jiwer.process_words(" ".join(r_words), h or "<empty>")
    err = np.zeros(len(r_words))
    for a in out.alignments[0]:
        if a.type in ("substitute", "delete"):
            err[a.ref_start_idx:a.ref_end_idx] += 1
        elif a.type == "insert":
            err[min(a.ref_start_idx, len(r_words) - 1)] += a.hyp_end_idx - a.hyp_start_idx
    return [float(err[s:e].sum() / (e - s)) for s, e in bounds]


class Models:
    def __init__(self, cfg):
        self.cfg = cfg["metrics"]
        self._asr = self._utmos = self._spk = None

    def asr(self, path, ref):
        if FAKE:   # perturb the reference so WER is non-trivial in tests
            words = ref.split()
            rnd = np.random.default_rng(abs(hash(path)) % 2**32)
            return " ".join(w for w in words if rnd.random() > 0.05)
        if self._asr is None:
            from faster_whisper import WhisperModel
            dev = self.cfg["asr_device"]
            if dev == "auto":
                try:
                    import ctranslate2
                    dev = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
                except Exception:  # noqa: BLE001
                    dev = "cpu"
            self._asr = WhisperModel(self.cfg["asr_model"], device=dev,
                                     compute_type="float16" if dev == "cuda" else "int8")
        segs, _ = self._asr.transcribe(str(path), language="en", beam_size=5, temperature=0.0,
                                       condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs)

    def load16k(self, path):
        import librosa
        y, _ = librosa.load(str(path), sr=16000, mono=True)
        return y

    def utmos(self, path):
        if FAKE or not self.cfg["utmos"]:
            return np.nan
        import torch
        if self._utmos is None:
            self._utmos = torch.hub.load("tarepan/SpeechMOS:v1.2.0", "utmos22_strong", trust_repo=True)
        wav = torch.from_numpy(self.load16k(path)).unsqueeze(0)
        with torch.no_grad():
            return float(self._utmos(wav, 16000).item())

    def embed(self, path):
        if FAKE or not self.cfg["speaker_similarity"]:
            return None
        import torch
        if self._spk is None:
            from speechbrain.inference.speaker import EncoderClassifier
            self._spk = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb",
                                                       savedir=str(ROOT / ".cache" / "ecapa"))
        with torch.no_grad():
            e = self._spk.encode_batch(torch.from_numpy(self.load16k(path)).unsqueeze(0))
        return e.squeeze().numpy()

    def duration(self, path):
        import soundfile as sf
        try:
            return float(sf.info(str(path)).duration)
        except Exception:  # noqa: BLE001
            return float(len(self.load16k(path)) / 16000)


def compute(cfg, pilot=False):
    d = audio_dir(pilot)
    clips = [json.loads(l) for l in open(d / "clips.jsonl")] if (d / "clips.jsonl").exists() else []
    if not clips:
        raise SystemExit("No clips yet. Run: python -m audiobench run --pilot")
    out_path = d / "metrics.jsonl"
    done = {json.loads(l)["path"] for l in open(out_path)} if out_path.exists() else set()
    by_uid = {it["uid"]: it for it in items()}
    mods = Models(cfg)
    emb_dir = d / "embeddings"
    emb_dir.mkdir(exist_ok=True)
    todo = [c for c in {c["path"]: c for c in clips}.values() if c["path"] not in done]
    print(f"{len(todo)} clips to score (ASR model: {cfg['metrics']['asr_model']}).")
    for k, c in enumerate(todo, 1):
        it, path = by_uid[c["uid"]], ROOT / c["path"]
        hyp = mods.asr(path, it["reference"])
        rec = dict(path=c["path"], uid=c["uid"], suite=c["suite"], run=c["run"], model_label=c["model_label"],
                   transcript=hyp, wer=wer(it["reference"], hyp), utmos=mods.utmos(path),
                   duration_s=mods.duration(path), chars=c["chars"], ttfa_s=c["ttfa_s"], total_s=c["total_s"],
                   credits_est=c["credits_est"])
        rec["sec_per_char"] = rec["duration_s"] / max(1, c["chars"])
        if it["suite"] == "S2":
            rec["s2_pass"], rec["s2_best_wer"] = s2_check(it["accepted"], hyp)
        if it["suite"] == "S5":
            rec["chunk_wer"] = chunk_wer(it["reference"], hyp, cfg["metrics"]["s5_chunk_chars"])
        e = mods.embed(path)
        if e is not None:
            np.save(emb_dir / (c["path"].replace("/", "__") + ".npy"), e)
        with open(out_path, "a") as f:
            f.write(json.dumps(rec, default=float) + "\n")
        if k % 10 == 0 or k == len(todo):
            print(f"  scored {k}/{len(todo)}")
    _speaker_similarity(cfg, d)


def _speaker_similarity(cfg, d):
    """Cosine similarity of each clip's ECAPA embedding to the centroid of the reference model's S1 clips."""
    emb_dir = d / "embeddings"
    files = list(emb_dir.glob("*.npy"))
    if not files:
        return
    ref_label = cfg["reference_model"]
    embs = {f.name[:-4].replace("__", "/"): np.load(f) for f in files}
    ref = [v for k, v in embs.items() if f"/{ref_label}/S1-" in k]
    if not ref:
        print(f"No S1 clips for reference model {ref_label}; skipping speaker similarity.")
        return
    c = np.mean(ref, axis=0)
    c /= np.linalg.norm(c)
    sims = {k: float(np.dot(v, c) / np.linalg.norm(v)) for k, v in embs.items()}
    (d / "speaker_similarity.json").write_text(json.dumps(sims, indent=0))
    print(f"Speaker similarity vs {ref_label} centroid written for {len(sims)} clips.")
