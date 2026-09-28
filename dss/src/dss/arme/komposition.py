from __future__ import annotations

from dss.fachmodell.bedarf import Bedarfstrajektorie, Segment
from dss.fachmodell.enums import Netztyp
from dss.fachmodell.versorgung import Netz
from dss.szenarien.m6 import M6_BASIS, Q0_MWH


def voll(p: dict) -> dict:
    return {**M6_BASIS, **p}


def baue_trajektorie(p: dict) -> Bedarfstrajektorie:
    p = voll(p)
    t_b = int(round(p["betrachtungszeitraum"]))
    return Bedarfstrajektorie(
        T=t_b,
        segmente=(Segment.geometrisch("bedarf", Q0_MWH, p["bedarfsrate"], T=t_b),),
    )


def baue_netz(p: dict) -> Netz:
    p = voll(p)
    return Netz(
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


def kompositionsfaktoren(p: dict) -> tuple[float, float, float]:
    p = voll(p)
    from dss.arme.wp import baue_wp
    leitend = baue_wp(p).realisierung
    netz = baue_netz(p)
    trajektorie = baue_trajektorie(p)
    c_d = netz.spezifische_kosten(
        leitend.wacc, trajektorie, leitend.preisaenderung_invest)
    return p["grundlast_anteil"], netz.verlustfaktor, c_d


def komponiere(lcoh_wp_wert: float, lcoh_bio_wert: float, p: dict) -> float:
    s, verlustfaktor, c_d = kompositionsfaktoren(p)
    erzeugung = s * lcoh_wp_wert + (1.0 - s) * lcoh_bio_wert
    return erzeugung * verlustfaktor + c_d


def lcoh_komponiert(p: dict) -> float:
    p = voll(p)
    from dss.arme.wp import lcoh_wp
    from dss.arme.bio import lcoh_bio
    return komponiere(lcoh_wp(p), lcoh_bio(p), p)


def komponiere_n(lcoh_arme: list[float], anteile: list[float], p: dict) -> float:
    if abs(sum(anteile) - 1.0) > 1e-9:
        raise ValueError("Anteile müssen auf 1 summieren")
    if len(lcoh_arme) != len(anteile):
        raise ValueError("lcoh_arme und anteile müssen gleich lang sein")
    _s, verlustfaktor, c_d = kompositionsfaktoren(p)
    erzeugung = sum(a * l for a, l in zip(anteile, lcoh_arme))
    return erzeugung * verlustfaktor + c_d
