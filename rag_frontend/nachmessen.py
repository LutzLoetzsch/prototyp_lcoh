#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nachmessung: Musterprüfungen auf die bereits gefahrenen Läufe anwenden.

ZIELPFAD: ~/Masterthesis-Code/Repos/rag_frontend/nachmessen.py

--------------------------------------------------------------------------
WARUM NACHTRÄGLICH

FM (Fundstellenmerkmale) und NR (Negative Rejection) sind erst nach den
Läufen entstanden. Ein Neulauf wäre unnötig: Die Antworttexte stehen
vollständig in den Protokollen, und beide Prüfungen sind deterministische
Musterabgleiche ohne Modellaufruf.

Damit ist die Nachmessung reproduzierbar -- sie lässt sich auf denselben
Protokollen jederzeit wiederholen und liefert dasselbe Ergebnis.

--------------------------------------------------------------------------
NR IST NICHT AUF ALLE STUFEN ANWENDBAR

Negative Rejection fragt, ob ein System die fehlende Datengrundlage
ausspricht. Verfügt die Stufe über kommunale Daten, stellt sich die Frage
nicht -- der Wert bleibt leer statt 0.

Als "mit Daten" gelten die Stufen mit Wissensbasis im Kontext (V2, V3).
V1 hat keinen Kontext, die externen Stufen haben keine kommunalen Daten.

Aufruf:
    .venv/bin/python nachmessen.py                 # Tabellen auf der Konsole
    .venv/bin/python nachmessen.py --csv           # zusätzlich als CSV
    .venv/bin/python nachmessen.py --belege        # mit Fundstellen-Nachweis
