from __future__ import annotations

from dss.fachmodell.enums import Groessenklasse, Waermequelle
from dss.fachmodell.erzeugervariante import Waermepumpe
from dss.fachmodell.realisierung import Realisierung
from dss.fachmodell.versorgung import Versorgungsoption
from dss.szenarien.m6 import EMIS_STROM, Q0_MWH, WP_LEBENSDAUER

from dss.arme.komposition import baue_trajektorie, voll


def baue_wp(p: dict) -> Versorgungsoption:
    p = voll(p)
    return Versorgungsoption(
        Waermepumpe(
            leistung=Q0_MWH * 1000.0 / p["vlh_wp"],
            lebensdauer=WP_LEBENSDAUER,
            investitionskosten=p["capex_wp"],
            betriebskostenFix=p["wartung_wp"] * p["capex_wp"],
            groessenklasse=Groessenklasse.NETZGEBUNDEN,
            jahresarbeitszahl=p["jaz"],
            waermequelle=Waermequelle.GRUBENWASSER,
            quellentemperatur=26.0,
        ),
        Realisierung(
            wacc=p["wacc"],
            volllaststunden=p["vlh_wp"],
            energiepreis_eur_pro_mwh=p["strompreis"],
            foerderquote=p["foerderquote"],
            emissionsfaktor_t_pro_mwh=EMIS_STROM,
            co2_preis_eur_pro_t=p["co2_preis"],
        ),
    )


def lcoh_wp(p: dict) -> float:
    p = voll(p)
    return baue_wp(p).waermegestehungskosten(baue_trajektorie(p))
