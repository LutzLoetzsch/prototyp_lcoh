#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

import yaml


_prozent_zu_anteil: Callable[[float], float] = lambda x: x / 100.0

MAPPING: dict[tuple[str, ...], tuple[str, Callable[[float], float] | None]] = {
    ("realisierung", "wacc"):                          ("wacc", None),
    ("realisierung", "foerderquote_dezentral"):        ("foerderquote", None),
    ("trajektorie", "bedarfsrate_kombiniert"):         ("bedarfsrate", _prozent_zu_anteil),
    ("erzeuger", "grubenwasser_wp", "jahresarbeitszahl"): ("jaz", None),
    ("erzeuger", "grubenwasser_wp", "investitionskosten"): ("capex_wp", None),
    ("realisierung", "energiepreis_strom"):            ("strompreis", None),
    ("erzeuger", "biomasse", "wirkungsgrad"):          ("nutzungsgrad", None),
    ("erzeuger", "biomasse", "investitionskosten"):    ("capex_bio", None),
    ("realisierung", "energiepreis_holz"):             ("brennstoffpreis", None),
    ("netz", "waermeliniendichte_ql"):                 ("waermeliniendichte", None),
    ("netz", "verlustanteil"):                         ("verlustanteil", _prozent_zu_anteil),
    ("realisierung", "foerderquote_netz"):             ("netz_foerderquote", None),
    ("netz", "investition_eur_pro_m"):                 ("netz_invest", None),
    ("netz", "trassenlaenge_m"):                       ("trassenlaenge_m", None),
    ("netz", "waermelieferung_mwh_a"):                 ("waermelieferung_mwh_a", None),
}

NICHT_ABBILDBAR = {
    ("netz", "netzkosten_validierungsanker"):
        "TK EUR/(MWh*a) (Tab 42 Z.17) = Gesamtkosten/Jahreswaermemenge (Dichte eingebacken). "
        "VALIDIERUNGSANKER, kein Input: c_d = netz_invest/Q_l wird hiergegen geprueft (Befund 2 = a).",
}


def lade_profil(pfad: str | Path) -> dict[str, Any]:
    with open(pfad, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _feldwert(profil: dict, pfad: tuple[str, ...]) -> Any:
    knoten: Any = profil
    for schluessel in pfad:
        if not isinstance(knoten, dict) or schluessel not in knoten:
            return None
        knoten = knoten[schluessel]
    if isinstance(knoten, dict):
        return knoten.get("wert")
    return knoten


def _quelle(profil: dict, pfad: tuple[str, ...]) -> str:
    knoten: Any = profil
    for schluessel in pfad:
        if not isinstance(knoten, dict) or schluessel not in knoten:
            return ""
        knoten = knoten[schluessel]
    return knoten.get("quelle", "") if isinstance(knoten, dict) else ""


def assembliere_parametersatz(
    profil: dict[str, Any],
    szenario: dict[str, float] | None = None,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    params: dict[str, float] = {}
    report: list[dict[str, Any]] = []

    for pfad, (m6_param, konv) in MAPPING.items():
        wert = _feldwert(profil, pfad)
        if wert is None:
            continue
        wert = float(wert)
        if konv is not None:
            wert = konv(wert)
        params[m6_param] = wert
        report.append({
            "parameter": m6_param,
            "wert": wert,
            "herkunft": "profil:" + ".".join(pfad),
            "quelle": _quelle(profil, pfad),
        })

    for k, v in (szenario or {}).items():
        params[k] = float(v)
        report.append({"parameter": k, "wert": float(v),
                        "herkunft": "szenario", "quelle": ""})

    T = _sub(profil, "_meta", "betrachtungszeitraum")
    if T is not None:
        reihe = bedarfsreihe_aus_profil(profil, int(T))
        if reihe is not None:
            params["bedarfsreihe"] = reihe
            params["betrachtungszeitraum"] = float(int(T))
            report.append({"parameter": "bedarfsreihe", "wert": f"[{len(reihe)} Jahreswerte]",
                           "herkunft": "profil:waermebedarf.segmente", "quelle": "aus Segmentreihen"})

    return params, report


def _finde_dss_python(dss_repo: str, explizit: str | None = None) -> str:
    if explizit:
        return explizit
    umgebung = os.environ.get("DSS_PYTHON")
    if umgebung:
        return umgebung
    kandidat = Path(dss_repo) / ".venv" / "bin" / "python"
    return str(kandidat) if kandidat.exists() else "python"


def entscheide_via_cli(
    params: dict[str, float],
    dss_python: str | None = None,
    dss_repo: str | None = None,
    modus: str | None = None,
) -> dict[str, Any]:
    dss_repo = dss_repo or os.environ.get("DSS_REPO", ".")
    dss_python = _finde_dss_python(dss_repo, dss_python)
    src_abs = str((Path(dss_repo) / "src").resolve())
    umgebung = dict(os.environ, PYTHONPATH=src_abs)
    zusatz = ["--modus", modus] if modus else []
    ergebnis = subprocess.run(
        [dss_python, "-m", "dss.cli_entscheidung", *zusatz],
        input=json.dumps(params), capture_output=True, text=True,
        cwd=dss_repo, env=umgebung, check=True,
    )
    return json.loads(ergebnis.stdout)


def entscheide_aus_profil(
    profil_pfad: str | Path,
    szenario: dict[str, float] | None = None,
    **cli,
) -> dict[str, Any]:
    profil = lade_profil(profil_pfad)
    params, report = assembliere_parametersatz(profil, szenario)
    ausgabe = entscheide_via_cli(params, **cli)
    ausgabe["herkunft"] = report
    return ausgabe


def _sub(profil: dict, *pfad: str) -> Any:
    knoten: Any = profil
    for s in pfad:
        if not isinstance(knoten, dict) or s not in knoten:
            return None
        knoten = knoten[s]
    return knoten.get("wert") if isinstance(knoten, dict) else knoten


def bedarfsreihe_aus_profil(profil: dict, T: int) -> list[float] | None:
    q0 = _sub(profil, "waermebedarf", "segment_haushalt", "q0")
    rate = _sub(profil, "waermebedarf", "segment_haushalt", "rate")
    if q0 is None or rate is None:
        return None
    r = float(rate) / 100.0
    haushalt = [float(q0) * (1.0 + r) ** t for t in range(T)]

    ind = profil.get("waermebedarf", {}).get("segment_industrie", {})
    bestand = _sub({"x": ind}, "x", "bestand_vor_anschluss")
    neu = _sub({"x": ind}, "x", "neu_ab_anschluss")
    ansj = _sub({"x": ind}, "x", "anschlussjahr")
    wachs = _sub({"x": ind}, "x", "wachstumsrate")
    if None in (bestand, neu, ansj, wachs):
        return haushalt
    g = float(wachs) / 100.0
    industrie = [
        (float(bestand) if (j + 1) < int(ansj)
         else float(neu) * (1.0 + g) ** ((j + 1) - int(ansj)))
        for j in range(T)
    ]
    return [round(haushalt[t] + industrie[t], 4) for t in range(T)]
