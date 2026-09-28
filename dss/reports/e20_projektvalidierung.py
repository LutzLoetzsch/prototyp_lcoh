#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from dss.arme.bio import lcoh_bio
from dss.arme.gas_dez import lcoh_gas_dez
from dss.arme.wp import lcoh_wp
from dss.entscheidung.dez_referenz import lcoh_dez
from dss.szenarien.m6 import M6_BASIS, lcoh_m6

import _lauf

TOLERANZ = 0.15


def _basis(**ov) -> dict:
    return {**M6_BASIS, "bedarfsrate": 0.0, "co2_preis": 0.0, **ov}


def v12_k1() -> dict:
    fest = {"wacc": 0.08, "betrachtungszeitraum": 20.0, "wartung_wp": 0.03,
            "jaz": 2.1, "foerderquote": 0.0}
    punkte = [(1247, 120.0, (450.0, 550.0)),
              (3500, 126.0, (150.0, 250.0)),
              (6000, 140.0, (100.0, 170.0))]
    zeilen = []
    for vlh, strom, band in punkte:
        werte = {}
        for capex in (700.0, 1150.0, 1600.0):
            p = _basis(**fest, capex_wp=capex, vlh_wp=float(vlh), strompreis=strom)
            werte[capex] = round(lcoh_wp(p), 3)
        spanne = (min(werte.values()), max(werte.values()))
        trifft = not (spanne[1] < band[0] or spanne[0] > band[1])
        zeilen.append({"vollbenutzungsstunden": vlh, "strompreis": strom,
                       "modell": werte, "modellspanne": [round(x, 2) for x in spanne],
                       "quelle_band": list(band), "trifft": trifft,
                       "speicherbedarf_kwh_pro_kw": {1247: 9, 3500: 5, 6000: 0}[vlh]})
    return {"id": "V12", "komposition": "K1",
            "quelle": "Agora Energiewende / Fraunhofer IEG (2023): Roll-out von "
                      "Großwärmepumpen in Deutschland",
            "fundstelle": "Tab. 3 S. 78 (Annahmen), Abb. 31 S. 76 (CAPEX), "
                          "Abb. 32 S. 80 (Ergebnis)",
            "systemgrenze": "Erzeugung, ohne Netz, ohne Förderung",
            "preisbasis": "netto, Projektion 2030",
            "art": "Kurvenschar", "zeilen": zeilen,
            "befund": "Das Modell trifft dort, wo die Quelle keinen Wärmespeicher "
                      "ansetzt, und weicht dort ab, wo sie einen ansetzt. Der "
                      "Speicherbedarf steht in derselben Tab. 3: 9 kWh/kW bei "
                      "1.247 h, 5 bei 3.500 h, 0 bei 6.000 h. Das Modell führt "
                      "keinen Speicherterm -- eine benannte FF3-Grenze."}


