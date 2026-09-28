#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re

BLOECKE = ("stammdaten", "waermebedarf", "trajektorie", "netz", "erzeuger",
           "realisierung", "potenzial")

STATUS_UNBELEGT = ("zu_beschaffen", "illustrativ", "annahme")
KOMMUNE_MODI = ("aus", "voll", "ort")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _ortsname(profil: dict) -> str:
    meta = profil.get("_meta", {})
    ort = meta.get("ort")
    if isinstance(ort, dict):
        ort = ort.get("wert")
    if isinstance(ort, str) and ort.strip():
        return ort.strip()
    name = str(meta.get("name", "unbekannt"))
    return name.split("(")[0].strip() or name.strip()


def _feld_text(name: str, feld, mit_status: bool = False) -> str:
    if isinstance(feld, dict) and "wert" in feld:
        w = feld.get("wert")
        e = feld.get("einheit", "")
        q = feld.get("quelle", "")
        st = feld.get("status", "")

        wert_text = "nicht belegt" if w is None else f"{w}"
        teil = f"{name}: {wert_text} {e}".strip()

        zusatz = []
        if q:
            zusatz.append(f"Quelle: {q}")
        if mit_status and st:
            if w is None:
                zusatz.append(f"Status: {st} -- KEIN Wert vorhanden, "
                              f"Quellenangabe nennt die vorgesehene Herkunft")
            elif st in STATUS_UNBELEGT:
                zusatz.append(f"Status: {st} -- nicht belegt")
            else:
                zusatz.append(f"Status: {st}")

        return f"{teil} ({'; '.join(zusatz)})" if zusatz else teil

    if isinstance(feld, dict):
        inner = "; ".join(_feld_text(k, v, mit_status) for k, v in feld.items())
        return name + " {" + inner + "}"
    return f"{name}: {feld}"


def _block_text(block: str, inhalt: dict, kopf: str | None = None,
                mit_status: bool = False) -> str:
    praefix = f"[{kopf} | {block}] " if kopf else f"[{block}] "
    return praefix + " | ".join(_feld_text(k, v, mit_status) for k, v in inhalt.items())


def chunk_profil(profil: dict, kommune_modus: str = "aus",
                 mit_status: bool = False) -> list[dict]:
    if kommune_modus not in KOMMUNE_MODI:
        raise ValueError(f"kommune_modus muss aus {KOMMUNE_MODI} sein, "
                         f"nicht {kommune_modus!r}")

    name_voll = profil.get("_meta", {}).get("name", "unbekannt")
    kopf = {"aus": None, "voll": name_voll, "ort": _ortsname(profil)}[kommune_modus]

    chunks = []
    for block in BLOECKE:
        if block in profil and isinstance(profil[block], dict):
            chunks.append({
                "chunk_id": f"{_slug(name_voll)}::{block}",
                "kommune": name_voll,
                "block": block,
                "text": _block_text(block, profil[block], kopf, mit_status),
            })
    return chunks
