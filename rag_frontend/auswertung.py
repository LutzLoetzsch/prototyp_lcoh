#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auswertung: alle Läufe zu konsistenten Tabellen zusammenführen.

ZIELPFAD: ~/Masterthesis-Code/Repos/rag_frontend/auswertung.py

--------------------------------------------------------------------------
WARUM DIESE SCHICHT

Die Läufe sind in Ordnung; ihre Zusammenfassung war es nicht. Drei Punkte
liessen sich erst im Nachhinein erkennen und werden hier behoben -- ohne
neuen Lauf, weil die Rohwerte vollständig vorliegen:

1  DOPPELTE ZELLEN. Die Stufe "GPT-5.6 Terra ohne Suche" liegt dreifach vor
   (zwei Anteste plus der Hauptlauf). Ungefiltert wöge sie dreifach.
   Behebung: je (Stufe, Prompt) zählt der JÜNGSTE Lauf.

2  DER NUMERISCHE FEHLER RUHT AUF EINEM PROMPT. Bei sechs der sieben Prompts
   nennt kein externes Modell eine Zahl in EUR/MWh -- sie fragen nach
   Wirtschaftlichkeit, Quellen und Sicherheit, nicht nach einem Wert. Nur D2
   liefert eine. Ein Mittelwert über "alle Prompts" wäre dort ein Einzelwert
   und stünde neben dem echten Siebenermittel der lokalen Stufen.
   Behebung: n wird IMMER mitgeführt; der Fehler wird auf D2 beschränkt
   ausgewiesen.

3  DIE ATTRIBUTION IST GRUPPENABHÄNGIG NORMIERT. Lokal sind die im Kontext
   vorkommenden Quellenmarken die Bezugsgrösse, extern notwendigerweise alle
   zehn -- ein externes Modell kann SAENA oder die 9. RBV gar nicht kennen.
   Die Werte sind daher INNERHALB einer Gruppe vergleichbar, nicht zwischen
   ihnen. Behebung: getrennt ausgewiesen, mit Vermerk.

Was NICHT behoben wird: Die numerische Korrektheit bleibt zwischen den
Gruppen schwächer erhoben -- lokal aus dem Vertragsergebnis, extern aus dem
Antworttext gelesen. Das ist eine Eigenschaft des Aufbaus und gehört als
Grenze in den Text.

Aufruf:
    .venv/bin/python auswertung.py                 # Tabellen auf der Konsole
    .venv/bin/python auswertung.py --md            # zusätzlich als Markdown
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from collections import defaultdict

from zahlen import de
import nachmessen

ORDNER = "reports"

# Metriken: (Schlüssel, Überschrift, Nachkommastellen, vergleichbar zwischen
# lokalen und externen Stufen?)
METRIKEN = [
    ("Kanalisierung",     "Werkzeugbindung",        2, True),
    ("Datenherkunft",     "Werte aus der Kommune",  3, True),
    ("Attribution",       "Quellen genannt",        2, False),
    ("Attributionstreue", "Quellen gedeckt",        2, False),
    ("stabil_zahl",       "Zahl stabil",            2, True),
    ("stabil_quellen",    "Quellen stabil",         2, True),
    ("Kontext_Token",     "Kontext (Token)",        0, True),
    ("Suchen",            "Suchanfragen",           1, True),
    ("Latenz_s",          "Antwortzeit (s)",        1, True),
    # aus der Nachmessung (nachmessen.py) -- Herkunft: Protokolltexte
    ("fm",                "Fundstellen",            2, True),
    ("fm_anzahl",         "Merkmale je Antwort",    1, True),
    ("nr",                "Enthaltung",             2, True),
]

# Metriken, die NICHT aus den Kennzahlendateien stammen, sondern aus der
# nachtraeglichen Musterpruefung der Protokolltexte. Die Herkunft ist in der
# Ausgabe zu kennzeichnen -- zwei Erhebungswege duerfen nicht unbemerkt
# nebeneinanderstehen.
AUS_NACHMESSUNG = {"fm", "fm_anzahl", "nr", "unscharf"}

REIHENFOLGE = ["V0", "LX", "V1", "V2", "V3", "V3-k3", "V3-k5",
               "VX-A-S0", "VX-A-S1", "VX-A-O0", "VX-A-O1",
               "VX-G-T0", "VX-G-T1", "VX-G-S0", "VX-G-S1"]