def v13_verhaeltnis() -> dict:
    from dss.fachmodell.enums import Brennstoffart, Groessenklasse, Waermequelle
    from dss.fachmodell.erzeugervariante import Biomassefeuerung, Waermepumpe
    from dss.fachmodell.realisierung import Realisierung

    ziel_wp, ziel_bio = 103.0, 79.0
    ziel = ziel_bio / ziel_wp

    def paar(vlh: float, strom: float) -> tuple[float, float]:
        wp = Waermepumpe(leistung=960.0, lebensdauer=15, investitionskosten=1400.0,
                         betriebskostenFix=0.0281 * 1400.0,
                         groessenklasse=Groessenklasse.NETZGEBUNDEN,
                         jahresarbeitszahl=2.30, waermequelle=Waermequelle.LUFT,
                         quellentemperatur=0.0)
        bio = Biomassefeuerung(leistung=999.0, lebensdauer=15,
                               investitionskosten=673.0,
                               betriebskostenFix=0.099 * 673.0,
                               groessenklasse=Groessenklasse.NETZGEBUNDEN,
                               wirkungsgrad=0.95,
                               brennstoff=Brennstoffart.HOLZHACKSCHNITZEL)
        r = lambda preis: Realisierung(wacc=0.045, volllaststunden=vlh,
                                       energiepreis_eur_pro_mwh=preis,
                                       foerderquote=0.0)
        return (wp.waermegestehungskosten(r(strom)),
                bio.waermegestehungskosten(r(32.6)))

    zeilen = []
    for vlh in (4000.0, 5000.0, 6000.0, 6979.0):
        for strom in (95.0, 110.0, 125.0):
            w, b = paar(vlh, strom)
            zeilen.append({"vollbenutzungsstunden": vlh, "strompreis": strom,
                           "lcoh_wp": round(w, 3), "lcoh_bio": round(b, 3),
                           "verhaeltnis": round(b / w, 4),
                           "abweichung": round((b / w) / ziel - 1.0, 5)})
    beste = min(zeilen, key=lambda z: abs(z["abweichung"]))
    bei_110 = [z for z in zeilen if z["strompreis"] == 110.0]
    spanne = (min(z["abweichung"] for z in bei_110),
              max(z["abweichung"] for z in bei_110))
    return {"id": "V13", "komposition": "K2 (Verhältnistest gegen K1)",
            "quelle": "DME Consult / LoCarDi (2024): Wirtschaftlichkeitsanalyse "
                      "Großwärmepumpen, Anwendungsfall Neuburg a. d. Donau",
            "fundstelle": "Anhang S. VII-VIII (WP), S. XXXIV (Biomasse), Abb. 03-3",
            "systemgrenze": "identische Infrastrukturumlage auf beiden Technologien",
            "preisbasis": "netto (S. 7 ausdrücklich), Bezugsjahr 2023",
            "art": "Verhältnistest", "ziel_verhaeltnis": round(ziel, 4),
            "zeilen": zeilen, "beste_abweichung": beste["abweichung"],
            "spanne_bei_strom_110": [round(x, 5) for x in spanne],
            "im_toleranzband": abs(beste["abweichung"]) <= TOLERANZ,
            "befund": "Das Ergebnis ist über die Vollbenutzungsstunden stabil: Bei "
                      "einem Strombezug von 110 EUR/MWh liegt die Abweichung "
                      "durchgehend zwischen -3,7 und -4,5 Prozent, obwohl die "
                      "Stundenzahl um Faktor 1,7 variiert. Der Strombezug der Quelle "
                      "ist Day-Ahead 2023 zuzüglich 17 EUR/kW Leistungspreis und "
                      "620 EUR Messpreis und liegt damit im mittleren Teil der "
                      "geprüften Spanne."}


def v13_k6() -> dict:
    import dss.entscheidung.dez_referenz as dz
    invest = 25000.0 * 1.5 + 2000.0 * 1.3
    leistung = 15.0
    alt = (dz.CAPEX_DEZ, dz.VLH_DEZ, dz.WARTUNG_DEZ, dz.FOERDER_DEZ, dz.LD_DEZ)
    try:
        dz.CAPEX_DEZ = invest / leistung
        dz.VLH_DEZ = 25000.0 / leistung
        dz.WARTUNG_DEZ = 272.0 / invest
        dz.FOERDER_DEZ = 0.52
        dz.LD_DEZ = 20
        modell = dz.lcoh_dez(_basis(strompreis=242.0 - 150.0, jaz=3.0,
                                    wacc=0.0001, betrachtungszeitraum=20.0))
    finally:
        (dz.CAPEX_DEZ, dz.VLH_DEZ, dz.WARTUNG_DEZ,
         dz.FOERDER_DEZ, dz.LD_DEZ) = alt
    ziel = 131.0
    return {"id": "V13", "komposition": "K6", "quelle": "wie V13",
            "fundstelle": "Anhang S. XXXV f.",
            "systemgrenze": "Vollkosten der Hausanlage, mit BEG-Förderung",
            "preisbasis": "netto, Bezugsjahr 2023", "art": "Punktwert",
            "eingang": {"investition_eur": invest, "leistung_kw": leistung,
                        "capex_eur_pro_kw": round(invest / leistung, 1),
                        "jaz": 3.0, "vollbenutzungsstunden": round(25000.0 / leistung, 1),
                        "strompreis_eur_pro_mwh": 242.0, "zins": 0.0001,
                        "foerderquote": 0.52},
            "zielwert": ziel, "modell": round(modell, 3),
            "abweichung": round(modell / ziel - 1.0, 5),
            "im_toleranzband": abs(modell / ziel - 1.0) <= TOLERANZ}


