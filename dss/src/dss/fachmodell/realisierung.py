from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Realisierung:

    wacc: float
    volllaststunden: float
    energiepreis_eur_pro_mwh: float
    foerderquote: float = 0.0
    emissionsfaktor_t_pro_mwh: float = 0.0
    co2_preis_eur_pro_t: float = 0.0
    preisaenderung_invest: float = 1.0
