from __future__ import annotations

import math


def annuitaetsfaktor(wacc: float, lebensdauer_jahre: int) -> float:
    if wacc <= 0:
        raise ValueError("WACC muss > 0 sein")

    if lebensdauer_jahre <= 0:
        raise ValueError("Lebensdauer muss positiv sein")

    q_hoch_n = (1.0 + wacc) ** lebensdauer_jahre
    return wacc * q_hoch_n / (q_hoch_n - 1.0)


def kapitalgebundene_annuitaet(
        investitionsbetrag_eur: float,
        wacc: float,
        lebensdauer_jahre: int,
        foerderquote: float = 0.0,
) -> float:
    if investitionsbetrag_eur < 0:
        raise ValueError("Investitionsbetrag < 0")

    if not (0 <= foerderquote <= 1):
        raise ValueError(f"Ungültige Förderquote: {foerderquote}")

    a = annuitaetsfaktor(wacc, lebensdauer_jahre)
    effektive_investition = investitionsbetrag_eur * (1 - foerderquote)
    return effektive_investition * a


def bedarfsgebundene_annuitaet(
        jahreswaerme_mwh: float,
        effizienz: float,
        energiepreis_eur_pro_mwh: float,
) -> float:
    if jahreswaerme_mwh < 0:
        raise ValueError("Jahreswärme muss >= 0 sein")

    if effizienz <= 0:
        raise ValueError("Effizienz (Nutzungsgrad/JAZ) muss positiv sein")

    if energiepreis_eur_pro_mwh < 0:
        raise ValueError("Ungültiger Energiepreis")

    energieeinsatz = jahreswaerme_mwh / effizienz
    return energieeinsatz * energiepreis_eur_pro_mwh


def betriebsgebundene_annuitaet_fix(
        leistung_kw: float,
        betriebskostenfix_eur_pro_kw_a: float,
) -> float:
    if leistung_kw < 0:
        raise ValueError("Leistung darf nicht negativ sein")

    if betriebskostenfix_eur_pro_kw_a < 0:
        raise ValueError("Betriebskosten dürfen nicht negativ sein")

    return leistung_kw * betriebskostenfix_eur_pro_kw_a


def jahreswaerme(
        nennleistung_kw: float,
        volllaststunden_h_pro_a: float,
) -> float:
    if nennleistung_kw <= 0 or volllaststunden_h_pro_a <= 0:
        raise ValueError("Nennleistung und Volllaststunden müssen positiv sein")

    return nennleistung_kw * volllaststunden_h_pro_a / 1000.0


def diskontierte_summe(jahreswerte, wacc: float) -> float:
    if wacc <= 0:
        raise ValueError("WACC muss > 0 sein")

    barwert = 0.0
    for t, wert in enumerate(jahreswerte, start=1):
        barwert += wert / (1.0 + wacc) ** t
    return barwert


def kapitalbarwert_mit_ersatz(
        investitionsbetrag_eur: float,
        lebensdauer_jahre: int,
        betrachtungszeitraum_jahre: int,
        wacc: float,
        preisaenderungsfaktor: float = 1.0,
) -> float:
    if investitionsbetrag_eur < 0:
        raise ValueError("Investitionsbetrag < 0")

    if lebensdauer_jahre <= 0 or betrachtungszeitraum_jahre <= 0:
        raise ValueError("Lebensdauer und Betrachtungszeitraum müssen positiv sein")

    if wacc <= 0:
        raise ValueError("WACC muss > 0 sein")

    q = 1.0 + wacc
    r = preisaenderungsfaktor
    t_n = lebensdauer_jahre
    t_b = betrachtungszeitraum_jahre

    n_b = math.ceil(t_b / t_n) - 1

    barwert = float(investitionsbetrag_eur)
    for j in range(1, n_b + 1):
        barwert += investitionsbetrag_eur * r ** (j * t_n) / q ** (j * t_n)

    restnutzung = (n_b + 1) * t_n - t_b
    restwert = (
        investitionsbetrag_eur
        * r ** (n_b * t_n)
        * (restnutzung / t_n)
        / q ** t_b
    )

    return barwert - restwert
