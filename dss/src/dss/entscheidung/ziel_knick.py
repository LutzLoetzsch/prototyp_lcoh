from __future__ import annotations

from dss.szenarien.m6 import lcoh_m6
from dss.entscheidung.dez_referenz import lcoh_dez


def lcoh_netz(p: dict) -> float:
    return lcoh_m6(p)


def ziel_knick(p: dict) -> float:
    return min(lcoh_netz(p), lcoh_dez(p))


def arme(p: dict) -> tuple[float, float]:
    return lcoh_netz(p), lcoh_dez(p)
