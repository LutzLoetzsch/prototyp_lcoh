#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import time

from dotenv import load_dotenv

from extern import system_prompt_extern

load_dotenv()

MODELLE = {
    "T": "gpt-5.6-terra",
    "S": "gpt-5.6-sol",
}

WEBSUCHE_WERKZEUG = {"type": "web_search"}
MAX_AUSGABE = 1500


def _client():
    from openai import OpenAI
    schluessel = os.environ.get("OPENAI_API_KEY")
    if not schluessel:
        raise SystemExit("OPENAI_API_KEY nicht gesetzt (.env prüfen)")
    return OpenAI(api_key=schluessel)


def _suchanfragen(antwort) -> list[str]:
    treffer: list[str] = []
    for element in getattr(antwort, "output", []) or []:
        if "web_search" not in str(getattr(element, "type", "")):
            continue
        for feld in ("action", "input", "arguments"):
            wert = getattr(element, feld, None)
            if isinstance(wert, dict) and wert.get("query"):
                treffer.append(str(wert["query"]))
                break
            q = getattr(wert, "query", None)
            if q:
                treffer.append(str(q))
                break
    return treffer


def frage_extern_openai(frage: str, modell_kurz: str, websuche: bool,
                        *, client=None,
                        max_tokens: int = MAX_AUSGABE) -> dict:
    client = client or _client()
    modell = MODELLE[modell_kurz]

    kwargs = {
        "model": modell,
        "instructions": system_prompt_extern(),
        "input": frage,
        "max_output_tokens": max_tokens,
    }
    if websuche:
        kwargs["tools"] = [WEBSUCHE_WERKZEUG]

    t0 = time.perf_counter()
    fehler = None
    text = ""
    suchanfragen: list[str] = []
    verbrauch: dict = {}
    try:
        antwort = client.responses.create(**kwargs)
        text = getattr(antwort, "output_text", "") or ""
        suchanfragen = _suchanfragen(antwort)
        u = getattr(antwort, "usage", None)
        if u is not None:
            verbrauch = {"eingabe_token": getattr(u, "input_tokens", None),
                         "ausgabe_token": getattr(u, "output_tokens", None)}
    except Exception as e:
        fehler = f"{type(e).__name__}: {e}"

    return {"anbieter": "openai", "modell": modell, "websuche": websuche,
            "antwort": text.strip(), "suchanfragen": suchanfragen,
            "anzahl_suchen": len(suchanfragen),
            "verbrauch": verbrauch, "fehler": fehler,
            "latenz_s": round(time.perf_counter() - t0, 2)}


if __name__ == "__main__":
    frage = ("Wie wirtschaftlich wäre ein Wärmenetz in Johanngeorgenstadt? "
             "Was kostet die Wärme ungefähr pro Megawattstunde?")
    antworten = []
    for kurz, suche in (("T", False), ("T", True)):
        r = frage_extern_openai(frage, kurz, suche)
        antworten.append(r["antwort"] or "(leer)")
    print("\n\n".join(antworten))