def _k_aus_protokoll(json_pfad: str) -> int | None:
    """Liest die Chunk-Zahl k aus dem zugehoerigen Protokoll.

    ANLASS: Die Stufe V3 wurde mit k=3 UND k=5 gefahren -- zwei verschiedene
    Konfigurationen derselben Kennung. Ohne Unterscheidung faellt der k-Test
    ueber die Dopplungsregel heraus. k steht nicht in der Ergebnisdatei; die
    Zahl der retrievten Chunk-IDs im Protokoll ist die verlaessliche Spur.

    Kuenftige Laeufe schreiben k mit (siehe rag_b_lauf.py); diese Funktion
    bleibt fuer die vorhandenen Daten noetig.
    """
    prot = json_pfad.replace("RAG-B_Ergebnis_", "RAG-B_Protokoll_")[:-5] + ".txt"
    if not os.path.exists(prot):
        return None
    with open(prot, encoding="utf-8") as f:
        for zeile in f:
            if "retrievt:" in zeile:
                return len([x for x in zeile.split("retrievt:")[1].split(",") if x.strip()])
    return None


def lade(ordner: str = ORDNER) -> tuple[dict, dict, dict]:
    """Alle Ergebnisdateien einlesen und Dopplungen auflösen.

    Je (Stufe, Prompt) gewinnt der jüngste Lauf. Das Dateidatum steckt im
    Namen; ersatzweise dient die Änderungszeit.
    """
    zellen: dict[tuple[str, str], dict] = {}
    herkunft: dict[tuple[str, str], str] = {}
    bezeichnung: dict[str, str] = {}
    bezeichnung_lang: dict[str, str] = {}
    gold: dict = {}
    verworfen = 0

    for pfad in sorted(glob.glob(os.path.join(ordner, "RAG-B_Ergebnis_*.json"))):
        stempel = os.path.basename(pfad).replace("RAG-B_Ergebnis_", "")[:-5]
        d = json.load(open(pfad, encoding="utf-8"))
        gold.update(d.get("gold", {}))
        # k-Wert ermitteln, damit V3 mit k=3 und k=5 nicht zusammenfallen
        k_wert = d.get("k") or _k_aus_protokoll(pfad)

        def kennung(s: str) -> str:
            if s == "V3" and k_wert:
                return f"V3-k{k_wert}"
            return s

        for s, info in d.get("stufen", {}).items():
            sk = kennung(s)
            bez = info.get("bezeichnung_kurz", s)
            lang = info.get("bezeichnung_lang", bez)
            if sk != s:
                bez = f"{bez}, k={k_wert}"
            bezeichnung[sk] = bez
            bezeichnung_lang[sk] = lang
        for z in d.get("zeilen", []):
            if z.get("ok", 0) == 0:
                continue
            z = {**z, "stufe": kennung(z["stufe"])}
            k = (z["stufe"], z["prompt"])
            if k in zellen:
                verworfen += 1
            zellen[k] = z
            herkunft[k] = stempel
    return zellen, {"bezeichnung": bezeichnung,
                    "bezeichnung_lang": bezeichnung_lang, "gold": gold,
                    "verworfen": verworfen,
                    "nachmessung": nachmessung(ordner)}, herkunft


def mittel(werte) -> tuple[float | None, int]:
    v = [w for w in werte if w is not None]
    return (round(sum(v) / len(v), 4) if v else None, len(v))


def nachmessung(ordner: str = ORDNER) -> dict:
    """FM und NR je Stufenbezeichnung, aus den Protokolltexten.

    Die Verknuepfung laeuft ueber die LANGE Bezeichnung, weil die Protokolle
    die Kennung (V1, VX-A-S0) nicht mitfuehren. Das ist der Grund, warum die
    sprechenden Bezeichnungen im Harness eingefuehrt wurden.
    """
    try:
        roh = nachmessen.lies_protokolle(ordner)
    except Exception:
        return {}
    if not roh:
        return {}
    eintraege = nachmessen.messe(nachmessen.entdoppeln(roh))
    je_stufe = {}
    for e in eintraege:
        if e["leer"]:
            continue
        je_stufe.setdefault(e["bezeichnung"], []).append(e)
    ergebnis = {}
    for bez, es in je_stufe.items():
        def m(feld):
            v = [x[feld] for x in es if x[feld] is not None]
            return round(sum(v) / len(v), 4) if v else None
        ergebnis[bez] = {"fm": m("fm"), "fm_anzahl": m("fm_anzahl"),
                         "nr": m("nr"),
                         "unscharf": round(sum(int(x["unscharf"]) for x in es)
                                           / len(es), 4),
                         "n_nachmessung": len(es)}
    return ergebnis


