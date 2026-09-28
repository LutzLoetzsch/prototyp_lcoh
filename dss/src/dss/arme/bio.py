from __future__ import annotations

from dss.fachmodell.enums import Brennstoffart, Groessenklasse
from dss.fachmodell.erzeugervariante import Biomassefeuerung
from dss.fachmodell.realisierung import Realisierung
from dss.fachmodell.versorgung import Versorgungsoption
from dss.szenarien.m6 import BIO_LEBENSDAUER, EMIS_HOLZ, Q0_MWH

from dss.arme.komposition import baue_trajektorie, voll


def baue_bio(p: dict) -> Versorgungsoption:
    p = voll(p)
    return Versorgungsoption(
        Biomassefeuerung(
            leistung=Q0_MWH * 1000.0 / p["vlh_bio"],
            lebensdauer=BIO_LEBENSDAUER,
            investitionskosten=p["capex_bio"],
            betriebskostenFix=p["wartung_bio"] * p["capex_bio"],
            groessenklasse=Groessenklasse.NETZGEBUNDEN,
            wirkungsgrad=p["nutzungsgrad"],
            brennstoff=Brennstoffart.HOLZHACKSCHNITZEL,
        ),
        Realisierung(
            wacc=p["wacc"],
            volllaststunden=p["vlh_bio"],
            energiepreis_eur_pro_mwh=p["brennstoffpreis"],
            foerderquote=p["foerderquote"],
            emissionsfaktor_t_pro_mwh=EMIS_HOLZ,
            co2_preis_eur_pro_t=p["co2_preis"],
        ),
    )


def lcoh_bio(p: dict) -> float:
    p = voll(p)
    return baue_bio(p).waermegestehungskosten(baue_trajektorie(p))
