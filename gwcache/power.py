# sample size and minimum detectable effect for a paired difference in hit rate
from math import sqrt

from scipy.stats import norm


# labeled requests needed to detect a paired hit-rate gain of delta, given the share of discordant decisions
def n_required(discordant_share: float, delta: float, alpha: float = 0.05, power: float = 0.8) -> int:
    z = norm.ppf(1 - alpha / 2) + norm.ppf(power)
    return int(round(z**2 * discordant_share / delta**2))


# smallest paired hit-rate gain detectable with n labeled requests
def min_detectable(discordant_share: float, n: int, alpha: float = 0.05, power: float = 0.8) -> float:
    z = norm.ppf(1 - alpha / 2) + norm.ppf(power)
    return z * sqrt(discordant_share / max(n, 1))
