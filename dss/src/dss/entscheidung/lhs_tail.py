from __future__ import annotations

import numpy as np

from dss.sampling.lhs import lhs_stichprobe

# Normierte Bandkoordinate
ZENTRUM_STANDARD = 0.5


def lhs_tail(baender: dict, n: int, seed: int, *,
             gamma: float = 1.0, ziel: str = "waermeliniendichte",
             zentrum: float = ZENTRUM_STANDARD) -> dict:
    proben = lhs_stichprobe(baender, n, seed)
    if gamma == 1.0 or ziel not in baender:
        return proben
    if not (0.0 < zentrum < 1.0):
        raise ValueError("zentrum muss echt zwischen 0 und 1 liegen")
    if gamma <= 0.0:
        raise ValueError("gamma muss größer als 0 sein")

    lo, hi = baender[ziel]
    u = np.clip((np.asarray(proben[ziel], dtype=float) - lo) / (hi - lo), 0.0, 1.0)

    c = zentrum
    unten = u < c
    v = np.empty_like(u)
    v[unten] = c - c * ((c - u[unten]) / c) ** gamma
    v[~unten] = c + (1.0 - c) * ((u[~unten] - c) / (1.0 - c)) ** gamma

    proben[ziel] = lo + (hi - lo) * v
    return proben


def empirisches_zentrum(n: int = 6000, seed: int = 7, band: float = 5.0,
                        ziel: str = "waermeliniendichte") -> float:
    import pandas as pd
    from dss.szenarien.m6 import M6_BAENDER
    from dss.entscheidung.ziel_knick import lcoh_netz, lcoh_dez

    rec = pd.DataFrame(lhs_stichprobe(M6_BAENDER, n, seed)).to_dict("records")
    netz = np.array([lcoh_netz(p) for p in rec])
    dez = np.array([lcoh_dez(p) for p in rec])
    lo, hi = M6_BAENDER[ziel]
    u = (np.array([p[ziel] for p in rec]) - lo) / (hi - lo)
    nah = np.abs(netz - dez) < band
    if not nah.any():
        raise ValueError("keine knicknahen Punkte gefunden -- band vergrößern")
    return float(u[nah].mean())
