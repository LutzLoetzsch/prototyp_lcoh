#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import numpy as np
import torch

from dss.surrogat.daten import PARAM_NAMEN, Standardisierer
from dss.surrogat.modell import MLP, n_parameter

DATEIVERSION = 1


def _std_als_dict(s: Standardisierer) -> dict:
    return {"mu": np.asarray(s.mu).tolist(),
            "sd": np.asarray(s.sd).tolist(),
            "log1p": bool(s.log1p)}


def _std_aus_dict(d: dict) -> Standardisierer:
    s = Standardisierer(log1p=d["log1p"])
    s.mu = np.asarray(d["mu"], dtype=np.float64)
    s.sd = np.asarray(d["sd"], dtype=np.float64)
    return s


def speichere_modell(pfad: Path, modell, sx: Standardisierer, sy: Standardisierer,
                     *, versteckt: list[int], aktiv: str, name: str,
                     ziel: str, extra: dict | None = None) -> Path:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    inhalt = {
        "dateiversion": DATEIVERSION,
        "name": name,
        "ziel": ziel,
        "state_dict": {k: v.cpu() for k, v in modell.state_dict().items()},
        "n_eingang": len(PARAM_NAMEN),
        "versteckt": list(versteckt),
        "aktiv": aktiv,
        "n_parameter": n_parameter(modell),
        "param_namen": list(PARAM_NAMEN),
        "sx": _std_als_dict(sx),
        "sy": _std_als_dict(sy),
        "datum": date.today().isoformat(),
        "extra": extra or {},
    }
    torch.save(inhalt, pfad)
    return pfad


def lade_modell(pfad: Path, device: str = "cpu"):
    inhalt = torch.load(Path(pfad), map_location=device, weights_only=False)
    if inhalt.get("dateiversion") != DATEIVERSION:
        raise ValueError(f"Unerwartete Dateiversion in {pfad}: "
                         f"{inhalt.get('dateiversion')} statt {DATEIVERSION}")
    if list(inhalt["param_namen"]) != list(PARAM_NAMEN):
        raise ValueError(
            "Parameterreihenfolge weicht ab -- das Modell wurde gegen einen "
            "anderen Parametersatz trainiert und darf nicht verwendet werden.\n"
            f"  gespeichert: {inhalt['param_namen']}\n  aktuell    : {PARAM_NAMEN}")
    modell = MLP(inhalt["n_eingang"], inhalt["versteckt"], inhalt["aktiv"]).to(device)
    modell.load_state_dict(inhalt["state_dict"])
    modell.eval()
    meta = {k: v for k, v in inhalt.items() if k not in ("state_dict", "sx", "sy")}
    return modell, _std_aus_dict(inhalt["sx"]), _std_aus_dict(inhalt["sy"]), meta


def schreibe_manifest(ordner: Path, eintraege: list[dict], kopf: dict) -> Path:
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / "modelle_manifest.json"
    pfad.write_text(json.dumps({**kopf, "modelle": eintraege},
                               indent=2, ensure_ascii=False), encoding="utf-8")
    return pfad


def vorhersage(modell, sx: Standardisierer, sy: Standardisierer,
               X: np.ndarray, device: str = "cpu") -> np.ndarray:
    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    with torch.no_grad():
        xs = torch.tensor(sx.transform(X), dtype=torch.float32).to(device)
        y = modell(xs).cpu().numpy()
    return np.asarray(sy.inverse(y)).ravel()
