from __future__ import annotations

import numpy as np

from dss.szenarien import m6

PARAM_NAMEN: list[str] = list(m6.M6_BAENDER.keys())


def datensatz(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    df = m6.lhs_ensemble(n=n, seed=seed)
    X = df[PARAM_NAMEN].to_numpy(dtype=np.float64)
    y = df["lcoh"].to_numpy(dtype=np.float64)
    return X, y


class Standardisierer:
    def __init__(self, log1p: bool = False) -> None:
        self.mu: np.ndarray | None = None
        self.sd: np.ndarray | None = None
        self.log1p = log1p

    def fit(self, a: np.ndarray) -> "Standardisierer":
        b = np.log1p(a) if self.log1p else a
        self.mu = b.mean(axis=0)
        sd = b.std(axis=0)
        self.sd = np.where(sd < 1e-12, 1.0, sd)
        return self

    def transform(self, a: np.ndarray) -> np.ndarray:
        b = np.log1p(a) if self.log1p else a
        return (b - self.mu) / self.sd

    def inverse(self, a: np.ndarray) -> np.ndarray:
        b = a * self.sd + self.mu
        return np.expm1(b) if self.log1p else b
