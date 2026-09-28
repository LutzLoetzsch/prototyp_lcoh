from __future__ import annotations

import numpy as np


def metriken(y_wahr: np.ndarray, y_pred: np.ndarray) -> dict:
    y_wahr = np.asarray(y_wahr, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    res = y_wahr - y_pred

    ss_res = float(np.sum(res ** 2))
    ss_tot = float(np.sum((y_wahr - y_wahr.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    p95_w = float(np.percentile(y_wahr, 95))
    p95_p = float(np.percentile(y_pred, 95))

    schwelle = float(np.percentile(y_wahr, 90))
    maske = y_wahr >= schwelle
    tail_mae = float(np.mean(np.abs(res[maske]))) if maske.any() else float("nan")

    return {
        "R2":          round(r2, 6),
        "RMSE":        round(float(np.sqrt(np.mean(res ** 2))), 4),
        "MAE":         round(float(np.mean(np.abs(res))), 4),
        "MaxFehler":   round(float(np.max(np.abs(res))), 4),
        "P95_wahr":    round(p95_w, 3),
        "P95_pred":    round(p95_p, 3),
        "P95_Fehler":  round(abs(p95_w - p95_p), 4),
        "Tail_MAE_oberes_Dezil": round(tail_mae, 4),
    }
