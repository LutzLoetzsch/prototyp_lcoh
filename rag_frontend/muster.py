#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re


FUNDSTELLE = {
    "tabelle": re.compile(
        r"\b(?:Tab(?:elle)?\.?|Tbl\.?)\s*\d+", re.IGNORECASE),
    "zeile": re.compile(
        r"\b(?:Z(?:eile)?\.?|Zl\.?)\s*\d+", re.IGNORECASE),
    "seite": re.compile(
        r"\b(?:S\.|Seite[n]?|pp?\.)\s*\d+", re.IGNORECASE),
    "abschnitt": re.compile(
        r"\b(?:Abschn(?:itt)?\.?|Kap(?:itel)?\.?|§)\s*\d+", re.IGNORECASE),
    "doi": re.compile(r"\b(?:doi[:\s]|10\.\d{4,}/)", re.IGNORECASE),
    "version": re.compile(r"\bv\d+(?:\.\d+)+\b", re.IGNORECASE),
    "bezugsjahr": re.compile(
        r"(?<!ca\.\s)(?<!ca\. )(?<!etwa\s)(?<!rund\s)(?<!circa\s)(?<!~)"
        r"\b(?:Stand|Stützjahr|Bezugsjahr|Erhebung|Berichtsjahr)\b[^.;]{0,12}"
        r"\b(?:19|20)\d{2}\b", re.IGNORECASE),
    "grundgesamtheit": re.compile(
        r"\b\d{1,5}\s*(?:Versorger|Städte|Gemeinden|Anlagen|Betriebe|"
        r"Netze|Standorte|Fälle|Beobachtungen)\b", re.IGNORECASE),
    "lizenz": re.compile(r"\bCC[- ]BY(?:[- ]\w+)*\b|\bDL-DE\b", re.IGNORECASE),
    "datensatzkennung": re.compile(
        r"\b[a-z]+_[a-z]+_[a-z]+(?:_[a-z]+)*\b"),
}

_UNSCHARF = re.compile(r"\b(?:ca\.|etwa|rund|circa|ungefähr|grob|~)\s*"
                       r"(?:19|20)\d{2}\b", re.IGNORECASE)


def fundstellenmerkmale(text: str) -> dict:
    if not text:
        return {"merkmale": [], "anzahl": 0, "fm": 0, "belege": {},
                "unscharfe_jahresangabe": False}

    gefunden, belege = [], {}
    for name, muster in FUNDSTELLE.items():
        m = muster.search(text)
        if m:
            gefunden.append(name)
            belege[name] = m.group(0).strip()

    return {"merkmale": gefunden, "anzahl": len(gefunden),
            "fm": int(bool(gefunden)), "belege": belege,
            "unscharfe_jahresangabe": bool(_UNSCHARF.search(text))}


ENTHALTUNG = [
    re.compile(r"\bkeine?\s+(?:belegten?\s+|konkreten?\s+|kommunenspezifischen?\s+|"
               r"lokalen?\s+|belastbaren?\s+)?Daten\b[^.]{0,40}\b(?:vor|"
               r"verfügbar|vorhanden|bekannt)", re.IGNORECASE),
    re.compile(r"\bliegen\s+(?:mir|uns)?\s*keine\b", re.IGNORECASE),
    re.compile(r"\bkeine\s+belastbare\s+(?:Zahl|Angabe|Aussage)", re.IGNORECASE),
    re.compile(r"\bkann\s+(?:ich\s+)?(?:daher\s+|deshalb\s+)?keine?\b[^.]{0,40}"
               r"\b(?:nennen|angeben|beziffern)", re.IGNORECASE),
    re.compile(r"\bnicht\s+(?:empirisch\s+)?(?:erfasst|erhoben|belegt|"
               r"verfügbar)\b", re.IGNORECASE),
    re.compile(r"\bkeine\s+(?:konkrete\s+)?Kostenangabe", re.IGNORECASE),
    re.compile(r"\bzu\s+\w+\s+liegen\s+(?:mir|uns)\s+keine", re.IGNORECASE),
    re.compile(r"\bohne\s+(?:eigene\s+)?(?:Machbarkeitsstudie|Wärmeplan|"
               r"Datengrundlage)\b[^.]{0,50}\bkeine\b", re.IGNORECASE),
]

KENNZEICHNUNG = [
    re.compile(r"\bbundesweit\w*\s+(?:Durchschnitt|Mittel|Erfahrungs|Richt)"
               r"\w*", re.IGNORECASE),
    re.compile(r"\bnicht\s+\w+-?\s*spezifisch", re.IGNORECASE),
    re.compile(r"\bkeine\s+Prognose\s+für\b", re.IGNORECASE),
    re.compile(r"\bOrientierungswert", re.IGNORECASE),
    re.compile(r"\bnur\s+(?:ein\s+)?(?:grober?\s+)?(?:Anhalts|Richt)wert",
               re.IGNORECASE),
    re.compile(r"\bnicht\s+auf\s+Daten\s+(?:Ihrer|dieser)\s+Kommune",
               re.IGNORECASE),
]


def negative_rejection(text: str, hat_kommunendaten: bool = False) -> dict:
    if hat_kommunendaten:
        return {"nr": None, "art": "nicht anwendbar", "belege": []}
    if not text:
        return {"nr": 0, "art": "keine", "belege": []}

    e = [m.group(0).strip() for p in ENTHALTUNG if (m := p.search(text))]
    k = [m.group(0).strip() for p in KENNZEICHNUNG if (m := p.search(text))]

    if e and k:
        art = "beides"
    elif e:
        art = "enthaltung"
    elif k:
        art = "kennzeichnung"
    else:
        art = "keine"

    return {"nr": int(bool(e or k)), "art": art, "belege": e + k}
