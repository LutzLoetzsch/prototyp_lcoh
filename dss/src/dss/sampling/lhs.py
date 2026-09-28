from __future__ import annotations

import numpy as np
from scipy.stats import qmc


def lhs_stichprobe(
    baender: dict[str, tuple[float, float]],
    n: int,
    seed: int = 42,
) -> dict[str, np.ndarray]:
    namen = list(baender)
    sampler = qmc.LatinHypercube(d=len(namen), seed=seed)
    einheitswuerfel = sampler.random(n)
    untere = np.array([baender[k][0] for k in namen])
    obere = np.array([baender[k][1] for k in namen])
    skaliert = qmc.scale(einheitswuerfel, untere, obere)
    return {k: skaliert[:, i] for i, k in enumerate(namen)}
