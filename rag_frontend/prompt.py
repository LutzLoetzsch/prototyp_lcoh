from __future__ import annotations

# name: (Beschreibung, Einheit, (min, max))
PARAMETER = {
    "wacc": ("Kapitalkostensatz (WACC)", "Anteil", (0.03, 0.06)),
    "foerderquote": ("Förderquote auf die Investition (Erzeuger/dezentral)", "Anteil", (0.0, 0.4)),
    "bedarfsrate": ("jährliche Änderungsrate des Wärmebedarfs", "Anteil/Jahr", (-0.02, 0.02)),
    "co2_preis": ("CO₂-Preis", "EUR/t", (0.0, 200.0)),
    "grundlast_anteil": ("Grundlastanteil der Wärmepumpe an der Wärmemenge", "Anteil", (0.5, 0.85)),
    "jaz": ("Jahresarbeitszahl der Großwärmepumpe", "-", (2.6, 3.4)),
    "capex_wp": ("spezifische Investition Großwärmepumpe", "EUR/kW", (719.0, 1243.0)),
    "strompreis": ("Strompreis für die Großwärmepumpe (NETZBEZUG, nicht Endkundentarif)", "EUR/MWh", (50.0, 120.0)),
    "vlh_wp": ("Volllaststunden der Wärmepumpe", "h/a", (3500.0, 4500.0)),
    "nutzungsgrad": ("Nutzungsgrad des Biomassekessels", "Anteil", (0.82, 0.92)),
    "capex_bio": ("spezifische Investition Biomasse", "EUR/kW", (820.0, 1070.0)),
    "brennstoffpreis": ("Brennstoffpreis (Holz/Hackschnitzel)", "EUR/MWh", (25.0, 45.0)),
    "vlh_bio": ("Volllaststunden Biomasse", "h/a", (1200.0, 1800.0)),
    "waermeliniendichte": ("Wärmeliniendichte (Wärmeabsatz je Trassenmeter)", "MWh/(m*a)", (0.8, 3.0)),
    "netz_invest": ("spezifische Netzinvestition (Hauptleitung)", "EUR/m", (692.0, 2459.0)),
    "verlustanteil": ("Wärmeverlustanteil im Netz", "Anteil", (0.14, 0.163)),
    "netz_foerderquote": ("Förderquote auf die Netzinvestition (BEW)", "Anteil", (0.0, 0.4)),
    "hausanschluss": ("spezifische Hausanschlusskosten", "EUR/(MWh/a)", (0.0, 400.0)),
    "betrachtungszeitraum": ("Betrachtungszeitraum der Wirtschaftlichkeitsrechnung", "a", (15.0, 45.0)),
}

HERLEITUNG = {
    "trassenlaenge_m": ("Länge der geplanten Wärmenetz-Trasse", "m"),
    "waermelieferung_mwh_a": ("jährlich gelieferte Wärmemenge im Netzgebiet", "MWh/a"),
}


def schema_block() -> str:
    return "\n".join(
        f"- {n}: {b} [{lo}-{hi}] {e}" for n, (b, e, (lo, hi)) in PARAMETER.items()
    )


def herleitungs_block() -> str:
    zeilen = "\n".join(f"- {n}: {b} in {e}" for n, (b, e) in HERLEITUNG.items())
    return (
        zeilen + "\n"
        "Werden BEIDE genannt, gib beide zurück und setze waermeliniendichte NICHT.\n"
        "Das Entscheidungssystem bildet sie selbst als\n"
        "  waermeliniendichte = waermelieferung_mwh_a / trassenlaenge_m\n"
        "Rechne das NICHT selbst aus."
    )


def system_prompt() -> str:
    return (
        "Du extrahierst Parameter für die kommunale Wärmeplanung aus dem Klartext "
        "einer Kommune in ein striktes JSON-Objekt.\n\n"
        "Felder (Name: Bedeutung [Band] Einheit):\n" + schema_block() + "\n\n"
        "Zusätzlich zulässig, statt waermeliniendichte:\n" + herleitungs_block() + "\n\n"
        "Regeln:\n"
        "1. Setze ein Feld NUR, wenn der Wert im Text explizit genannt oder direkt "
        "daraus ableitbar ist.\n"
        "2. Erfinde nichts. Unbekannte Felder LÄSST DU WEG — nicht raten, keine "
        "typischen Werte einsetzen.\n"
        "3. Gib den genannten Zahlenwert in der angegebenen Einheit zurück, auch wenn "
        "er außerhalb des Bandes liegt (Daten nicht verändern).\n"
        "4. EINHEITEN UMRECHNEN: Verlangt ein Feld einen Anteil und ist der Wert als "
        "Prozent angegeben (Einheit '%' oder '%/a'), teile durch 100. "
        "Beispiele: -2,0 %/a -> -0.02 | 16,0 % -> 0.16 | 30 % -> 0.3. "
        "Betroffen sind: bedarfsrate, verlustanteil, wacc, foerderquote, "
        "netz_foerderquote, grundlast_anteil, nutzungsgrad. "
        "Das ist KEINE Änderung des Werts, sondern seine Umrechnung in die "
        "geforderte Einheit.\n"
        "5. Antworte mit einem EINZIGEN JSON-Objekt, nur belegte Felder, ohne Kommentar."
    )


def user_prompt(klartext: str, kontext: str | None = None) -> str:
    teile = []
    if kontext:
        teile.append("Kontext (belegte Quellen):\n" + kontext)
    teile.append("Klartext der Kommune:\n" + klartext)
    teile.append("Extrahiere die belegten Parameter als JSON.")
    return "\n\n".join(teile)
