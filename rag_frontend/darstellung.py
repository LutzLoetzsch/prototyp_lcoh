#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from prompt import PARAMETER, HERLEITUNG
from zahlen import de

ERGEBNISFELDER = {
    "lcoh_netz": ("Wärmegestehungskosten, netzgebunden", "EUR/MWh", 4),
    "lcoh_dez": ("Wärmegestehungskosten, dezentral", "EUR/MWh", 4),
    "lcoh": ("Wärmegestehungskosten der günstigeren Option", "EUR/MWh", 4),
    "abstand": ("Abstand zwischen beiden Optionen", "EUR/MWh", 4),
    "vorteilhaftere_option": ("Vorteilhaftere Versorgungsart", "", None),
    "status": ("Modellstatus", "", None),
    "datenstand": ("Datenstand", "", None),
    "hinweis": ("Hinweis", "", None),
    "kommune": ("Kommune", "", None),
    "szenario": ("Szenario", "", None),
    # Explizite Jahresreihe für nicht-monotone Verläufe.
    "bedarfsreihe": ("Jährliche Wärmemengen (Bedarfsreihe)", "MWh/a", None),
    "trassenlaenge_m": ("Länge der geplanten Wärmenetz-Trasse", "m", 1),
    "waermelieferung_mwh_a": ("Jährlich gelieferte Wärmemenge im Netzgebiet",
                              "MWh/a", 1),
}

_TEXTFELDER = {"vorteilhaftere_option", "status", "datenstand", "hinweis",
               "kommune", "szenario"}


def _beschreibung(feld: str) -> tuple[str, str, int | None]:
    if feld in ERGEBNISFELDER:
        return ERGEBNISFELDER[feld]
    if feld in PARAMETER:
        beschr, einheit, _ = PARAMETER[feld]
        stellen = 4 if einheit == "Anteil" or einheit.startswith("Anteil") else 2
        return beschr[0].upper() + beschr[1:], einheit, stellen
    if feld in HERLEITUNG:
        beschr, einheit = HERLEITUNG[feld]
        return beschr[0].upper() + beschr[1:], einheit, 1
    return feld, "", 2


def wert_text(feld: str, wert) -> str:
    _, einheit, stellen = _beschreibung(feld)
    if wert is None:
        return "—"
    if isinstance(wert, list):
        spanne = ""
        zahlen = [w for w in wert if isinstance(w, (int, float))]
        if zahlen:
            spanne = f", {de(min(zahlen), 1)} bis {de(max(zahlen), 1)}"
        return (f"{de(len(wert), 0)} Jahreswerte{spanne}"
                + (f" {einheit}" if einheit else ""))
    if feld in _TEXTFELDER or stellen is None or isinstance(wert, str):
        return str(wert)
    return (de(wert, stellen) + (f" {einheit}" if einheit and einheit != "-" else "")).strip()


def satz(daten: dict, einzug: str = "  ", breite: int | None = None) -> list[str]:
    if not daten:
        return [einzug + "(keine)"]
    namen = {f: _beschreibung(f)[0] for f in daten}
    b = breite or max(len(n) for n in namen.values()) + 2
    zeilen = []
    for feld in sorted(daten, key=lambda f: namen[f].lower()):
        zeilen.append(f"{einzug}{namen[feld]:<{b}} {wert_text(feld, daten[feld])}")
    return zeilen


def einzeiler(daten: dict, felder: list[str] | None = None) -> str:
    schluessel = felder or list(daten)
    return " | ".join(
        f"{_beschreibung(f)[0]} {wert_text(f, daten[f])}"
        for f in schluessel if f in daten)


def angenommen_text(felder: list[str], einzug: str = "  ") -> list[str]:
    if not felder:
        return []
    zeilen = [einzug + "Vom Modell angenommen (keine kommunalen Werte):"]
    for f in sorted(felder, key=lambda x: _beschreibung(x)[0].lower()):
        zeilen.append(f"{einzug}  · {_beschreibung(f)[0]}")
    return zeilen


def unbeschrieben(daten: dict) -> list[str]:
    bekannt = set(PARAMETER) | set(HERLEITUNG) | set(ERGEBNISFELDER)
    return sorted(set(daten) - bekannt)


def verbrauch_text(v: dict) -> str:
    namen = {"eingabe_token": "Eingabe", "ausgabe_token": "Ausgabe"}
    return " | ".join(f"{namen.get(k, k)} {de(w, 0)} Token"
                      for k, w in v.items() if w is not None)
