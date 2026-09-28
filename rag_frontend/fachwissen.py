#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from pathlib import Path

import yaml

from zahlen import de

STANDARD = "wissensbasis/technikkatalog.yaml"

BLOECKE = ("waermepumpe_dezentral", "grosswaermepumpe", "biomasse",
           "gas", "netz", "emissionsfaktoren")

ANZEIGE = {
    "waermepumpe_dezentral": "Wärmepumpen (dezentral)",
    "grosswaermepumpe":      "Großwärmepumpen (netzgebunden)",
    "biomasse":              "Biomasse",
    "gas":                   "Gas (Referenztechnologie)",
    "netz":                  "Wärmenetz",
    "emissionsfaktoren":     "Emissionsfaktoren",
}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


FELDNAMEN = {
    "leistung":                    ("Leistung", ""),
    "jahresarbeitszahl":           ("Jahresarbeitszahl", ""),
    "nutzungsgrad":                ("Nutzungsgrad", ""),
    "wirkungsgrad":                ("Wirkungsgrad", ""),
    "lebensdauer_a":               ("Lebensdauer", "a"),
    "investition":                 ("Investition", ""),
    "investition_eur_pro_kw":      ("Investition", "EUR/kW"),
    "betrieb":                     ("Betriebskosten", ""),
    "betrieb_eur_pro_kw_a":        ("Betriebskosten", "EUR/(kW·a)"),
    "verlustanteil":               ("Verlustanteil", ""),
    "hauptleitung_eur_pro_m":      ("Hauptleitung", "EUR/m"),
    "spez_verteilkosten_eur_pro_mwh_a": ("Spezifische Verteilkosten", "EUR/(MWh·a)"),
    "betriebskostenanteil":        ("Betriebskostenanteil", "Anteil"),
    "wert_t_pro_mwh":              ("Emissionsfaktor", "t/MWh"),
    "typ":                         ("Typ", ""),
    "luft_wasser":                 ("Luft-Wasser-Wärmepumpe", ""),
    "wasser_wasser":               ("Wasser-Wasser-Wärmepumpe", ""),
    "sole_wasser":                 ("Sole-Wasser-Wärmepumpe", ""),
    "luft":                        ("Luft als Quelle", ""),
    "abwaerme":                    ("Abwärme als Quelle", ""),
    "gewaesser":                   ("Gewässer als Quelle", ""),
    "klaerwasser":                 ("Klärwasser als Quelle", ""),
    "grubenwasser":                ("Grubenwasser als Quelle", ""),
    "pelletkessel_dezentral":      ("Pelletkessel (dezentral)", ""),
    "hackschnitzelkessel_dezentral": ("Hackschnitzelkessel (dezentral)", ""),
    "heizwerk_hackschnitzel":      ("Heizwerk Hackschnitzel", ""),
    "heizwerk_pellets":            ("Heizwerk Pellets", ""),
    "biogas_bhkw":                 ("Biogas-BHKW", ""),
    "brennwert_dezentral":         ("Gas-Brennwertkessel (dezentral)", ""),
    "brennwert_zentral":           ("Gas-Brennwertkessel (zentral)", ""),
    "konventionell":               ("Konventionelles Wärmenetz", ""),
    "niedertemperatur":            ("Niedertemperaturnetz", ""),
    "kalte_nahwaerme":             ("Kalte Nahwärme", ""),
    "strom_mix_d_2025":            ("Strommix Deutschland 2025", ""),
    "erdgas":                      ("Erdgas", ""),
    "holz_biogen":                 ("Holz (biogen)", ""),
}


def _feldname(schluessel: str) -> tuple[str, str]:
    if schluessel in FELDNAMEN:
        return FELDNAMEN[schluessel]
    return schluessel.replace("_", " "), ""


def _eintrag_text(name: str, feld: dict) -> str:
    teile = []
    for k, v in feld.items():
        if k in ("quelle", "status", "hinweis", "projektnotiz"):
            continue
        klartext, einheit = _feldname(k)
        roh = de(v, 3).rstrip("0").rstrip(",") if isinstance(v, float) else (
            de(v, 0) if isinstance(v, int) and not isinstance(v, bool) else f"{v}")
        wert = f"{roh} {einheit}".strip() if einheit else roh
        teile.append(f"{klartext} {wert}")
    lesbar, _ = _feldname(name)
    kern = f"{lesbar} ({'; '.join(teile)})" if teile else lesbar

    zusatz = []
    if feld.get("quelle"):
        zusatz.append(f"Quelle: {feld['quelle']}")
    if feld.get("status"):
        zusatz.append(f"Status: {feld['status']}")
    if feld.get("hinweis"):
        zusatz.append("Hinweis: " + " ".join(str(feld["hinweis"]).split()))
    return kern + (" [" + "; ".join(zusatz) + "]" if zusatz else "")


def lade_technikkatalog(pfad: str | Path = STANDARD) -> list[dict]:
    kat = yaml.safe_load(open(pfad, encoding="utf-8"))
    meta = kat.get("_meta", {})
    kopf = (f"[{meta.get('name', 'Technikkatalog')} "
            f"{meta.get('version', '')} | Stützjahr {meta.get('stuetzjahr', '')}"
            f" | {meta.get('waehrung', '')} | {meta.get('lizenz', '')}]")

    chunks = []
    for block in BLOECKE:
        if block not in kat or not isinstance(kat[block], dict):
            continue
        zeilen = [_eintrag_text(name, feld) if isinstance(feld, dict) else f"{name}: {feld}"
                  for name, feld in kat[block].items()]
        chunks.append({
            "chunk_id": f"technikkatalog::{_slug(block)}",
            "kommune": None,
            "block": block,
            "text": f"{kopf} {ANZEIGE.get(block, block)}: " + " | ".join(zeilen),
        })
    return chunks


def technikkatalog_text(pfad: str | Path = STANDARD) -> str:
    return "\n\n".join(c["text"] for c in lade_technikkatalog(pfad))


if __name__ == "__main__":
    cs = lade_technikkatalog()
    print(f"{len(cs)} Chunks, {sum(len(c['text']) for c in cs)} Zeichen")