def tabelle_stufen(zellen, meta, nur_prompt: str | None = None) -> list[dict]:
    je_stufe = defaultdict(list)
    for (s, p), z in zellen.items():
        if nur_prompt and p != nur_prompt:
            continue
        je_stufe[s].append(z)

    reihen = []
    for s in REIHENFOLGE:
        if s not in je_stufe:
            continue
        zs = je_stufe[s]
        r = {"stufe": s, "bezeichnung": meta["bezeichnung"].get(s, s),
             "gruppe": "extern" if s.startswith("VX") else "lokal",
             "prompts": len(zs),
             "laeufe": sum(z.get("ok", 0) for z in zs)}
        for k, _, _, _ in METRIKEN:
            w, n = mittel([z.get(k) for z in zs])
            r[k] = w
            r[k + "_n"] = n
        w, n = mittel([z.get("relFehler") for z in zs])
        r["relFehler"], r["relFehler_n"] = w, n

        # Nachmessung ueber die LANGE Bezeichnung zuordnen
        nm = meta.get("nachmessung", {}).get(
            meta.get("bezeichnung_lang", {}).get(s, ""), {})
        for k in ("fm", "fm_anzahl", "nr", "unscharf"):
            r[k] = nm.get(k)
            r[k + "_n"] = nm.get("n_nachmessung", 0) if nm.get(k) is not None else 0
        reihen.append(r)
    return reihen


def _z(wert, stellen, breite=8) -> str:
    return f"{de(wert, stellen):>{breite}}"


def drucke(reihen, titel: str, spalten=None, mit_n=False) -> None:
    spalten = spalten or METRIKEN
    breite = max(len(r["bezeichnung"]) for r in reihen) + 2
    print(f"\n{titel}\n" + "─" * (breite + 11 * len(spalten)))
    kopf = f"  {'Stufe':<{breite}}"
    for _, name, _, _ in spalten:
        kopf += f"{name[:10]:>11}"
    print(kopf)
    print("  " + "─" * (breite + 11 * len(spalten) - 2))
    for r in reihen:
        z = f"  {r['bezeichnung']:<{breite}}"
        for k, _, st, _ in spalten:
            wert = _z(r.get(k), st, 11)
            if mit_n and r.get(k) is not None:
                wert = f"{de(r[k], st)} ({r[k + '_n']})".rjust(11)
            z += wert
        print(z)