"""
from __future__ import annotations

import argparse
import csv
import glob
import os
import re
from collections import defaultdict

from muster import fundstellenmerkmale, negative_rejection
from zahlen import de

ORDNER = "reports"

# Stufen, die kommunale Daten im Kontext haben -> NR nicht anwendbar
MIT_DATEN = ("Vollkontext", "Retrieval", "Wissensbasis")

_KOPF = re.compile(r"^(D\d[\w]*)\s*·\s*Lauf\s+(\d+)\s*·\s*(\S+)")


def lies_protokolle(ordner: str = ORDNER) -> list[dict]:
    """Zerlegt alle Protokolle in Einzelläufe.

    Aufbau eines Eintrags:
        <Trennlinie>
        D3 · Lauf 1 · 2026-08-09T00:12:34
        <Bezeichnung der Stufe>
        <Trennlinie>
        ...
        ANTWORT DES SYSTEMS
          <Text>
        MESSWERTE
    """
    eintraege = []
    for pfad in sorted(glob.glob(os.path.join(ordner, "RAG-B_Protokoll_*.txt"))):
        stempel = os.path.basename(pfad).replace("RAG-B_Protokoll_", "")[:-4]
        zeilen = open(pfad, encoding="utf-8").read().split("\n")
        i = 0
        while i < len(zeilen):
            m = _KOPF.match(zeilen[i].strip())
            if not m:
                i += 1
                continue
            prompt, lauf, zeit = m.group(1), int(m.group(2)), m.group(3)
            bezeichnung = zeilen[i + 1].strip() if i + 1 < len(zeilen) else "?"

            antwort, j, sammeln = [], i + 2, False
            while j < len(zeilen):
                z = zeilen[j]
                if _KOPF.match(z.strip()):
                    break
                if z.strip() == "ANTWORT DES SYSTEMS":
                    sammeln = True
                    j += 1
                    continue
                if z.strip() == "MESSWERTE":
                    sammeln = False
                if sammeln:
                    antwort.append(z.strip())
                j += 1

            eintraege.append({
                "datei": stempel, "prompt": prompt, "lauf": lauf, "zeit": zeit,
                "bezeichnung": bezeichnung,
                "antwort": "\n".join(antwort).strip(),
            })
            i = j
    return eintraege


def entdoppeln(eintraege: list[dict]) -> list[dict]:
    """Je (Bezeichnung, Prompt, Lauf) gewinnt der jüngste Protokolleintrag.

    Dieselbe Regel wie in auswertung.py -- Anteste und Wiederholungen liegen
    mehrfach vor und wögen sonst mehrfach.
    """
    nach_schluessel = {}
    for e in sorted(eintraege, key=lambda x: x["datei"]):
        s = (e["bezeichnung"], e["prompt"], e["lauf"])
        vorher = nach_schluessel.get(s)
        # Ein leerer Eintrag verdraengt keinen gefuellten. Ein Lauf mit
        # FEHLER statt ANTWORT DES SYSTEMS ist keine neuere Messung, sondern
        # eine fehlende (Befund 10.08.2026: ein APITimeoutError vom 09.08.
        # verdraengte die vollstaendige Antwort vom 08.08. fuer V2 / D3).
        # Unter den Eintraegen MIT Text gewinnt weiterhin der juengste.
        if vorher is not None and not e["antwort"].strip() \
                and vorher["antwort"].strip():
            continue
        nach_schluessel[s] = e
    return list(nach_schluessel.values())


def messe(eintraege: list[dict]) -> list[dict]:
    for e in eintraege:
        hat_daten = any(k in e["bezeichnung"] for k in MIT_DATEN)
        fm = fundstellenmerkmale(e["antwort"])
        nr = negative_rejection(e["antwort"], hat_kommunendaten=hat_daten)
        e.update({"fm": fm["fm"], "fm_anzahl": fm["anzahl"],
                  "fm_merkmale": fm["merkmale"], "fm_belege": fm["belege"],
                  "unscharf": fm["unscharfe_jahresangabe"],
                  "nr": nr["nr"], "nr_art": nr["art"], "nr_belege": nr["belege"],
                  "leer": not e["antwort"]})
    return eintraege


def mittel(werte):
    v = [w for w in werte if w is not None]
    return round(sum(v) / len(v), 3) if v else None


def tabelle(eintraege: list[dict]) -> None:
    je_stufe = defaultdict(list)
    for e in eintraege:
        je_stufe[e["bezeichnung"]].append(e)

    breite = max(len(b) for b in je_stufe) + 2
    print("=" * 78)
    print("FM · Fundstellenmerkmale und NR · Negative Rejection")
    print("=" * 78)
    print(f"  {'Stufe':<{breite}}{'FM':>6}{'Merkm.':>8}{'NR':>6}{'unscharf':>10}{'n':>5}")
    print("  " + "─" * (breite + 35))
    for b in sorted(je_stufe, key=lambda x: ("Prototyp" not in x, x)):
        es = [e for e in je_stufe[b] if not e["leer"]]
        if not es:
            continue
        print(f"  {b:<{breite}}"
              f"{de(mittel([e['fm'] for e in es]), 2):>6}"
              f"{de(mittel([e['fm_anzahl'] for e in es]), 1):>8}"
              f"{de(mittel([e['nr'] for e in es]), 2):>6}"
              f"{de(mittel([int(e['unscharf']) for e in es]), 2):>10}"
              f"{len(es):>5}")

    print("\n  FM  Anteil der Antworten mit mindestens einem Fundstellenmerkmal")
    print("  Merkm.  mittlere Zahl verschiedener Merkmalsarten je Antwort")
    print("  NR  Anteil der Antworten, die die fehlende Datengrundlage aussprechen")
    print("      (leer, wo die Stufe über kommunale Daten verfügt)")
    print("  unscharf  Anteil mit abgeschwächter Jahresangabe, etwa Stand ca. 2023")


def merkmalsverteilung(eintraege: list[dict]) -> None:
    print("\n" + "=" * 78)
    print("Welche Fundstellenmerkmale treten auf?")
    print("=" * 78)
    je_stufe = defaultdict(lambda: defaultdict(int))
    for e in eintraege:
        for m in e["fm_merkmale"]:
            je_stufe[e["bezeichnung"]][m] += 1
    for b in sorted(je_stufe, key=lambda x: ("Prototyp" not in x, x)):
        eintrag = ", ".join(f"{m} ({n})" for m, n
                            in sorted(je_stufe[b].items(), key=lambda x: -x[1]))
        print(f"  {b}\n    {eintrag}")


def nr_arten(eintraege: list[dict]) -> None:
    print("\n" + "=" * 78)
    print("Art der Enthaltung")
    print("=" * 78)
    je_stufe = defaultdict(lambda: defaultdict(int))
    for e in eintraege:
        if e["nr"] is not None and not e["leer"]:
            je_stufe[e["bezeichnung"]][e["nr_art"]] += 1
    for b in sorted(je_stufe):
        arten = ", ".join(f"{a} ({n})" for a, n
                          in sorted(je_stufe[b].items(), key=lambda x: -x[1]))
        print(f"  {b:<44} {arten}")
    print("\n  enthaltung     benennt ausdrücklich fehlende Daten")
    print("  kennzeichnung  nennt Werte und weist sie als nicht ortsbezogen aus")
    print("  beides         beides zugleich")
    print("  keine          nennt Werte ohne Vorbehalt")


def belege(eintraege: list[dict], anzahl: int = 12) -> None:
    print("\n" + "=" * 78)
    print("Belege — für die Nachprüfung im Anhang")
    print("=" * 78)
    gezeigt = set()
    for e in eintraege:
        if e["fm_belege"] and e["bezeichnung"] not in gezeigt:
            gezeigt.add(e["bezeichnung"])
            print(f"\n  {e['bezeichnung']} · {e['prompt']}")
            for m, b in e["fm_belege"].items():
                print(f"    {m:<18} „{b}“")
            if len(gezeigt) >= anzahl:
                break


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ordner", default=ORDNER)
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--belege", action="store_true")
    a = ap.parse_args()

    roh = lies_protokolle(a.ordner)
    if not roh:
        raise SystemExit(f"Keine Protokolle in {a.ordner}")
    eintraege = messe(entdoppeln(roh))
    print(f"  Protokolleinträge gelesen : {len(roh)}")
    print(f"  nach Entdopplung          : {len(eintraege)}")
    print(f"  davon mit Antworttext     : {sum(1 for e in eintraege if not e['leer'])}\n")

    tabelle(eintraege)
    merkmalsverteilung(eintraege)
    nr_arten(eintraege)
    if a.belege:
        belege(eintraege)

    if a.csv:
        pfad = os.path.join(a.ordner, "NACHMESSUNG.csv")
        with open(pfad, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["Stufe", "Prompt", "Lauf", "FM", "Merkmale", "NR",
                        "NR-Art", "unscharfe Jahresangabe"])
            for e in eintraege:
                if e["leer"]:
                    continue
                w.writerow([e["bezeichnung"], e["prompt"], e["lauf"], e["fm"],
                            "|".join(e["fm_merkmale"]), e["nr"], e["nr_art"],
                            int(e["unscharf"])])
        print(f"\n  geschrieben: {pfad}")
