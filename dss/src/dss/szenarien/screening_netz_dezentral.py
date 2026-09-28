from __future__ import annotations

import numpy as np

from dss.fachmodell.bedarf import Bedarfstrajektorie, Segment
from dss.fachmodell.enums import (
    Brennstoffart,
    Groessenklasse,
    Netztyp,
    Waermequelle,
)
from dss.fachmodell.erzeugervariante import Biomassefeuerung, Waermepumpe
from dss.fachmodell.realisierung import Realisierung
from dss.fachmodell.versorgung import (
    Netz,
    Rolle,
    Versorgungsanteil,
    Versorgungsoption,
    Versorgungsszenario,
)

WACC = 0.045
T_B = 25
BEDARFSRATE = -0.005
CO2_PREIS = 100.0
Q0_MWH = 8000.0
STROMPREIS = 200.0
BRENNSTOFFPREIS = 32.5
EMIS_STROM = 0.260
EMIS_HOLZ = 0.020

WP_Z_CAPEX, WP_Z_JAZ, WP_Z_VLH, WP_Z_WARTUNG, WP_Z_LD = 978.0, 3.0, 4000.0, 0.025, 25
BIO_CAPEX, BIO_ETA, BIO_VLH, BIO_WARTUNG, BIO_LD = 692.0, 0.90, 1500.0, 0.0075, 20
GRUNDLAST = 0.70

NETZ_C = 811.0  # EUR/m
NETZ_VERLUST = 0.16
NETZ_LD = 40
NETZ_BETRIEB = 0.01
HAUSANSCHLUSS = 400.0  # EUR/(MWh/a)
HAUS_LD = 20

WP_D_CAPEX, WP_D_JAZ, WP_D_VLH, WP_D_WARTUNG, WP_D_LD = 1700.0, 3.0, 2000.0, 0.019, 20

FOERDER_BEW = 0.40
FOERDER_KFW = 0.30


def _trajektorie() -> Bedarfstrajektorie:
    return Bedarfstrajektorie(
        T=T_B,
        segmente=(Segment.geometrisch("bedarf", Q0_MWH, BEDARFSRATE, T=T_B),),
    )


def lcoh_zentral(waermeliniendichte: float, foerderung: bool = True) -> float:
    f = FOERDER_BEW if foerderung else 0.0
    wp = Versorgungsoption(
        Waermepumpe(
            leistung=Q0_MWH * 1000.0 / WP_Z_VLH, lebensdauer=WP_Z_LD,
            investitionskosten=WP_Z_CAPEX, betriebskostenFix=WP_Z_WARTUNG * WP_Z_CAPEX,
            groessenklasse=Groessenklasse.NETZGEBUNDEN, jahresarbeitszahl=WP_Z_JAZ,
            waermequelle=Waermequelle.GRUBENWASSER, quellentemperatur=26.0,
        ),
        Realisierung(
            wacc=WACC, volllaststunden=WP_Z_VLH, energiepreis_eur_pro_mwh=STROMPREIS,
            foerderquote=f, emissionsfaktor_t_pro_mwh=EMIS_STROM, co2_preis_eur_pro_t=CO2_PREIS,
        ),
    )
    bio = Versorgungsoption(
        Biomassefeuerung(
            leistung=Q0_MWH * 1000.0 / BIO_VLH, lebensdauer=BIO_LD,
            investitionskosten=BIO_CAPEX, betriebskostenFix=BIO_WARTUNG * BIO_CAPEX,
            groessenklasse=Groessenklasse.NETZGEBUNDEN, wirkungsgrad=BIO_ETA,
            brennstoff=Brennstoffart.HOLZHACKSCHNITZEL,
        ),
        Realisierung(
            wacc=WACC, volllaststunden=BIO_VLH, energiepreis_eur_pro_mwh=BRENNSTOFFPREIS,
            foerderquote=f, emissionsfaktor_t_pro_mwh=EMIS_HOLZ, co2_preis_eur_pro_t=CO2_PREIS,
        ),
    )
    netz = Netz(
        netztyp=Netztyp.NAHWAERME, investition_eur_pro_m=NETZ_C,
        waermeliniendichte_mwh_pro_m=waermeliniendichte, lebensdauer=NETZ_LD,
        betriebskostenanteil=NETZ_BETRIEB, verlustanteil=NETZ_VERLUST,
        foerderquote=f, hausanschluss_eur_pro_mwh_a=HAUSANSCHLUSS,
        hausanschluss_lebensdauer=HAUS_LD,
    )
    szen = Versorgungsszenario(
        (
            Versorgungsanteil(wp, GRUNDLAST, rolle=Rolle.GRUNDLAST),
            Versorgungsanteil(bio, 1.0 - GRUNDLAST, rolle=Rolle.SPITZENLAST),
        ),
        netz=netz,
    )
    return szen.waermegestehungskosten(_trajektorie())


def lcoh_dezentral(foerderung: bool = True) -> float:
    f = FOERDER_KFW if foerderung else 0.0
    wp = Versorgungsoption(
        Waermepumpe(
            leistung=Q0_MWH * 1000.0 / WP_D_VLH, lebensdauer=WP_D_LD,
            investitionskosten=WP_D_CAPEX, betriebskostenFix=WP_D_WARTUNG * WP_D_CAPEX,
            groessenklasse=Groessenklasse.DEZENTRAL, jahresarbeitszahl=WP_D_JAZ,
            waermequelle=Waermequelle.LUFT, quellentemperatur=5.0,
        ),
        Realisierung(
            wacc=WACC, volllaststunden=WP_D_VLH, energiepreis_eur_pro_mwh=STROMPREIS,
            foerderquote=f, emissionsfaktor_t_pro_mwh=EMIS_STROM, co2_preis_eur_pro_t=CO2_PREIS,
        ),
    )
    szen = Versorgungsszenario(
        (Versorgungsanteil(wp, 1.0, rolle=Rolle.GRUNDLAST),),
        netz=None,
    )
    return szen.waermegestehungskosten(_trajektorie())


def kurve(q_min: float = 0.5, q_max: float = 4.0, punkte: int = 120,
          foerderung: bool = True) -> tuple[np.ndarray, np.ndarray, float]:
    qs = np.linspace(q_min, q_max, punkte)
    zentral = np.array([lcoh_zentral(q, foerderung) for q in qs])
    dezentral = lcoh_dezentral(foerderung)
    return qs, zentral, dezentral


def schwelle(foerderung: bool = True) -> float | None:
    qs, zentral, dezentral = kurve(foerderung=foerderung)
    diff = zentral - dezentral
    vz = np.where(np.diff(np.sign(diff)))[0]
    if len(vz) == 0:
        return None
    i = vz[0]
    return float(qs[i] - diff[i] * (qs[i + 1] - qs[i]) / (diff[i + 1] - diff[i]))
