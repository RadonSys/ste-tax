"""Sample size for the paired token-cost contrast. Standard library only.

Outcome per task: d = log(tokens under arm X) - log(tokens under A0).
Test: paired two-sided z approximation, H0 mean(d) = 0.
sd_d = sd_task * sqrt(2 * (1 - rho)): sd_task is the between-task sd of
log length, rho the between-arm correlation of log length per task.
Default sd_task = 0.57: measured, sd of log word count of the GSM8K
test reference solutions (1319 items). Default rho = 0.5: assumption,
conservative for a same-task paired design.

Usage: python3 eval/tasks/power.py [--effect 0.10] [--contrasts 4]
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
    ap.add_argument("--sd-task", type=float, default=0.57)
    ap.add_argument("--rho", type=float, default=0.5)
    ap.add_argument("--contrasts", type=int, default=4,
                    help="Bonferroni family: 2 arm contrasts x 2 models")
    ap.add_argument("--power", type=float, default=0.8)
    ap.add_argument("--n", type=int, default=400)
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