def v14_k5() -> dict:
    Q, L, N = 1147.81, 730.0, 19
    fest = {"waermeliniendichte": Q / L, "wacc": 0.015,
            "betrachtungszeitraum": 20.0, "verlustanteil": 0.161,
            "grundlast_anteil": 1e-9, "capex_wp": 945.0, "strompreis": 35.0,
            "jaz": 0.88, "vlh_wp": 2300.0, "wartung_wp": 0.014,
            "netz_foerderquote": 0.0, "foerderquote": 0.0,
            "brennstoffpreis": 35.0, "nutzungsgrad": 0.88, "vlh_bio": 2300.0,
            "wartung_bio": 0.014, "netz_betriebskostenanteil": 0.002,
            "capex_bio": 945.0}
    ziel = 87.7
    zeilen = []
    for ha_eur, ha_lab in ((5150.0, "TK Tab 42 Z. 21, Mitte"),
                           (400.0 * Q / N, "Modellwert 400 EUR/(MWh*a) rückgerechnet")):
        ha_spez = ha_eur * N / Q
        for netz_invest, ni_lab in ((370.0, "PEX-Flexrohr, SAENA Q84"),
                                    (692.0, "TK Tab 42 Z. 25, unten")):
            m = lcoh_m6(_basis(**fest, netz_invest=netz_invest,
                               hausanschluss=ha_spez))
            zeilen.append({"hausanschluss_eur_je_anschluss": round(ha_eur, 1),
                           "hausanschluss_herkunft": ha_lab,
                           "hausanschluss_eur_pro_mwh_a": round(ha_spez, 1),
                           "netz_invest": netz_invest, "netz_herkunft": ni_lab,
                           "modell": round(m, 3),
                           "abweichung": round(m / ziel - 1.0, 5)})
    beste = min(zeilen, key=lambda z: abs(z["abweichung"]))
    return {"id": "V14", "komposition": "K5",
            "quelle": "ratioplan GmbH (2017): Projektstudie Nahwärmeversorgung "
                      "Markt Heimenkirch, Variante 5",
            "fundstelle": "Abschn. 5.1, 5.3, 7, 12, 13.3; Abb. 16 und 17",
            "systemgrenze": "alle Jahreskosten geteilt durch die Jahreswärmemenge, "
                            "ohne Betreiberrendite",
            "preisbasis": "NETTO (Abb. 17); der Bruttowert 10,43 ct/kWh steht in "
                          "der Tabelle und ist NICHT der Vergleichswert",
            "art": "Punktwert", "zielwert": ziel,
            "eingang": {"waermemenge_mwh_a": Q, "trassenlaenge_m": L,
                        "anschluesse": N, "mwh_je_anschluss": round(Q / N, 2),
                        "waermeliniendichte": round(Q / L, 4),
                        "verlustanteil": 0.161, "zins": 0.015,
                        "investition_eur": 769176.47},
            "zeilen": zeilen, "beste_abweichung": beste["abweichung"],
            "im_toleranzband": abs(beste["abweichung"]) <= TOLERANZ,
            "befund": "Die Hausanschlussbrücke wiegt schwerer als der Rohrtyp. "
                      "Mit dem Modellwert 400 EUR/(MWh*a) beträgt die Abweichung "
                      "rund +35 %, mit der aus TK Tab 42 gebildeten Brücke rund "
                      "+13 %. Das bestätigt die in K16 Abschn. A.2 dokumentierte "
                      "Umrechnungsfalle an einem realen Fall."}


