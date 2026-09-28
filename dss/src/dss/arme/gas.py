from __future__ import annotations

from dss.fachmodell.enums import Brennstoffart, Groessenklasse
from dss.fachmodell.erzeugervariante import Gasfeuerung
from dss.fachmodell.realisierung import Realisierung
from dss.fachmodell.versorgung import Versorgungsoption
from dss.szenarien.m6 import Q0_MWH
from dss.arme.komposition import baue_trajektorie, voll

GAS_LEBENSDAUER = 25       # a
EMIS_GAS = 0.240           # t CO2/MWh

GAS_DEFAULTS = {
    "capex_gas": 110.0,        # EUR/kW
    "wirkungsgrad_gas": 0.99,
    "wartung_gas": 0.018,
    "vlh_gas": 1000.0,
    "gaspreis": 80.0,          # EUR/MWh
}


def baue_gas(p: dict) -> Versorgungsoption:
    p = {**GAS_DEFAULTS, **voll(p)}
    return Versorgungsoption(
        Gasfeuerung(
            leistung=Q0_MWH * 1000.0 / p["vlh_gas"],
            lebensdauer=GAS_LEBENSDAUER,
            investitionskosten=p["capex_gas"],
            betriebskostenFix=p["wartung_gas"] * p["capex_gas"],
            groessenklasse=Groessenklasse.NETZGEBUNDEN,
            wirkungsgrad=p["wirkungsgrad_gas"],
            brennstoff=Brennstoffart.ERDGAS,
        ),
        Realisierung(
            wacc=p["wacc"],
            volllaststunden=p["vlh_gas"],
            energiepreis_eur_pro_mwh=p["gaspreis"],
            foerderquote=p["foerderquote"],
            emissionsfaktor_t_pro_mwh=EMIS_GAS,
            co2_preis_eur_pro_t=p["co2_preis"],
        ),
    )


def lcoh_gas(p: dict) -> float:
    p = {**GAS_DEFAULTS, **voll(p)}
    return baue_gas(p).waermegestehungskosten(baue_trajektorie(p))
