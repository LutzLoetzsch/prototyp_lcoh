from __future__ import annotations

from dss.fachmodell.enums import Brennstoffart, Groessenklasse
from dss.fachmodell.erzeugervariante import Biomassefeuerung


def heizwerk_fuer_bedarf(q0_mwh: float, volllaststunden: float,
                         capex_eur_pro_kw: float, wartungssatz: float,
                         nutzungsgrad: float, lebensdauer: int) -> Biomassefeuerung:
    leistung_kw = q0_mwh * 1000.0 / volllaststunden
    return Biomassefeuerung(
        leistung=leistung_kw,
        lebensdauer=lebensdauer,
        investitionskosten=capex_eur_pro_kw,
        betriebskostenFix=wartungssatz * capex_eur_pro_kw,
        groessenklasse=Groessenklasse.NETZGEBUNDEN,
        wirkungsgrad=nutzungsgrad,
        brennstoff=Brennstoffart.HOLZHACKSCHNITZEL,
    )
