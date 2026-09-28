from __future__ import annotations

import numpy as np
import pandas as pd

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
from dss.sampling.lhs import lhs_stichprobe
from dss.sampling.zufall import zufalls_stichprobe

Q0_MWH = 8000.0
WP_LEBENSDAUER = 25
BIO_LEBENSDAUER = 20
EMIS_STROM = 0.260      # t CO2/MWh
EMIS_HOLZ = 0.020       # t CO2/MWh

M6_BAENDER: dict[str, tuple[float, float]] = {
    "wacc": (0.030, 0.060),
    "foerderquote": (0.00, 0.40),
    "bedarfsrate": (-0.020, 0.020),
    "grundlast_anteil": (0.50, 0.85),
    "jaz": (2.6, 3.4),
    "capex_wp": (719.0, 1243.0),
    "strompreis": (50.0, 120.0),
    "vlh_wp": (3500.0, 4500.0),
    "nutzungsgrad": (0.82, 0.92),
    "capex_bio": (820.0, 1070.0),
    "brennstoffpreis": (25.0, 45.0),
    "vlh_bio": (1200.0, 1800.0),
    "waermeliniendichte": (0.8, 3.0),
    "netz_invest": (692.0, 2459.0),
    "verlustanteil": (0.140, 0.163),
    "netz_foerderquote": (0.00, 0.40),
}

M6_BASIS: dict[str, float] = {
    "wacc": 0.045,
    "foerderquote": 0.0,
    "bedarfsrate": -0.005,
    "co2_preis": 100.0,
    "grundlast_anteil": 0.70,
    "jaz": 3.0,
    "capex_wp": 978.0,
    "strompreis": 85.0,
    "vlh_wp": 4000.0,
    "nutzungsgrad": 0.88,
    "capex_bio": 945.0,
    "brennstoffpreis": 32.5,
    "vlh_bio": 1500.0,
    "waermeliniendichte": 2.0,
    "netz_invest": 1367.0,
    "verlustanteil": 0.163,
    "betrachtungszeitraum": 25.0,
    "netz_lebensdauer": 40.0,
    "netz_betriebskostenanteil": 0.002,
    "wartung_wp": 0.025,
    "wartung_bio": 0.014,
    "netz_foerderquote": 0.0,
    "hausanschluss": 400.0,
    "hausanschluss_lebensdauer": 20.0,
}

CO2_SZENARIEN: dict[str, float] = {
    "null":     0.0,
    "bestand":  45.0,
    "mittel":  100.0,
    "hoch":    200.0,
}

SWEEP_BEREICHE: dict[str, tuple[float, float]] = {
    **M6_BAENDER,
    "co2_preis": (min(CO2_SZENARIEN.values()), max(CO2_SZENARIEN.values())),
    "betrachtungszeitraum": (15.0, 45.0),
    "netz_lebensdauer": (25.0, 50.0),
    "netz_foerderquote": (0.0, 0.40),
    "hausanschluss": (0.0, 400.0),
}


def _trajektorie_aus_params(p: dict, T: int) -> Bedarfstrajektorie:
    reihe = p.get("bedarfsreihe")
    if reihe:
        return Bedarfstrajektorie(T=len(reihe),
                                  segmente=(Segment.aus_reihe("bedarf", reihe),))
    return Bedarfstrajektorie(T=T,
                              segmente=(Segment.geometrisch("bedarf", Q0_MWH, p["bedarfsrate"], T=T),))


def lcoh_m6(p: dict) -> float:
    basis = dict(M6_BASIS)
    basis.update(p)
    p = basis

    t_b = len(p["bedarfsreihe"]) if p.get("bedarfsreihe") else int(round(p["betrachtungszeitraum"]))
    trajektorie = _trajektorie_aus_params(p, t_b)

    wp = Versorgungsoption(
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
    bio = Versorgungsoption(
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
    netz = Netz(
        netztyp=Netztyp.NAHWAERME,
        investition_eur_pro_m=p["netz_invest"],
        waermeliniendichte_mwh_pro_m=p["waermeliniendichte"],
        lebensdauer=int(round(p["netz_lebensdauer"])),
        betriebskostenanteil=p["netz_betriebskostenanteil"],
        verlustanteil=p["verlustanteil"],
        foerderquote=p["netz_foerderquote"],
        hausanschluss_eur_pro_mwh_a=p["hausanschluss"],
        hausanschluss_lebensdauer=int(round(p["hausanschluss_lebensdauer"])),
    )
    s = p["grundlast_anteil"]
    szenario = Versorgungsszenario(
        (
            Versorgungsanteil(wp, s, rolle=Rolle.GRUNDLAST),
            Versorgungsanteil(bio, 1.0 - s, rolle=Rolle.SPITZENLAST),
        ),
        netz=netz,
    )
    return szenario.waermegestehungskosten(trajektorie)


def lhs_ensemble(n: int = 2000, seed: int = 42,
                 verfahren: str = "lhs") -> pd.DataFrame:
    sampler = zufalls_stichprobe if verfahren == "zufall" else lhs_stichprobe
    proben = sampler(M6_BAENDER, n=n, seed=seed)
    df = pd.DataFrame(proben)
    df["lcoh"] = [lcoh_m6(zeile) for zeile in df.to_dict("records")]
    return df


def parameter_sweep(param: str, punkte: int = 120) -> tuple[np.ndarray, np.ndarray]:
    untere, obere = SWEEP_BEREICHE[param]
    xs = np.linspace(untere, obere, punkte)
    ys = np.empty_like(xs)
    for i, x in enumerate(xs):
        p = dict(M6_BASIS)
        p[param] = float(x)
        ys[i] = lcoh_m6(p)
    return xs, ys
