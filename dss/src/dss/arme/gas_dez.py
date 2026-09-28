from __future__ import annotations

from dss.fachmodell.enums import Brennstoffart, Groessenklasse
from dss.fachmodell.erzeugervariante import Gasfeuerung
from dss.fachmodell.realisierung import Realisierung
from dss.fachmodell.versorgung import Versorgungsoption
from dss.szenarien.m6 import Q0_MWH
from dss.arme.komposition import baue_trajektorie, voll

GAS_DEZ_LEBENSDAUER = 20
EMIS_GAS = 0.240  # t CO2/MWh

GAS_DEZ_DEFAULTS = {
    "capex_gas_dez": 245.0,
    "capex_gas_dez_band": (165.0, 354.0),
    "wirkungsgrad_gas_dez": 0.994,
    "wartung_gas_dez": 7.0 / 245.0,
    "vlh_gas_dez": 1800.0,
    "gaspreis": 80.0,
}


def baue_gas_dez(p: dict) -> Versorgungsoption:
    p = {**GAS_DEZ_DEFAULTS, **voll(p)}
    return Versorgungsoption(
        Gasfeuerung(
            leistung=Q0_MWH * 1000.0 / p["vlh_gas_dez"],
            lebensdauer=GAS_DEZ_LEBENSDAUER,
            investitionskosten=p["capex_gas_dez"],
            betriebskostenFix=p["wartung_gas_dez"] * p["capex_gas_dez"],
            groessenklasse=Groessenklasse.DEZENTRAL,
            wirkungsgrad=p["wirkungsgrad_gas_dez"],
            brennstoff=Brennstoffart.ERDGAS,
        ),
        Realisierung(
            wacc=p["wacc"],
            volllaststunden=p["vlh_gas_dez"],
            energiepreis_eur_pro_mwh=p["gaspreis"],
            foerderquote=p["foerderquote"],
            emissionsfaktor_t_pro_mwh=EMIS_GAS,
            co2_preis_eur_pro_t=p["co2_preis"],
        ),
    )


def lcoh_gas_dez(p: dict) -> float:
    p = {**GAS_DEZ_DEFAULTS, **voll(p)}
    return baue_gas_dez(p).waermegestehungskosten(baue_trajektorie(p))
