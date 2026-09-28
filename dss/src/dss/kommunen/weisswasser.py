from __future__ import annotations

from dss.fachmodell.bedarf import Bedarfstrajektorie, Segment
from dss.fachmodell.realisierung import Realisierung
from dss.kommunen._gemeinsam import heizwerk_fuer_bedarf

NAME = "Weisswasser (Lausitz, Strukturwandel)"
BETRACHTUNGSZEITRAUM = 20
_ANSCHLUSSJAHR = 4
_INDUSTRIE_BESTAND = 600.0
_INDUSTRIE_NEU = 6500.0
_INDUSTRIE_WACHSTUM = 0.01


def _industrie_reihe() -> list[float]:
    reihe = []
    for jahr in range(1, BETRACHTUNGSZEITRAUM + 1):
        if jahr < _ANSCHLUSSJAHR:
            reihe.append(_INDUSTRIE_BESTAND)
        else:
            reihe.append(_INDUSTRIE_NEU * (1.0 + _INDUSTRIE_WACHSTUM) ** (jahr - _ANSCHLUSSJAHR))
    return reihe


trajektorie = Bedarfstrajektorie(
    T=BETRACHTUNGSZEITRAUM,
    segmente=(
        Segment.geometrisch("Haushalt", 9000.0, rate=-0.012, T=BETRACHTUNGSZEITRAUM),
        Segment.aus_reihe("Industrie-Neuansiedlung", _industrie_reihe()),
    ),
)

erzeuger = heizwerk_fuer_bedarf(
    q0_mwh=trajektorie.q0(), volllaststunden=2500.0,
    capex_eur_pro_kw=550.0, wartungssatz=0.03,
    nutzungsgrad=0.88, lebensdauer=BETRACHTUNGSZEITRAUM,
)

realisierung = Realisierung(
    wacc=0.045, volllaststunden=2500.0,
    energiepreis_eur_pro_mwh=32.5, foerderquote=0.40,
)


def lcoh() -> float:
    return erzeuger.waermegestehungskosten(realisierung, trajektorie)


def lcoh_statisch() -> float:
    return erzeuger.waermegestehungskosten(realisierung)
