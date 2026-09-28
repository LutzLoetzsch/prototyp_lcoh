#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from config import LLM


def system_prompt_antwort() -> str:
    return (
        "Du beantwortest Fragen von Mitarbeitenden einer kleinen Kommune zur "
        "kommunalen Wärmeplanung. Die Rechnung hat bereits ein geprüftes "
        "Entscheidungssystem durchgeführt; du formulierst die Antwort.\n\n"
        "Regeln:\n"
        "1. ZAHLEN: Verwende ausschließlich die Werte aus dem Abschnitt "
        "'Rechenergebnis'. Rechne NICHTS selbst aus, runde nicht um, schätze "
        "nicht. Gibt es keinen Wert, sage das.\n"
        "1a. WELCHER WERT GILT: Das Feld 'vorteilhaftere_option' nennt die "
        "günstigere Versorgungsart. Das Feld 'lcoh' ist der zugehörige "
        "Wärmepreis; 'lcoh_netz' und 'lcoh_dez' sind die beiden Vergleichswerte. "
        "Nenne die vorteilhaftere Option und den Wert aus 'lcoh'.\n"
        "1b. EINHEIT UND SCHREIBWEISE: Der Wärmepreis steht in EUR/MWh. "
        "Schreibe Zahlen deutsch, mit Komma als Dezimaltrennzeichen "
        "(170,23 EUR/MWh). Verwende KEINE Feldnamen im Antworttext.\n"
        "2. QUELLEN: Nenne zu jedem kommunalen Wert die Quelle so, wie sie im "
        "Abschnitt 'Belegte Daten' steht — mit Datensatz, Bezugsjahr und "
        "Lizenz, sofern angegeben. Erfinde KEINE Quellen. Steht dort nichts, "
        "gibt es keine Quelle.\n"
        "3. ANNAHMEN: Werte aus dem Abschnitt 'Vom Modell angenommen' sind "
        "KEINE kommunalen Daten, sondern Modellvorgaben. Sage das ausdrücklich, "
        "wenn du sie verwendest.\n"
        "4. OHNE DATEN: Liegen keine belegten Daten vor, sage klar, dass die "
        "Rechnung auf Modellvorgaben beruht und nicht die Lage dieser Kommune "
        "abbildet. Beschönige das nicht.\n"
        "5. SPRACHE: Deutsch, sachlich, ohne Fachjargon, höchstens 150 Wörter. "
        "Die Antwort geht an eine Person, die sie im Gemeinderat vertreten muss."
    )


def user_prompt_antwort(frage: str, kontext: str | None, ergebnis: dict,
                        extrahiert: dict, angenommen: list) -> str:
    teile = []

    if kontext:
        teile.append("Belegte Daten aus der Wissensbasis:\n" + kontext)
    else:
        teile.append("Belegte Daten aus der Wissensbasis:\n"
                     "(keine — für diese Kommune sind keine Daten angebunden)")

    if extrahiert:
        teile.append("Aus den Daten übernommene Werte:\n"
                     + json.dumps(extrahiert, ensure_ascii=False, indent=2))
    else:
        teile.append("Aus den Daten übernommene Werte:\n(keine)")

    if angenommen:
        teile.append("Vom Modell angenommen (KEINE kommunalen Daten):\n"
                     + ", ".join(sorted(angenommen)))

    teile.append("Rechenergebnis des Entscheidungssystems:\n"
                 + json.dumps(ergebnis, ensure_ascii=False, indent=2))

    teile.append("Frage:\n" + frage)
    teile.append("Beantworte die Frage nach den Regeln.")
    return "\n\n".join(teile)


def _client(llm: dict = LLM):
    from openai import OpenAI
    return OpenAI(base_url=llm["base_url"], api_key="ollama")


def erzeuge_antwort(frage: str, kontext: str | None, ergebnis: dict,
                    extrahiert: dict | None = None,
                    angenommen: list | None = None,
                    *, llm: dict = LLM, client=None) -> str:
    client = client or _client(llm)
    antwort = client.chat.completions.create(
        model=llm["model"],
        messages=[
            {"role": "system", "content": system_prompt_antwort()},
            {"role": "user", "content": user_prompt_antwort(
                frage, kontext, ergebnis, extrahiert or {}, angenommen or [])},
        ],
        temperature=llm.get("temperature", 0.0),
    )
    return (antwort.choices[0].message.content or "").strip()
