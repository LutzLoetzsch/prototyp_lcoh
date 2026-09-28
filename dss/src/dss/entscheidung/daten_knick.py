from __future__ import annotations

import numpy as np
import pandas as pd

from dss.szenarien.m6 import M6_BAENDER
from dss.surrogat.daten import PARAM_NAMEN
from dss.entscheidung.lhs_tail import lhs_tail
from dss.entscheidung.ziel_knick import lcoh_netz, lcoh_dez


def datensatz_knick(n: int, seed: int, *, gamma: float = 1.0):
    rec = pd.DataFrame(lhs_tail(M6_BAENDER, n, seed, gamma=gamma)).to_dict("records")
    netz = np.array([lcoh_netz(p) for p in rec])
    dez = np.array([lcoh_dez(p) for p in rec])
    y = np.minimum(netz, dez)
    X = pd.DataFrame(rec)[PARAM_NAMEN].to_numpy(dtype=np.float64)
    return X, y, netz, dez
