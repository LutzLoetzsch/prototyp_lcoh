from __future__ import annotations

from dss.fachmodell.bedarf import Bedarfstrajektorie, Segment
from dss.fachmodell.enums import Groessenklasse, Waermequelle
from dss.fachmodell.erzeugervariante import Waermepumpe
from dss.fachmodell.realisierung import Realisierung
from dss.fachmodell.versorgung import (
    Rolle, Versorgungsanteil, Versorgungsoption, Versorgungsszenario,
)
from dss.szenarien.m6 import EMIS_STROM, M6_BASIS, Q0_MWH, _trajektorie_aus_params

CAPEX_DEZ, JAZ_DEZ, VLH_DEZ, LD_DEZ = 1700.0, 3.0, 2000.0, 20
WARTUNG_DEZ = 0.030
FOERDER_DEZ = 0.30
AUFSCHLAG_HAUSHALT = 150.0  # EUR/MWh
T_B = 25


def lcoh_dez(p: dict) -> float:
    p = {**M6_BASIS, **p}
    strompreis_dez = p["strompreis"] + AUFSCHLAG_HAUSHALT
    _tb = len(p["bedarfsreihe"]) if p.get("bedarfsreihe") else int(round(p["betrachtungszeitraum"]))
    traj = _trajektorie_aus_params(p, _tb)
    wp = Versorgungsoption(
        Waermepumpe(
            leistung=Q0_MWH * 1000.0 / VLH_DEZ, lebensdauer=LD_DEZ,
            investitionskosten=CAPEX_DEZ, betriebskostenFix=WARTUNG_DEZ * CAPEX_DEZ,
            groessenklasse=Groessenklasse.DEZENTRAL, jahresarbeitszahl=JAZ_DEZ,
            waermequelle=Waermequelle.LUFT, quellentemperatur=5.0,
        ),
        Realisierung(
            wacc=p["wacc"], volllaststunden=VLH_DEZ, energiepreis_eur_pro_mwh=strompreis_dez,
            foerderquote=FOERDER_DEZ, emissionsfaktor_t_pro_mwh=EMIS_STROM,
            co2_preis_eur_pro_t=p["co2_preis"],
        ),
    )
    szen = Versorgungsszenario(
        (Versorgungsanteil(wp, 1.0, rolle=Rolle.GRUNDLAST),), netz=None)
    return szen.waermegestehungskosten(traj)
