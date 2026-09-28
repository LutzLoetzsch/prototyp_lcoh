#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys

from dss.szenarien.m6 import M6_BAENDER, SWEEP_BEREICHE
from dss.entscheidung.ziel_knick import arme


RAHMEN_BAENDER = {k: SWEEP_BEREICHE[k] for k in ("netz_foerderquote", "hausanschluss", "betrachtungszeitraum", "co2_preis")}
AKZEPTIERT = {**M6_BAENDER, **RAHMEN_BAENDER}

NETZ_VALIDIERUNG_EUR_PRO_MWH_A = {"laendlich": 739.0, "teilbefestigt": 1045.0, "innerstaedtisch": 1351.0}

HERLEITUNG = ("trassenlaenge_m", "waermelieferung_mwh_a")


def waermeliniendichte_aus(trassenlaenge_m: float, waermelieferung_mwh_a: float) -> float:
    if trassenlaenge_m <= 0:
        raise ValueError("trassenlaenge_m muss größer als 0 sein")
    if waermelieferung_mwh_a < 0:
        raise ValueError("waermelieferung_mwh_a darf nicht negativ sein")
    return waermelieferung_mwh_a / trassenlaenge_m


def _herleiten(p: dict, warnungen: list[str]) -> dict:
    rest = {k: v for k, v in (p or {}).items() if k not in HERLEITUNG}
    vorhanden = [k for k in HERLEITUNG if k in (p or {})]
    if not vorhanden:
        return rest
    if len(vorhanden) == 1:
        warnungen.append(
            f"{vorhanden[0]} allein genügt nicht; beide Größen nötig "
            f"({HERLEITUNG[0]} und {HERLEITUNG[1]}) -- ignoriert")
        return rest
    try:
        q_l = waermeliniendichte_aus(float(p[HERLEITUNG[0]]), float(p[HERLEITUNG[1]]))
    except (TypeError, ValueError) as fehler:
        warnungen.append(f"Herleitung der Wärmeliniendichte fehlgeschlagen: {fehler} -- ignoriert")
        return rest
    if "waermeliniendichte" in rest:
        warnungen.append(
            f"waermeliniendichte={rest['waermeliniendichte']} wird durch die Herleitung "
            f"aus Trassenlänge und Wärmelieferung ersetzt (Q_l={q_l:.4f})")
    rest["waermeliniendichte"] = q_l
    warnungen.append(
        f"waermeliniendichte hergeleitet: {p[HERLEITUNG[1]]} MWh/a / "
        f"{p[HERLEITUNG[0]]} m = {q_l:.4f} MWh/(m*a)")
    return rest


def schema() -> dict:
    return {
        "anzahl": len(AKZEPTIERT),
        "davon_gesampelt": len(M6_BAENDER),
        "einheit_ausgabe": "EUR/MWh",
        "parameter": {
            k: {"min": v[0], "max": v[1],
                "typ": "gesampelt" if k in M6_BAENDER else "rahmen"}
            for k, v in AKZEPTIERT.items()
        },
        "herleitung": {
            "waermeliniendichte": {
                "aus": list(HERLEITUNG),
                "formel": "waermelieferung_mwh_a / trassenlaenge_m",
                "einheiten": {"trassenlaenge_m": "m", "waermelieferung_mwh_a": "MWh/a"},
            }
        },
    }


