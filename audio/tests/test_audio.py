import numpy as np
import pandas as pd

from audiobench.generate import items, strip_tags
from audiobench.listening import bradley_terry
from audiobench.metrics import chunk_wer, s2_check, wer


def test_items_and_tags():
    its = items()
    assert len({i["uid"] for i in its}) == len(its) == 30 + 25 + 15 + 12 + 1
    assert strip_tags("[whispers] Don't wake her.") == "Don't wake her."


def test_wer_and_s2():
    assert wer("The cat sat.", "the cat sat") == 0
    assert s2_check(["the speed limit is fifty kilometers per hour"], "The speed limit is 50 km per hour")[1] >= 0
    ok, best = s2_check(["doctor smith lives on smith drive"], "Doctor Smith lives on Smith Drive.")
    assert ok == 1 and best == 0
    ok, _ = s2_check(["doctor smith lives on smith drive"], "Doctor Smith lives on Smith Doctor.")
    assert ok == 0


def test_chunk_wer_finds_skipped_section():
    ref = " ".join(f"word{i}" for i in range(100))
    hyp = " ".join(f"word{i}" for i in range(100) if not 50 <= i < 70)
    ch = chunk_wer(ref, hyp, chunk_chars=60)
    assert max(ch) > 0.5 and ch[0] == 0


def test_bradley_terry_order():
    rows = [dict(ma="a", mb="b", choice="A")] * 8 + [dict(ma="a", mb="b", choice="B")] * 2 + \
           [dict(ma="b", mb="c", choice="A")] * 8 + [dict(ma="b", mb="c", choice="B")] * 2
    th = bradley_terry(pd.DataFrame(rows), ["a", "b", "c"])
    assert th[0] > th[1] > th[2] and abs(np.mean(th) - 1500) < 1