def hauptteil(zellen, meta) -> None:
    reihen = tabelle_stufen(zellen, meta)
    lokal = [r for r in reihen if r["gruppe"] == "lokal"]
    extern = [r for r in reihen if r["gruppe"] == "extern"]

    print("=" * 78)
    print("ÜBERSICHT")
    print("=" * 78)
    print(f"  Stufen mit Daten : {len(reihen)}")
    print(f"  Zellen gesamt    : {len(zellen)}")
    print(f"  Läufe gesamt     : {sum(r['laeufe'] for r in reihen)}")
    print(f"  Dopplungen verworfen (jüngster Lauf gewinnt): {meta['verworfen']}")
    print("  Wahrheit         : " + " | ".join(
        f"{k} {de(v.get('lcoh'), 4)} EUR/MWh" for k, v in meta["gold"].items()))
    print("\n  Erhebungswege:")
    print("    Kennzahlendateien  WB, KD, QN, QG, SZ, SQ, KU, SA, AZ, NK")
    print("    Protokolltexte     FM, NR  (nachträgliche Musterprüfung)")

    kern = [("Kanalisierung", "WB Werkzeugbindung", 2, True),
            ("Datenherkunft", "KD Kommunendaten", 3, True),
            ("fm", "FM Fundstellen", 2, True),
            ("nr", "NR Enthaltung", 2, True),
            ("stabil_zahl", "SZ Zahl stabil", 2, True),
            ("stabil_quellen", "SQ Quellen stabil", 2, True),
            ("Kontext_Token", "KU Kontext", 0, True),
            ("Suchen", "SA Suchen", 1, True),
            ("Latenz_s", "AZ Zeit (s)", 1, True)]
    drucke(reihen, "TABELLE 1  Kernkennzahlen — über alle Stufen vergleichbar", kern)
    print("\n  FM und NR stammen aus der Musterprüfung der Protokolltexte,")
    print("  alles Übrige aus den Kennzahlendateien der Läufe.")

    print("\n  Vollständigkeit je Stufe (Prompts / Einzelläufe):")
    for r in reihen:
        print(f"    {r['bezeichnung']:<44} {r['prompts']} / {r['laeufe']}")

    nicht = [m for m in METRIKEN if not m[3]]
    print("\n" + "=" * 78)
    print("TABELLE 2  Quellennennung — NUR INNERHALB einer Gruppe vergleichbar")
    print("=" * 78)
    print("  Die Bezugsgröße hängt daran, ob eine Stufe einen Kontext hat,")
    print("  nicht an der Gruppe: Mit Kontext (V2, V3) zählen die dort")
    print("  vorkommenden Quellenmarken, ohne Kontext -- V1 und LX ebenso wie")
    print("  alle externen Stufen -- notwendigerweise alle zehn. Ein Modell")
    print("  ohne Kontext kann SAENA oder die 9. RBV nicht kennen.")
    print("  FM (Fundstellen) ist davon UNABHÄNGIG und daher vergleichbar:")
    print("  es prüft die Form der Angabe, nicht welche Quelle gemeint ist.")
    if lokal:
        drucke(lokal, "  lokal", nicht)
    if extern:
        drucke(extern, "  extern", nicht)

    print("\n" + "=" * 78)
    print("TABELLE 3  Numerische Korrektheit — nur Prompt D2")
    print("=" * 78)
    print("  Bei D1 und D3 bis D7 nennt kein externes Modell eine Zahl in")
    print("  EUR/MWh. Lokal stammt der Wert aus dem Vertragsergebnis, extern")
    print("  aus dem Antworttext gelesen — schwächer erhoben.")
    d2 = tabelle_stufen(zellen, meta, nur_prompt="D2")
    breite = max(len(r["bezeichnung"]) for r in d2) + 2
    print(f"\n  {'Stufe':<{breite}}{'rel. Fehler':>13}{'n':>4}")
    print("  " + "─" * (breite + 17))
    for r in d2:
        print(f"  {r['bezeichnung']:<{breite}}"
              f"{de(r['relFehler'], 3):>13}{r['relFehler_n']:>4}")

    print("\n" + "=" * 78)
    print("NICHT ERHOBEN")
    print("=" * 78)
    print("  Faithfulness (4) und Answer Relevance (5) — der Judge kann im")
    print("  gegebenen Aufbau nicht unabhängig sein: Beide großen Anbieter")
    print("  sind Untersuchungsgegenstand. Begründet ausgeschlossen.")
    print("  Bezugsgrößen-Passung (BP) — kein Muster erkennt, ob ein")
    print("  Verkaufspreis die Frage nach Gestehungskosten beantwortet.")
    print("  Im Text als Einzelfall beschrieben.")