def v15() -> dict:
    import dss.entscheidung.dez_referenz as dz
    import dss.arme.gas_dez as gd
    ergebnis = []

    ziel_wp = 21.7 / 1.19 * 10
    alt = (dz.CAPEX_DEZ, dz.VLH_DEZ, dz.WARTUNG_DEZ, dz.FOERDER_DEZ)
    try:
        dz.CAPEX_DEZ = 39800.0 / 1.19 / 15.0
        dz.VLH_DEZ = 25000.0 / 15.0
        dz.WARTUNG_DEZ = 350.0 / 39800.0
        dz.FOERDER_DEZ = 0.0
        m6_ = dz.lcoh_dez(_basis(strompreis=26.0 / 1.19 * 10 - 150.0, jaz=3.1,
                                 wacc=0.036, betrachtungszeitraum=20.0))
    finally:
        dz.CAPEX_DEZ, dz.VLH_DEZ, dz.WARTUNG_DEZ, dz.FOERDER_DEZ = alt
    ergebnis.append({"komposition": "K6", "zielwert": round(ziel_wp, 2),
                     "modell": round(m6_, 3),
                     "abweichung": round(m6_ / ziel_wp - 1.0, 5),
                     "im_toleranzband": abs(m6_ / ziel_wp - 1.0) <= TOLERANZ,
                     "hinweis": "Investition, Wartung, JAZ, Strompreis, Zins und "
                                "Horizont aus der Quelle. Nicht abgebildet ist die "
                                "Grundgebühr für den zweiten Stromzähler von "
                                "90 EUR/a (3,0 EUR/MWh)."})

    ziel_gas = 20.5 / 1.19 * 10
    alt_gas = dict(gd.GAS_DEZ_DEFAULTS)
    try:
        gd.GAS_DEZ_DEFAULTS.update({
            "capex_gas_dez": 16300.0 / 1.19 / 15.0,
            "wirkungsgrad_gas_dez": 0.90,
            "wartung_gas_dez": 270.0 / 16300.0,
            "vlh_gas_dez": 25000.0 / 15.0,
            "gaspreis": 12.8 / 1.19 * 10,
        })
        m7_ = lcoh_gas_dez(_basis(wacc=0.036, betrachtungszeitraum=20.0,
                                  foerderquote=0.0))
    finally:
        gd.GAS_DEZ_DEFAULTS.clear()
        gd.GAS_DEZ_DEFAULTS.update(alt_gas)
    ergebnis.append({"komposition": "K7", "zielwert": round(ziel_gas, 2),
                     "modell": round(m7_, 3),
                     "abweichung": round(m7_ / ziel_gas - 1.0, 5),
                     "im_toleranzband": abs(m7_ / ziel_gas - 1.0) <= TOLERANZ,
                     "hinweis": "Investition, Nutzungsgrad, Wartung, Gaspreis, Zins "
                                "und Horizont aus der Quelle. capex_gas_dez ist im "
                                "Modellstand für 20 bis 60 kW belegt, die Quelle "
                                "rechnet 15 kW. Nicht abgebildet sind Schornsteinfeger "
                                "und Grundgebühren von zusammen 305 EUR/a "
                                "(10,3 EUR/MWh)."})

    return {"id": "V15",
            "quelle": "C.A.R.M.E.N. e. V. (2026): Heizkostenvergleich, Stand 02/2026",
            "fundstelle": "Tab. 1, S. 3",
            "systemgrenze": "Vollkosten der Hausanlage",
            "preisbasis": "BRUTTO inkl. CO2-Preis 55 EUR/t; Zielwerte durch 1,19 "
                          "geteilt; co2_preis im Modell 0, da in der Quelle enthalten",
            "art": "Modellfall", "ergebnis": ergebnis}


def analytisch_geschlossen() -> dict:
    p = _basis()
    from dss.arme.gas import lcoh_gas
    from dss.arme.komposition import lcoh_komponiert
    return {"K3": {"wert": round(lcoh_gas(p), 3),
                   "begruendung": "strukturell K7 in anderer Größenklasse"},
            "K4": {"wert": round(lcoh_komponiert(p), 3),
                   "begruendung": "über die E05-Kompositionsidentität aus K1 und K2; "
                                  "Residuum der N-Arm-Komposition 0,0 (E08)"}}


def lauf() -> dict:
    return {"toleranz": TOLERANZ,
            "hinweis_bedarfsrate": "Alle Anker rechnen statisch. bedarfsrate = 0 "
                                   "statt -0,005 aus M6_BASIS. Diese Setzung "
                                   "erklärt die in K09 Abschn. 2e.3 notierte "
                                   "Differenz von 1 bis 5 EUR/MWh.",
            "V12_K1": v12_k1(), "V13_verhaeltnis": v13_verhaeltnis(),
            "V13_K6": v13_k6(), "V14_K5": v14_k5(), "V15": v15(),
            "analytisch_geschlossen": analytisch_geschlossen()}


