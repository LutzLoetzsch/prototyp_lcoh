#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re

_EUR_MWH = r"(?:EUR|€|Euro)\s*(?:/|pro\s+)\s*(?:MWh|Megawattstunde\w*)"
_CT_KWH = r"(?:Ct|Cent)\s*(?:/|pro\s+)\s*(?:kWh|Kilowattstunde\w*)"

_ZAHL = r"\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?"
_TRENNER = r"(?:-|–|—|bis|und)"

_SPANNE_EUR_A = re.compile(
    rf"({_ZAHL})\s*{_TRENNER}\s*({_ZAHL})\s*{_EUR_MWH}", re.IGNORECASE)
_SPANNE_EUR_B = re.compile(
    rf"({_ZAHL})\s*{_EUR_MWH}\s*{_TRENNER}\s*({_ZAHL})\s*{_EUR_MWH}",
    re.IGNORECASE)
_SPANNE_CT_A = re.compile(
    rf"({_ZAHL})\s*{_TRENNER}\s*({_ZAHL})\s*{_CT_KWH}", re.IGNORECASE)
_SPANNE_CT_B = re.compile(
    rf"({_ZAHL})\s*{_CT_KWH}\s*{_TRENNER}\s*({_ZAHL})\s*{_CT_KWH}",
    re.IGNORECASE)

_EINZEL_EUR = re.compile(rf"({_ZAHL})\s*{_EUR_MWH}", re.IGNORECASE)
_EINZEL_CT = re.compile(rf"({_ZAHL})\s*{_CT_KWH}", re.IGNORECASE)


def _zu_float(roh: str) -> float | None:
    s = roh.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def lcoh_befund(text: str) -> dict:
    leer = {"art": "keine", "werte": [], "vertreter": None,
            "einheit": None, "fundstelle": None}
    if not text:
        return leer

    # Spezifische Form mit zwei Einheiten zuerst prüfen.
    for muster, faktor, einheit in ((_SPANNE_EUR_B, 1.0, "EUR/MWh"),
                                    (_SPANNE_CT_B, 10.0, "Ct/kWh (umgerechnet)"),
                                    (_SPANNE_EUR_A, 1.0, "EUR/MWh"),
                                    (_SPANNE_CT_A, 10.0, "Ct/kWh (umgerechnet)")):
        m = muster.search(text)
        if m:
            a, b = _zu_float(m.group(1)), _zu_float(m.group(2))
            if a is not None and b is not None:
                werte = sorted(round(x * faktor, 2) for x in (a, b))
                return {"art": "spanne", "werte": werte,
                        "vertreter": round(sum(werte) / 2, 2),
                        "einheit": einheit, "fundstelle": m.group(0)}

    for muster, faktor, einheit in ((_EINZEL_EUR, 1.0, "EUR/MWh"),
                                    (_EINZEL_CT, 10.0, "Ct/kWh (umgerechnet)")):
        m = muster.search(text)
        if m:
            a = _zu_float(m.group(1))
            if a is not None:
                w = round(a * faktor, 2)
                return {"art": "einzelwert", "werte": [w], "vertreter": w,
                        "einheit": einheit, "fundstelle": m.group(0)}

    return leer


def lcoh_aus_text(text: str) -> float | None:
    return lcoh_befund(text)["vertreter"]


def de(x, stellen: int = 2, leer: str = "—") -> str:
    if x is None:
        return leer
    if isinstance(x, bool):
        return "ja" if x else "nein"
    if isinstance(x, int):
        return f"{x:,}".replace(",", ".")
    try:
        s = f"{float(x):,.{stellen}f}"
    except (TypeError, ValueError):
        return str(x)
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


_ALLE = re.compile(r"\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def zahlen_kandidaten(text: str) -> set[float]:
    treffer: set[float] = set()
    if not text:
        return treffer
    for roh in _ALLE.findall(text):
        s = roh.replace(" ", "")
        # Punkt kann Dezimal- oder Tausendertrennzeichen sein.
        for kandidat in (s.replace(".", "").replace(",", "."),
                         s.replace(",", "")):
            try:
                treffer.add(float(kandidat))
            except ValueError:
                pass
    return treffer
