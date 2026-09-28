#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from zahlen import lcoh_aus_text, lcoh_befund  # noqa: F401

load_dotenv()

MODELLE = {
    "S": "claude-sonnet-5",
    "O": "claude-opus-5",
}

WEBSUCHE_WERKZEUG = {"type": "web_search_20250305", "name": "web_search"}
MAX_AUSGABE = 1500


def system_prompt_extern() -> str:
    return (
        "Du beantwortest Fragen von Mitarbeitenden einer kleinen Kommune zur "
        "kommunalen Wärmeplanung.\n\n"
        "Regeln:\n"
        "1. ZAHLEN: Nenne konkrete Zahlen, soweit du sie verantworten kannst. "
        "Kennzeichne, worauf sie beruhen. Kannst du keine Zahl verantworten, "
        "sage das.\n"
        "2. QUELLEN: Nenne zu jeder Zahl die Quelle so genau wie möglich — "
        "Datensatz, Bezugsjahr, Fundstelle. Erfinde KEINE Quellen.\n"
        "3. ANNAHMEN: Was auf Durchschnittswerten oder Erfahrungswerten beruht "
        "und nicht auf Daten dieser Kommune, ist ausdrücklich als solches zu "
        "kennzeichnen.\n"
        "4. OHNE DATEN: Liegen dir keine Daten zu dieser Kommune vor, sage das "
        "klar. Beschönige es nicht.\n"
        "5. SPRACHE: Deutsch, sachlich, ohne Fachjargon, höchstens 150 Wörter. "
        "Die Antwort geht an eine Person, die sie im Gemeinderat vertreten muss."
    )


def _client():
    import anthropic
    schluessel = os.environ.get("CLAUDE_API_KEY")
    if not schluessel:
        raise SystemExit("CLAUDE_API_KEY nicht gesetzt (.env prüfen)")
    return anthropic.Anthropic(api_key=schluessel)


def frage_extern(frage: str, modell_kurz: str, websuche: bool,
                 *, client=None, max_tokens: int = MAX_AUSGABE) -> dict:
    client = client or _client()
    modell = MODELLE[modell_kurz]

    kwargs = {
        "model": modell,
        "max_tokens": max_tokens,
        "system": system_prompt_extern(),
        "messages": [{"role": "user", "content": frage}],
    }
    if websuche:
        kwargs["tools"] = [WEBSUCHE_WERKZEUG]

    t0 = time.perf_counter()
    fehler = None
    text = ""
    suchanfragen: list[str] = []
    verbrauch = {}
    try:
        antwort = client.messages.create(**kwargs)
        for block in antwort.content:
            typ = getattr(block, "type", None)
            if typ == "text":
                text += getattr(block, "text", "")
            elif typ == "server_tool_use":
                eingabe = getattr(block, "input", {}) or {}
                if isinstance(eingabe, dict) and eingabe.get("query"):
                    suchanfragen.append(str(eingabe["query"]))
        u = getattr(antwort, "usage", None)
        if u is not None:
            verbrauch = {"eingabe_token": getattr(u, "input_tokens", None),
                         "ausgabe_token": getattr(u, "output_tokens", None)}
    except Exception as e:
        fehler = f"{type(e).__name__}: {e}"

    return {"anbieter": "anthropic", "modell": modell, "websuche": websuche,
            "antwort": text.strip(), "suchanfragen": suchanfragen,
            "anzahl_suchen": len(suchanfragen),
            "verbrauch": verbrauch, "fehler": fehler,
            "latenz_s": round(time.perf_counter() - t0, 2)}


if __name__ == "__main__":
    r = frage_extern("Was kostet die Wärme aus einem Nahwärmenetz in "
                     "Johanngeorgenstadt ungefähr pro Megawattstunde?",
                     "S", websuche=False)
    print(r["antwort"] or "(leer)")