def als_markdown(zellen, meta, pfad="reports/AUSWERTUNG.md") -> None:
    reihen = tabelle_stufen(zellen, meta)
    d2 = tabelle_stufen(zellen, meta, nur_prompt="D2")
    verg = [m for m in METRIKEN if m[3]]
    nicht = [m for m in METRIKEN if not m[3]]

    def tab(rr, spalten):
        z = ["| Stufe | " + " | ".join(n for _, n, _, _ in spalten) + " |",
             "|---|" + "---|" * len(spalten)]
        for r in rr:
            z.append("| " + r["bezeichnung"] + " | "
                     + " | ".join(de(r.get(k), st) for k, _, st, _ in spalten) + " |")
        return "\n".join(z)

    t = ["# Auswertung Benchmark RAG-B", "",
         f"Stufen mit Daten: {len(reihen)} · Zellen: {len(zellen)} · "
         f"Läufe: {sum(r['laeufe'] for r in reihen)}", "",
         "Wahrheit je Kommune: " + " · ".join(
             f"{k} {de(v.get('lcoh'), 4)} EUR/MWh" for k, v in meta["gold"].items()),
         "", "## Tabelle 1 — über alle Stufen vergleichbar", "",
         tab(reihen, verg), "",
         "## Tabelle 2 — Quellenmetriken, nur innerhalb einer Gruppe vergleichbar", "",
         "Bezugsgröße lokal: die im Kontext vorkommenden Quellenmarken. "
         "Bezugsgröße extern: alle zehn Marken — ein externes Modell kann SAENA "
         "oder die 9. RBV nicht kennen.", "",
         "### lokal", "", tab([r for r in reihen if r["gruppe"] == "lokal"], nicht), "",
         "### extern", "", tab([r for r in reihen if r["gruppe"] == "extern"], nicht), "",
         "## Tabelle 3 — numerische Korrektheit, nur Prompt D2", "",
         "Bei D1 und D3 bis D7 nennt kein externes Modell eine Zahl in EUR/MWh. "
         "Lokal stammt der Wert aus dem Vertragsergebnis, extern aus dem "
         "Antworttext gelesen — schwächer erhoben.", "",
         "| Stufe | rel. Fehler | n |", "|---|---|---|"]
    for r in d2:
        t.append(f"| {r['bezeichnung']} | {de(r['relFehler'], 3)} | {r['relFehler_n']} |")
    t += ["", "## Noch nicht erhoben", "",
          "Quellenspezifität und Passung der Bezugsgröße sind handkodiert. Sie "
          "sind die einzigen Metriken, die zwischen lokalen und externen Stufen "
          "von Bauart her vergleichbar sind."]
    open(pfad, "w", encoding="utf-8").write("\n".join(t) + "\n")
    print(f"\n  geschrieben: {pfad}")


def fuer_abbildungen(zellen, meta, pfad="reports/ABBILDUNGSDATEN.json") -> None:
    """Eine Datenquelle für alle Abbildungen.

    Die Beschriftungen kommen aus derselben Datei wie die Werte -- sonst
    müssten sie zweimal gepflegt werden und liefen auseinander.
    """
    reihen = tabelle_stufen(zellen, meta)
    d2 = {r["stufe"]: r["relFehler"] for r in tabelle_stufen(zellen, meta, "D2")}
    daten = {
        "erzeugt": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "wahrheit": {k: v.get("lcoh") for k, v in meta["gold"].items()},
        "stufen": [
            {"kennung": r["stufe"],
             "bezeichnung": r["bezeichnung"],
             "bezeichnung_lang": meta.get("bezeichnung_lang", {}).get(
                 r["stufe"], r["bezeichnung"]),
             "gruppe": r["gruppe"],
             "prompts": r["prompts"], "laeufe": r["laeufe"],
             "WB": r.get("Kanalisierung"), "KD": r.get("Datenherkunft"),
             "QN": r.get("Attribution"), "QG": r.get("Attributionstreue"),
             "FM": r.get("fm"), "FM_anzahl": r.get("fm_anzahl"),
             "NR": r.get("nr"), "unscharf": r.get("unscharf"),
             "SZ": r.get("stabil_zahl"), "SQ": r.get("stabil_quellen"),
             "KU": r.get("Kontext_Token"), "SA": r.get("Suchen"),
             "AZ": r.get("Latenz_s"), "NK_D2": d2.get(r["stufe"])}
            for r in reihen],
        "hinweise": {
            "QN": "gruppenabhängig normiert — nur innerhalb einer Gruppe vergleichbar",
            "QG": "bei externen Stufen nicht definiert (kein Kontext)",
            "WB": "bei externen Stufen strukturell 0 — Eigenschaft des Aufbaus",
            "NK_D2": "nur Prompt D2, n = 1 je Stufe; lokal aus dem Vertrag, extern aus dem Text",
            "KU": "lokal aus der Zeichenzahl geschätzt, extern aus der Schnittstelle gezählt",
            "FM": "Musterprüfung: erkennt die Form einer Fundstelle, nicht ihre Richtigkeit",
            "NR": "Musterprüfung: erkennt die Aussage, nicht ob sie zutrifft",
        },
    }
    json.dump(daten, open(pfad, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"  geschrieben: {pfad}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ordner", default=ORDNER)
    ap.add_argument("--md", action="store_true")
    a = ap.parse_args()
    zellen, meta, _ = lade(a.ordner)
    if not zellen:
        raise SystemExit(f"Keine Ergebnisdateien in {a.ordner}")
    hauptteil(zellen, meta)
    if a.md:
        als_markdown(zellen, meta)
    fuer_abbildungen(zellen, meta)