def entscheide(p: dict, modus: str = "analytisch", *,
               modelle: str | None = None,
               rahmen_abweichung: str = "abbruch") -> dict:
    if modus not in ("analytisch", "surrogat"):
        raise ValueError(f"unbekannter Modus: {modus!r} (analytisch oder surrogat)")
    if rahmen_abweichung not in ("abbruch", "warnung"):
        raise ValueError(
            f"unbekannte Behandlung: {rahmen_abweichung!r} (abbruch oder warnung)")
    warnungen: list[str] = []
    p = _herleiten(p, warnungen)
    bereinigt: dict[str, float] = {}
    for k, v in (p or {}).items():
        if k == "bedarfsreihe":
            if (not isinstance(v, list) or not v
                    or any(not isinstance(x, (int, float)) or x < 0 for x in v)):
                warnungen.append("bedarfsreihe ungültig (nichtleere Liste nichtnegativer Zahlen) -- ignoriert")
                continue
            bereinigt[k] = [float(x) for x in v]
            continue
        if k not in AKZEPTIERT:
            warnungen.append(f"unbekannter Parameter ignoriert: {k}")
            continue
        lo, hi = AKZEPTIERT[k]
        try:
            x = float(v)
        except (TypeError, ValueError):
            warnungen.append(f"{k}: kein Zahlenwert ({v!r}) -- ignoriert")
            continue
        if not (lo <= x <= hi):
            warnungen.append(f"{k}={x} außerhalb Band [{lo}, {hi}]")
        bereinigt[k] = x

    if "bedarfsreihe" in bereinigt and "betrachtungszeitraum" in bereinigt:
        _tb = int(round(bereinigt["betrachtungszeitraum"]))
        if len(bereinigt["bedarfsreihe"]) != _tb:
            warnungen.append(
                f"bedarfsreihe-Länge {len(bereinigt['bedarfsreihe'])} != betrachtungszeitraum {_tb}")
    angenommen = [k for k in AKZEPTIERT if k not in bereinigt]
    if "bedarfsreihe" in bereinigt and "bedarfsrate" in angenommen:
        angenommen.remove("bedarfsrate")
    zusatz: dict = {}
    if modus == "analytisch":
        netz, dez = arme(bereinigt)
    else:
        # torch nur im Surrogatmodus laden
        from dss.surrogat.modus import (Surrogatarme, pruefe_trainingsraum,
                                        trainingsraum_bericht)
        bericht = trainingsraum_bericht()
        sperren, hinweise = pruefe_trainingsraum(bereinigt, bericht)
        warnungen.extend(hinweise)
        if sperren and rahmen_abweichung == "abbruch":
            return {
                "eingang": bereinigt,
                "angenommen": angenommen,
                "warnungen": warnungen,
                "modus": modus,
                "fehler": {
                    "art": "ausserhalb_trainingsraum",
                    "meldung": ("Die Anfrage verlangt eine Größe, die das Surrogat "
                                "als Konstante gelernt hat. Das Ergebnis wäre still "
                                "falsch, deshalb wird nicht gerechnet."),
                    "gruende": sperren,
                    "abhilfe": ("--modus analytisch rechnet die Anfrage exakt; "
                                "--rahmen-abweichung warnung rechnet trotzdem und "
                                "kennzeichnet das Ergebnis als unzulässig."),
                },
                "einheit": "EUR/MWh",
            }
        warnungen.extend(sperren)
        surrogat = Surrogatarme(modelle)
        netz, dez = surrogat.arme(bereinigt)
        zusatz = {
            "zerlegung": surrogat.zerlegung(bereinigt),
            "modellherkunft": surrogat.herkunft,
            "trainingsraum": {k: v["wirksam"] for k, v in bericht.items()},
        }
        if sperren:
            zusatz["gueltigkeit"] = (
                "unzulässig -- außerhalb des Trainingsraums gerechnet")

    vorteilhaftere = "netz" if netz <= dez else "dezentral"
    return {
        "eingang": bereinigt,
        "angenommen": angenommen,
        "warnungen": warnungen,
        "modus": modus,
        **zusatz,
        "ergebnis": {
            "lcoh_netz": round(float(netz), 4),
            "lcoh_dez": round(float(dez), 4),
            "lcoh": round(float(min(netz, dez)), 4),
            "vorteilhaftere_option": vorteilhaftere,
            "abstand": round(float(abs(netz - dez)), 4),
        },
        "einheit": "EUR/MWh",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parametersatz (JSON) -> Entscheidung (JSON).")
    ap.add_argument("--in", dest="ein", help="JSON-Eingabedatei; ohne Angabe: stdin")
    ap.add_argument("--schema", action="store_true", help="Parameter-Schema ausgeben und beenden")
    ap.add_argument("--modus", choices=("analytisch", "surrogat"), default="analytisch",
                    help="Rechenweg: analytisch (Vorgabe, exakt) oder surrogat")
    ap.add_argument("--modelle", default=None,
                    help="Ordner der Armmodelle e07_{wp,bio,dez}.pt")
    ap.add_argument("--rahmen-abweichung", dest="rahmen_abweichung",
                    choices=("abbruch", "warnung"), default="abbruch",
                    help="Verhalten bei Parametern außerhalb des Trainingsraums")
    a = ap.parse_args(argv)

    if a.schema:
        json.dump(schema(), sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    roh = open(a.ein, encoding="utf-8").read() if a.ein else sys.stdin.read()
    p = json.loads(roh) if roh.strip() else {}
    json.dump(entscheide(p, a.modus, modelle=a.modelle,
                         rahmen_abweichung=a.rahmen_abweichung),
              sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
