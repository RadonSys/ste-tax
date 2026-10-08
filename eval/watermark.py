"""Green-list watermark (Kirchenbauer et al. 2023): generate + detect.

Generation: at each step, a hash of (key, previous token) seeds a split of
the vocabulary into a green list (fraction gamma). Green logits get a bias
of delta. Detection needs no model: count green tokens in a sequence and
report the z-score against the null (binomial with p = gamma).

    z = (G - gamma * T) / sqrt(T * gamma * (1 - gamma))

The ste-tax question: does an ASD-STE100 vocabulary constraint lower the
z-score at matched length? A small approved vocabulary cuts the entropy
the watermark hides in, so detection should weaken. This module is the
measurement tool, not the answer.
"""

import hashlib
import math
import random


def green_set(prev_token, vocab_size, gamma, key):
    """Deterministic green list for one position. Pure stdlib."""
    seed = hashlib.sha256(f"{key}:{prev_token}".encode()).digest()
    rng = random.Random(seed)
    k = max(1, int(gamma * vocab_size))
    return set(rng.sample(range(vocab_size), k))


def z_score(token_ids, vocab_size, gamma=0.25, key=0):
    """Detection statistic for a token sequence. Returns (z, greens, T)."""
    ids = list(token_ids)
    if len(ids) < 2:
        return 0.0, 0, len(ids)
    greens = 0
    for prev, cur in zip(ids, ids[1:]):
        if cur in green_set(prev, vocab_size, gamma, key):
            greens += 1
    t = len(ids) - 1
    z = (greens - gamma * t) / math.sqrt(t * gamma * (1 - gamma))
    return z, greens, t


class GreenListProcessor:
    """HF LogitsProcessor that applies the green-list bias.

    Lazy torch import: this module stays importable without torch so the
    detector can run anywhere.
    """

    def __init__(self, vocab_size, gamma=0.25, delta=2.0, key=0):
        self.vocab_size = vocab_size
        self.gamma = gamma
        self.delta = delta
        self.key = key

    def __call__(self, input_ids, scores):
        import torch

        prev = int(input_ids[0, -1])
        green = green_set(prev, self.vocab_size, self.gamma, self.key)
        idx = torch.tensor(sorted(green), dtype=torch.long,
                           device=scores.device)
        scores[0, idx] += self.delta
        return scores