def bericht(d: dict) -> str:
    z = ["# E20 — Projektvalidierung: sieben Kompositionen gegen vier Anker\n"]
    z.append("Die Anker sind unabhängig erstellte Vergleichsrechnungen realer "
             "Planungsfälle, **keine gemessenen Betriebsdaten**. Das ist die "
             "sachlich richtige Referenz: Die Wärmegestehungskosten sind eine "
             "Rechenvorschrift unter offengelegten Annahmen, keine Prognose.\n")
    z.append(f"**Toleranzregel:** Bei einer Abweichung über ±{d['toleranz']:.0%} sind "
             "zuerst Systemgrenze, Steuern und Bezugsjahr zu prüfen, erst danach "
             "Modellparameter.\n")
    z.append(f"**Normalisierung:** {d['hinweis_bedarfsrate']}\n")

    z.append("\n## Übersicht\n")
    z.append("| Komposition | Anker | Abweichung | im Toleranzband |")
    z.append("|---|---|---:|---|")
    v12 = d["V12_K1"]
    trefferzahl = sum(1 for x in v12["zeilen"] if x["trifft"])
    z.append(f"| K1 Großwärmepumpe | V12 | Bandvergleich: {trefferzahl} von "
             f"{len(v12['zeilen'])} Punkten im Band | siehe Befund |")
    vr = d["V13_verhaeltnis"]
    z.append(f"| K2 Biomasse | V13 Verhältnistest | **{vr['beste_abweichung']*100:+.2f} %** | "
             f"{'ja' if vr['im_toleranzband'] else 'NEIN'} |")
    ag = d["analytisch_geschlossen"]
    z.append("| K3 Gas zentral | über E05-Identität | — | analytisch geschlossen |")
    z.append("| K4 WP + Bio | über E05-Identität | — | analytisch geschlossen |")
    v14 = d["V14_K5"]
    z.append(f"| K5 Bio + Netz | V14 | **{v14['beste_abweichung']*100:+.2f} %** | "
             f"{'ja' if v14['im_toleranzband'] else 'NEIN'} |")
    k6a = d["V13_K6"]
    k6b = next(x for x in d["V15"]["ergebnis"] if x["komposition"] == "K6")
    z.append(f"| K6 dezentrale WP | V13 | **{k6a['abweichung']*100:+.2f} %** | "
             f"{'ja' if k6a['im_toleranzband'] else 'NEIN'} |")
    z.append(f"| K6 dezentrale WP | V15 | **{k6b['abweichung']*100:+.2f} %** | "
             f"{'ja' if k6b['im_toleranzband'] else 'NEIN'} |")
    k7 = next(x for x in d["V15"]["ergebnis"] if x["komposition"] == "K7")
    z.append(f"| K7 Gaskessel | V15 | **{k7['abweichung']*100:+.2f} %** | "
             f"{'ja' if k7['im_toleranzband'] else 'NEIN'} |")

    z.append(f"\n\n## V12 — K1 gegen {v12['quelle']}\n")
    z.append(f"Fundstelle: {v12['fundstelle']} · Systemgrenze: {v12['systemgrenze']} · "
             f"Preisbasis: {v12['preisbasis']}\n")
    z.append("| Vollbenutzungs-<br>stunden | Strombezug | Modell bei CAPEX<br>700 / 1.150 / 1.600 | "
             "Modellspanne | Band der Quelle | Speicher-<br>bedarf | trifft |")
    z.append("| [h/a] | [EUR/MWh] | [EUR/MWh] | [EUR/MWh] | [EUR/MWh] | [kWh/kW] | |")
    z.append("|---:|---:|---|---|---|---:|---|")
    for x in v12["zeilen"]:
        w = " / ".join(f"{v:.0f}" for v in x["modell"].values())
        z.append(f"| {x['vollbenutzungsstunden']} | {x['strompreis']:.0f} | {w} | "
                 f"{x['modellspanne'][0]:.0f}–{x['modellspanne'][1]:.0f} | "
                 f"{x['quelle_band'][0]:.0f}–{x['quelle_band'][1]:.0f} | "
                 f"{x['speicherbedarf_kwh_pro_kw']} | "
                 f"{'ja' if x['trifft'] else 'nein'} |")
    z.append(f"\n**Befund.** {v12['befund']}\n")

    z.append("\n## V13 — K2 im Verhältnistest gegen K1\n")
    z.append(f"Fundstelle: {vr['fundstelle']} · {vr['systemgrenze']}\n")
    z.append(f"Zielverhältnis der Quelle: **{vr['ziel_verhaeltnis']:.4f}** "
             f"(7,9 zu 10,3 ct/kWh)\n")
    z.append("| Strombezug | LCOH WP | LCOH Biomasse | Verhältnis | Abweichung |")
    z.append("| [EUR/MWh] | [EUR/MWh] | [EUR/MWh] | [—] | [%] |")
    z.append("|---:|---:|---:|---:|---:|")
    for x in vr["zeilen"]:
        z.append(f"| {x['strompreis']:.0f} | {x['lcoh_wp']:.2f} | {x['lcoh_bio']:.2f} | "
                 f"{x['verhaeltnis']:.4f} | **{x['abweichung']*100:+.2f}** |")
    z.append(f"\n**Befund.** {vr['befund']}\n")

    z.append("\n## V13 — K6 dezentrale Wärmepumpe\n")
    e = k6a["eingang"]
    z.append(f"Fundstelle: {k6a['fundstelle']} · Preisbasis: {k6a['preisbasis']}\n")
    z.append(f"Eingang: Investition {e['investition_eur']:,.0f} EUR bei "
             f"{e['leistung_kw']:.0f} kW = {e['capex_eur_pro_kw']:.0f} EUR/kW · "
             f"JAZ {e['jaz']} · {e['vollbenutzungsstunden']:.0f} h/a · "
             f"Strombezug {e['strompreis_eur_pro_mwh']:.0f} EUR/MWh · "
             f"Zins {e['zins']:.4f} · Förderquote {e['foerderquote']:.0%}\n"
             .replace(",", "."))
    z.append("| | Wert | Einheit |")
    z.append("|---|---:|---|")
    z.append(f"| Zielwert der Quelle | {k6a['zielwert']:.2f} | EUR/MWh |")
    z.append(f"| Modell | **{k6a['modell']:.2f}** | EUR/MWh |")
    z.append(f"| Abweichung | **{k6a['abweichung']*100:+.2f}** | % |")

    z.append("\n\n## V14 — K5 Biomasse plus Netz\n")
    z.append(f"Fundstelle: {v14['fundstelle']}\n")
    z.append(f"**Preisbasis:** {v14['preisbasis']}\n")
    e = v14["eingang"]
    z.append(f"Eingang: {e['waermemenge_mwh_a']:.2f} MWh/a · {e['trassenlaenge_m']:.0f} m "
             f"Trasse · {e['anschluesse']} Anschlüsse = {e['mwh_je_anschluss']:.1f} MWh/a "
             f"je Anschluss · Q_l {e['waermeliniendichte']:.3f} MWh/(m·a) · "
             f"Verluste {e['verlustanteil']:.1%} · Zins {e['zins']:.1%}\n")
    z.append(f"Zielwert: **{v14['zielwert']:.1f} EUR/MWh netto**\n")
    z.append("| Hausanschluss | Herkunft | spezifisch | Trassenkosten | Modell | Abweichung |")
    z.append("| [EUR/Anschluss] | | [EUR/(MWh·a)] | [EUR/m] | [EUR/MWh] | [%] |")
    z.append("|---:|---|---:|---:|---:|---:|")
    for x in v14["zeilen"]:
        z.append(f"| {x['hausanschluss_eur_je_anschluss']:.0f} | "
                 f"{x['hausanschluss_herkunft']} | "
                 f"{x['hausanschluss_eur_pro_mwh_a']:.1f} | {x['netz_invest']:.0f} | "
                 f"{x['modell']:.2f} | **{x['abweichung']*100:+.2f}** |")
    z.append(f"\n**Befund.** {v14['befund']}\n")

    v15 = d["V15"]
    z.append(f"\n## V15 — K6 und K7 gegen {v15['quelle']}\n")
    z.append(f"**Preisbasis:** {v15['preisbasis']}\n")
    z.append(f"\n**K6** — Zielwert {k6b['zielwert']:.2f} EUR/MWh, Modell "
             f"**{k6b['modell']:.2f}**, Abweichung **{k6b['abweichung']*100:+.2f} %**\n")
    z.append(f"*{k6b['hinweis']}*\n")
    z.append(f"\n**K7** — Zielwert {k7['zielwert']:.2f} EUR/MWh, Modell "
             f"**{k7['modell']:.2f}**, Abweichung **{k7['abweichung']*100:+.2f} %**\n")
    z.append(f"\n*{k7['hinweis']}*\n")

    z.append("\n## K3 und K4 — analytisch geschlossen\n")
    z.append("| Komposition | Modellwert im Basisfall | Begründung |")
    z.append("|---|---:|---|")
    for k, v in ag.items():
        z.append(f"| {k} | {v['wert']:.2f} EUR/MWh | {v['begruendung']} |")
    return "\n".join(z) + "\n"


if __name__ == "__main__":
    d = lauf()
    ziel = Path(_lauf.reports("E20_projektvalidierung"))
    ziel.mkdir(parents=True, exist_ok=True)
    (ziel / "e20.json").write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    txt = bericht(d)
    (ziel / "e20.md").write_text(txt, encoding="utf-8")
    print(f"Geschrieben: {ziel}/e20.json und .md")
