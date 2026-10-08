"""Sample size for the paired token-cost contrast. Standard library only.

Outcome per task: d = log(tokens under arm X) - log(tokens under A0).
Test: paired two-sided z approximation, H0 mean(d) = 0.
sd_d = sd_task * sqrt(2 * (1 - rho)): sd_task is the between-task sd of
log length, rho the between-arm correlation of log length per task.
Default sd_task = 0.95: a conversion, not a measurement. Srivastava et
al. 2025 (arXiv 2511.04108, Table 5) report reasoning tokens at batch
size 1 as 2,973 +- 190 (DeepSeek-R1) and 2,926 +- 210 (o1), 95% CI over
n = 1,300. Inverting the CI gives sd 3,500 and 3,860 (CV 1.2, 1.3);
under a lognormal the sd of log tokens is 0.93 and 1.00
(docs/lit-review-reasoning-cost.md; the conversion is the reviewer's).
Pooled over 13 datasets, so it overstates one benchmark's spread. The
earlier 0.57 (sd of log word count of the GSM8K reference solutions)
measured text, not model output. Default rho = 0.5: assumption,
conservative for a same-task paired design.
Default --n 200: the MATH-500 sample that carries the accuracy claim.

Usage: python3 eval/tasks/power.py [--effect 0.10] [--contrasts 4]
         [--sd-task 0.95] [--rho 0.5] [--n 200]
"""

import argparse
import math
from statistics import NormalDist


def n_tokens(effect, sd_task, rho, alpha, power):
    delta = math.log(1 + effect)
    sd_d = sd_task * math.sqrt(2 * (1 - rho))
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    return math.ceil((z * sd_d / delta) ** 2), sd_d


def mcnemar_power(n, p10, p01, alpha):
    """Power of McNemar (normal approx.) for discordant rates p10, p01."""
    pd, diff = p10 + p01, p10 - p01
    za = NormalDist().inv_cdf(1 - alpha / 2)
    num = abs(diff) * math.sqrt(n) - za * math.sqrt(pd)
    return NormalDist().cdf(num / math.sqrt(pd - diff ** 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--effect", type=float, default=0.10,
                    help="relative token change to detect")
    ap.add_argument("--sd-task", type=float, default=0.95)
    ap.add_argument("--rho", type=float, default=0.5)
    ap.add_argument("--contrasts", type=int, default=4,
                    help="Bonferroni family: 2 arm contrasts x 2 models")
    ap.add_argument("--power", type=float, default=0.8)
    ap.add_argument("--n", type=int, default=200,
                    help="items for the accuracy contrast (MATH-500)")
    a = ap.parse_args()
    alpha = 0.05 / a.contrasts
    n, sd_d = n_tokens(a.effect, a.sd_task, a.rho, alpha, a.power)
    print(f"tokens: effect {a.effect:.0%}, sd_d {sd_d:.3f}, "
          f"alpha {alpha:.4f}, power {a.power}: n = {n}")
    for p10, p01 in ((0.08, 0.03), (0.10, 0.05), (0.06, 0.03)):
        pw = mcnemar_power(a.n, p10, p01, alpha)
        print(f"accuracy at n={a.n}: drop {p10 - p01:.0%} "
              f"(discordant {p10:.2f}/{p01:.2f}): power {pw:.2f}")


if __name__ == "__main__":
    main()
