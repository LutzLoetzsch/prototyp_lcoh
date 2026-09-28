from __future__ import annotations

import json

from pydantic import ValidationError

from config import LLM
from schema import Parametersatz
from prompt import system_prompt, user_prompt


def _client(llm: dict = LLM):
    from openai import OpenAI
    return OpenAI(base_url=llm["base_url"], api_key="ollama")


def extrahiere(klartext: str, kontext: str | None = None, *,
               llm: dict = LLM, client=None, max_versuche: int = 3) -> Parametersatz:
    client = client or _client(llm)
    nachrichten = [
        {"role": "system", "content": system_prompt()},
        {"role": "user", "content": user_prompt(klartext, kontext)},
    ]
    letzter = None
    for _ in range(max_versuche):
        antwort = client.chat.completions.create(
            model=llm["model"], messages=nachrichten,
            temperature=llm.get("temperature", 0.0),
            response_format={"type": "json_object"},
        )
        roh = antwort.choices[0].message.content
        try:
            daten = {k: v for k, v in json.loads(roh).items() if v is not None}
            return Parametersatz(**daten)
        except (json.JSONDecodeError, ValidationError) as e:
            letzter = e
            nachrichten.append({"role": "assistant", "content": roh})
            nachrichten.append({"role": "user", "content":
                f"Die Ausgabe war ungültig ({e}). Gib AUSSCHLIESSLICH gültiges JSON "
                "nach dem Schema aus, nur belegte Felder, ohne Kommentar."})
    raise ValueError(f"Extraktion nach {max_versuche} Versuchen fehlgeschlagen: {letzter}")
