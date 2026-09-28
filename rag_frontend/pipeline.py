from __future__ import annotations

from llm_client import extrahiere
from decision_client import entscheide


def klartext_zu_entscheidung(klartext: str, kontext: str | None = None, *,
                             client=None) -> dict:
    p = extrahiere(klartext, kontext, client=client)
    ergebnis = entscheide(p.als_eingabe())
    ergebnis["extrahiert"] = p.als_eingabe()
    return ergebnis
