import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from listenbench.report import diarization, grade  # noqa: E402

CFG = {"onset_tolerance_s": 0.5, "event_window_s": 1.5, "trailing_gap_s": 0.5}


def clip(**kw):
    base = dict(uid="x", suite="L1", item="S1-00", condition="clean", reference="the cat sat",
                speech_start=1.0, speech_end=2.0, event=None, turns=None)
    base.update(kw)
    return base


def w(t, s, e, spk=None):
    return dict(text=t, start=s, end=e, speaker=spk)


def test_perfect_transcript():
    g = grade(clip(), dict(system="s", run=0, text="The cat sat.", words=[w("The", 1.0, 1.2), w("cat", 1.3, 1.5), w("sat.", 1.6, 2.0)], events=[]), CFG)
    assert g["wer"] == 0 and g["onset_ok"] == 1 and g["any_insertion"] == 0 and g["false_event"] == 0


def test_words_in_trailing_silence_count_as_invented():
    words = [w("the", 1.0, 1.2), w("cat", 1.3, 1.5), w("sat", 1.6, 2.0), w("Thank", 3.5, 3.7), w("you.", 3.7, 3.9)]
    g = grade(clip(), dict(system="s", run=0, text="the cat sat Thank you.", words=words, events=[]), CFG)
    assert g["inserted_words"] == 2 and g["any_insertion"] == 1


def test_no_speech_clip():
    c = clip(suite="L3", item="silence_5s", condition="silence", reference="", speech_start=None, speech_end=None)
    assert grade(c, dict(system="s", run=0, text="", words=[], events=[]), CFG)["hallucinated"] == 0
    g = grade(c, dict(system="s", run=0, text="Thanks for watching!", words=[w("Thanks", 0, 1)], events=[]), CFG)
    assert g["hallucinated"] == 1


def test_event_needs_right_label_and_time():
    ev = dict(key="dog", start=1.0, end=2.0, keywords=["dog", "bark"])
    c = clip(suite="L4", item="dog-before", condition="before", speech_start=3.0, speech_end=4.0, event=ev)
    base = dict(system="s", run=0, text="the cat sat", words=[w("the", 3.0, 3.2), w("cat", 3.3, 3.5), w("sat", 3.6, 4.0)])
    assert grade(c, dict(base, events=[dict(text="(dog barking)", start=1.1, end=2)]), CFG)["event_correct"] == 1
    assert grade(c, dict(base, events=[dict(text="(applause)", start=1.1, end=2)]), CFG)["event_correct"] == 0
    assert grade(c, dict(base, events=[dict(text="(dog barking)", start=6.0, end=7)]), CFG)["event_correct"] == 0
    assert "event_correct" not in grade(c, dict(base, events=[]), CFG, tags_events=False)


def test_diarization_label_mapping():
    turns = [dict(speaker="A", start=0, end=1), dict(speaker="B", start=1.2, end=2)]
    words = [w("a", 0.1, 0.5, "speaker_7"), w("b", 0.5, 0.9, "speaker_7"), w("c", 1.3, 1.8, "speaker_2")]
    n, acc = diarization(words, turns)
    assert n == 2 and acc == 1.0
    n, acc = diarization([dict(x, speaker="speaker_0") for x in words], turns)
    assert n == 1 and abs(acc - 2 / 3) < 1e-9


def test_fake_pipeline(tmp_path):
    env = dict(os.environ, LISTENBENCH_FAKE="1", LISTENBENCH_HOME=str(tmp_path))
    for cmd in (["build", "-y"], ["transcribe", "--pilot", "-y"], ["report"]):
        subprocess.run([sys.executable, "-m", "listenbench", *cmd], cwd=ROOT, env=env, check=True, capture_output=True)
    man = [json.loads(l) for l in open(tmp_path / "clips" / "manifest.jsonl")]
    assert {m["suite"] for m in man} == {"L1", "L3", "L4", "L5"}
    assert len([m for m in man if m["suite"] == "L1"]) == 30 * 4
    assert (tmp_path / "results" / "summary.md").exists()
    assert np.all([m["duration"] > 0 for m in man])
