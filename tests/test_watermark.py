"""Laws of the green-list watermark core. No model, no torch.

Goldens were computed on the pre-refactor module (commit 6a78bae); they
pin the hash scheme so stored z-scores stay valid.
"""

import itertools
import math
import random
import statistics
import sys
import types
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

import watermark as wm

V, GAMMA, KEY = 1000, 0.25, 0
S = wm.Scheme(V, GAMMA, KEY)


def naive_z(ids, vocab, gamma, key):
    """Oracle: the pre-refactor per-pair loop, O(T * V)."""
    greens = sum(cur in wm.green_set(prev, vocab, gamma, key)
                 for prev, cur in itertools.pairwise(ids))
    t = len(ids) - 1
    return (greens - gamma * t) / math.sqrt(t * gamma * (1 - gamma)), greens


def random_ids(seed, n, vocab=V):
    rng = random.Random(seed)
    return [rng.randrange(vocab) for _ in range(n)]


def green_walk(seed, t, scheme=S):
    """Sequence whose every next token is drawn from the green list."""
    rng = random.Random(seed)
    ids = [rng.randrange(scheme.vocab_size)]
    for _ in range(t):
        ids.append(rng.choice(wm.green_ids(scheme, ids[-1])))
    return ids


# ---------------------------------------------------------- hash scheme pin

def test_golden_green_set_small():
    assert sorted(wm.green_set(7, 50, 0.25, 0)) == [
        0, 1, 3, 4, 9, 14, 20, 21, 22, 24, 40, 47]


def test_golden_green_set_qwen_vocab():
    g = sorted(wm.green_set(42, 151936, 0.25, 42))
    assert len(g) == 37984
    assert g[:10] == [6, 11, 12, 13, 19, 24, 28, 33, 35, 39]


def test_golden_z():
    rng = random.Random(1)
    seq = [rng.randrange(50) for _ in range(30)]
    assert tuple(wm.z_score(seq, 50, 0.25, 0)) == (
        -0.9649012813540153, 5, 29)


# ---------------------------------------------------------- green list laws

def test_green_set_deterministic():
    for prev in (0, 1, 999, -3):
        assert wm.green_set(prev, V, GAMMA, KEY) == wm.green_set(
            prev, V, GAMMA, KEY)


def test_green_set_depends_on_key_and_prev():
    assert wm.green_set(5, V, GAMMA, 0) != wm.green_set(5, V, GAMMA, 1)
    assert wm.green_set(5, V, GAMMA, 0) != wm.green_set(6, V, GAMMA, 0)


@pytest.mark.parametrize("vocab", [1, 2, 3, 7, 10, 999, 1000, 1001])
@pytest.mark.parametrize("gamma", [0.01, 0.1, 0.25, 0.5, 0.9])
def test_green_set_size_within_one(vocab, gamma):
    g = wm.green_set(5, vocab, gamma, KEY)
    assert abs(len(g) - gamma * vocab) < 1
    assert all(0 <= i < vocab for i in g)


def test_green_ids_distinct():
    ids = wm.green_ids(S, 3)
    assert len(ids) == len(set(ids)) == S.green_size


# ----------------------------------------------------------- smart constructor

@pytest.mark.parametrize("vocab,gamma", [
    (0, 0.25), (-1, 0.25), (True, 0.25), (10.0, 0.25),
    (V, 0.0), (V, 1.0), (V, -0.1), (V, 1.5), (V, float("nan"))])
def test_scheme_rejects(vocab, gamma):
    with pytest.raises(ValueError):
        wm.Scheme(vocab, gamma, KEY)


def test_z_score_rejects_degenerate_gamma():
    # Old code: ZeroDivisionError at gamma 0 or 1. Now one ValueError.
    for gamma in (0.0, 1.0):
        with pytest.raises(ValueError):
            wm.z_score([1, 2, 3], V, gamma, KEY)


# ----------------------------------------------------------- detector laws

@pytest.mark.parametrize("n", [0, 1])
def test_short_sequence_scores_nothing(n):
    # Finding: old code returned T = len(ids) = 1 for one token, though
    # no pair was scored. T counts scored pairs: max(0, n - 1).
    assert tuple(wm.z_score(random_ids(0, n), V, GAMMA, KEY)) == (0.0, 0, 0)


