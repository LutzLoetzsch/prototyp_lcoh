from __future__ import annotations

from typing import Optional
from pydantic import BaseModel

_FELDER = [
    "wacc", "foerderquote", "bedarfsrate", "grundlast_anteil", "jaz",
    "capex_wp", "strompreis", "vlh_wp", "nutzungsgrad", "capex_bio",
    "brennstoffpreis", "vlh_bio", "waermeliniendichte", "netz_invest",
    "verlustanteil", "netz_foerderquote",
    "hausanschluss", "betrachtungszeitraum", "co2_preis",
]

_HERLEITUNG = ["trassenlaenge_m", "waermelieferung_mwh_a"]


class Parametersatz(BaseModel):
    model_config = {"extra": "ignore"}

    wacc: Optional[float] = None
    foerderquote: Optional[float] = None
    bedarfsrate: Optional[float] = None
    grundlast_anteil: Optional[float] = None
    jaz: Optional[float] = None
    capex_wp: Optional[float] = None
    strompreis: Optional[float] = None
    vlh_wp: Optional[float] = None
    nutzungsgrad: Optional[float] = None
    capex_bio: Optional[float] = None
    brennstoffpreis: Optional[float] = None
    vlh_bio: Optional[float] = None
    waermeliniendichte: Optional[float] = None
    netz_invest: Optional[float] = None
    verlustanteil: Optional[float] = None
    netz_foerderquote: Optional[float] = None

    hausanschluss: Optional[float] = None
    betrachtungszeitraum: Optional[float] = None
    co2_preis: Optional[float] = None

    trassenlaenge_m: Optional[float] = None
    waermelieferung_mwh_a: Optional[float] = None

    def als_eingabe(self) -> dict:
        return {k: v for k, v in self.model_dump().items() if v is not None}
