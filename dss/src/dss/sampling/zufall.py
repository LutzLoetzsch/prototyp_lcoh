from __future__ import annotations

import numpy as np

def zufalls_stichprobe(
    baender: dict[str, tuple[float, float]],
    n: int,
    seed: int = 42,
) -> dict[str, np.ndarray]:

    rng = np.random.default_rng(seed)
    return {k: rng.uniform(lo, hi, n) for k, (lo, hi) in baender.items()}
