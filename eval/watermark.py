"""Green-list watermark (Kirchenbauer et al. 2023): generate + detect.

Generation: at each step, a hash of (key, previous token) seeds a split of
the vocabulary into a green list (fraction gamma). Green logits get a bias
of delta. Detection needs no model: count green tokens in a sequence and
report the z-score against the null (binomial with p = gamma).

    z = (G - gamma * T) / sqrt(T * gamma * (1 - gamma))

The ste-tax question: does an ASD-STE100 vocabulary constraint lower the
z-score at matched length? A small approved vocabulary cuts the entropy
the watermark hides in, so detection should weaken. This module is the
measurement tool, not the answer. Scheme and parameters: docs/watermark.md.

Layout: a pure core over integer sequences (stdlib only) and one adapter,
GreenListProcessor, the only code that touches torch. Sizes below: V =
vocabulary size (151936 for Qwen3), k = green-list size = max(1,
floor(gamma * V)), T = scored pairs = len(ids) - 1, D = distinct previous
tokens in a sequence (D <= min(T, V)).

Hash scheme (frozen; a change breaks every stored z-score): seed =
SHA-256 of the UTF-8 string f"{key}:{prev}"; green list =
random.Random(seed).sample(range(V), k). Not numpy: a numpy permutation
gives a different list for the same seed.
"""

import hashlib
import itertools
import math
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import NamedTuple


@dataclass(frozen=True, slots=True)
class Scheme:
    """Validated watermark parameters. The one smart constructor.

    Invariants: vocab_size >= 1; 0 < gamma < 1 (gamma 0 or 1 makes the
    z denominator zero; gamma > 1 asks for more green ids than exist).
    key: any value with a stable str(); the harness passes an int.
    """

    vocab_size: int
    gamma: float = 0.25
    key: object = 0

    def __post_init__(self) -> None:
        if isinstance(self.vocab_size, bool) or not isinstance(
                self.vocab_size, int) or self.vocab_size < 1:
            raise ValueError(f"vocab_size must be an int >= 1, got "
                             f"{self.vocab_size!r}")
        if not 0.0 < self.gamma < 1.0:
            raise ValueError(f"gamma must be in (0, 1), got {self.gamma!r}")

    @property
    def green_size(self) -> int:
        """k = max(1, floor(gamma * V)). |k - gamma * V| < 1."""
        return max(1, int(self.gamma * self.vocab_size))


def green_ids(scheme: Scheme, prev: int) -> list[int]:
    """Green list for one previous token, in sample order. Pure.

    Deterministic in (key, prev, V, gamma). Cost: O(V) time (random.sample
    copies the population when k is a large fraction of V; k Python-level
    draws), O(V) transient and O(k) result space. ~4 ms at V = 151936,
    gamma 0.25 (unmeasured estimate: 38k draws at ~100 ns).
    """
    seed = hashlib.sha256(f"{scheme.key}:{prev}".encode()).digest()
    return random.Random(seed).sample(range(scheme.vocab_size),
                                      scheme.green_size)


def green_set(prev_token, vocab_size, gamma, key) -> frozenset[int]:
    """Green list as a set, for membership. Cost: green_ids plus O(k)."""
    return frozenset(green_ids(Scheme(vocab_size, gamma, key),
                               int(prev_token)))


class Detection(NamedTuple):
    """z-score, green count G, scored pairs T. Unpacks as (z, G, T)."""

    z: float
    greens: int
    scored: int


def detect(scheme: Scheme, token_ids: Iterable[int],
           unique: bool = False) -> Detection:
    """Score a token sequence. Pure.

    Pair i = (ids[i], ids[i+1]); green iff ids[i+1] is in the green list of
    ids[i]. T = number of pairs scored; z = 0.0 when T = 0 (no evidence).
    unique=True scores each distinct (prev, cur) pair once, the repeated-
    pair filter of Kirchenbauer et al. (arXiv:2306.04634); default False
    keeps the original count.

    Pairs are grouped by previous token, so each green list is built once
    per call: O(D * V + T) time, O(V + T) space. The naive per-pair form
    costs O(T * V).
    """
    pairs = list(itertools.pairwise(token_ids))
    if unique:
        pairs = list(dict.fromkeys(pairs))
    by_prev: dict[int, list[int]] = {}
    for prev, cur in pairs:
        by_prev.setdefault(prev, []).append(cur)
    greens = 0
    for prev, curs in by_prev.items():
        green = frozenset(green_ids(scheme, int(prev)))
        greens += sum(map(green.__contains__, curs))
    t = len(pairs)
    if t == 0:
        return Detection(0.0, 0, 0)
    g = scheme.gamma
    return Detection((greens - g * t) / math.sqrt(t * g * (1 - g)),
                     greens, t)


def z_score(token_ids, vocab_size, gamma=0.25, key=0) -> Detection:
    """Detection statistic for a token sequence. Returns (z, greens, T).

    Harness entry point; same value as detect(Scheme(...), token_ids).
    """
    return detect(Scheme(vocab_size, gamma, key), token_ids)


def truncate_matched[A, B](a: Sequence[A],
                           b: Sequence[B]) -> tuple[Sequence[A],
                                                    Sequence[B]]:
    """Cut both sequences to the shorter length. Pure.

    Laws: idempotent; symmetric (swap in, swap out); both outputs are
    prefixes of the inputs, of equal length. Cost: O(min(len a, len b))
    for the slice copies.
    """
    m = min(len(a), len(b))
    return a[:m], b[:m]


class GreenListProcessor:
    """HF LogitsProcessor that applies the green-list bias. The adapter.

    Each step, for each batch row: green list of the row's last token,
    then scores[row, green] += delta. Batch rows are independent; the
    original code biased row 0 only (same result at batch size 1, the
    harness setting). torch is imported inside the call, so the core stays
    importable without torch. Cost per step: B * (green_ids + O(k) tensor
    build and host-to-device copy of k int64 = 300 KB at V = 151936).
    """

    def __init__(self, vocab_size, gamma=0.25, delta=2.0, key=0):
        self.scheme = Scheme(vocab_size, gamma, key)
        self.delta = delta

    @property
    def vocab_size(self):
        return self.scheme.vocab_size

    @property
    def gamma(self):
        return self.scheme.gamma

    @property
    def key(self):
        return self.scheme.key

    def __call__(self, input_ids, scores):
        import torch

        for row in range(input_ids.shape[0]):
            prev = int(input_ids[row, -1])
            idx = torch.tensor(sorted(green_ids(self.scheme, prev)),
                               dtype=torch.long, device=scores.device)
            scores[row, idx] += self.delta
        return scores