def test_scored_pairs_count():
    for n in (2, 3, 50):
        _, g, t = wm.z_score(random_ids(n, n), V, GAMMA, KEY)
        assert t == n - 1
        assert 0 <= g <= t


def test_grouped_detector_equals_naive_oracle():
    for seed in range(20):
        ids = random_ids(seed, 60, vocab=40)  # small vocab: many repeats
        z, g, _ = wm.z_score(ids, 40, GAMMA, KEY)
        nz, ng = naive_z(ids, 40, GAMMA, KEY)
        assert (z, g) == (nz, ng)


def test_null_z_mean_near_zero():
    # Uniform ids: each pair green w.p. k/V = gamma exactly (V * gamma is
    # an integer), pairs independent, so z ~ mean 0, sd 1. Mean of 300
    # draws has sd 1/sqrt(300) = 0.058; bound at 4 sd.
    zs = [wm.z_score(random_ids(s, 101), V, GAMMA, KEY).z
          for s in range(300)]
    assert abs(statistics.mean(zs)) < 4 / math.sqrt(300)
    assert 0.8 < statistics.stdev(zs) < 1.2


@pytest.mark.parametrize("t", [16, 64, 256])
def test_all_green_z_grows_as_sqrt_t(t):
    # All T pairs green: z = sqrt(T) * sqrt((1 - gamma) / gamma).
    z, g, scored = wm.z_score(green_walk(t, t), V, GAMMA, KEY)
    assert g == scored == t
    assert z == pytest.approx(math.sqrt(t * (1 - GAMMA) / GAMMA))


def test_z_ratio_across_lengths_is_sqrt():
    z = {t: wm.z_score(green_walk(1, t), V, GAMMA, KEY).z
         for t in (25, 100, 400)}
    assert z[100] / z[25] == pytest.approx(2.0)
    assert z[400] / z[100] == pytest.approx(2.0)


def test_unique_scores_each_pair_once():
    ids = [3, 4] * 50  # two distinct pairs, repeated
    d = wm.detect(S, ids, unique=True)
    assert d.scored == 2
    assert wm.detect(S, ids).scored == 99


# ------------------------------------------------------- truncation laws

CASES = [([], []), ([1], []), ([1, 2, 3], [4, 5]), ([1, 2], [3, 4]),
         (list(range(10)), [7])]


@pytest.mark.parametrize("a,b", CASES)
def test_truncate_idempotent(a, b):
    once = wm.truncate_matched(a, b)
    assert wm.truncate_matched(*once) == once


@pytest.mark.parametrize("a,b", CASES)
def test_truncate_symmetric(a, b):
    x, y = wm.truncate_matched(a, b)
    assert wm.truncate_matched(b, a) == (y, x)


@pytest.mark.parametrize("a,b", CASES)
def test_truncate_equal_length_prefixes(a, b):
    x, y = wm.truncate_matched(a, b)
    assert len(x) == len(y) == min(len(a), len(b))
    assert a[:len(x)] == x and b[:len(y)] == y


# ------------------------------------------------- adapter, torch faked

def fake_torch():
    mod = types.ModuleType("torch")
    mod.long = np.int64
    mod.tensor = lambda data, dtype, device: np.asarray(data, dtype=dtype)
    return mod


def test_processor_biases_green_ids_per_row(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", fake_torch())
    proc = wm.GreenListProcessor(V, GAMMA, 2.0, KEY)
    input_ids = np.array([[9, 5], [9, 7]])
    scores = np.zeros((2, V))
    out = proc(input_ids, scores)
    for row, prev in enumerate((5, 7)):
        green = wm.green_set(prev, V, GAMMA, KEY)
        expect = np.array([2.0 if i in green else 0.0 for i in range(V)])
        assert np.array_equal(out[row], expect)


def test_processor_then_detector_all_green(monkeypatch):
    # Infinite delta forces green tokens: greedy decoding under the
    # processor yields an all-green sequence.
    monkeypatch.setitem(sys.modules, "torch", fake_torch())
    proc = wm.GreenListProcessor(V, GAMMA, 1e9, KEY)
    rng = np.random.default_rng(0)
    ids = [11]
    for _ in range(40):
        scores = rng.normal(size=(1, V))
        ids.append(int(np.argmax(proc(np.array([ids]), scores)[0])))
    assert wm.z_score(ids, V, GAMMA, KEY).greens == 40
