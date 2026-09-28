from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from dss.fachmodell.bedarf import Bedarfstrajektorie
from dss.fachmodell.enums import Brennstoffart, Groessenklasse, Waermequelle
from dss.fachmodell.realisierung import Realisierung
from dss.wirtschaftlichkeit.annuitaet import (
    bedarfsgebundene_annuitaet,
    betriebsgebundene_annuitaet_fix,
    diskontierte_summe,
    jahreswaerme,
    kapitalbarwert_mit_ersatz,
    kapitalgebundene_annuitaet,
)


@dataclass
class Erzeugervariante(ABC):
    leistung: float
    lebensdauer: int
    investitionskosten: float
    betriebskostenFix: float
    groessenklasse: Groessenklasse

    @abstractmethod
    def effizienz(self) -> float:
        pass

    def waermegestehungskosten(self, realisierung: Realisierung,
                               trajektorie: Bedarfstrajektorie | None = None) -> float:
        effektiver_energiepreis = (
            realisierung.energiepreis_eur_pro_mwh
            + realisierung.emissionsfaktor_t_pro_mwh * realisierung.co2_preis_eur_pro_t
        )

        if trajektorie is None:
            q_th_mwh = jahreswaerme(self.leistung, realisierung.volllaststunden)
            investitionsbetrag = self.investitionskosten * self.leistung

            an_k = kapitalgebundene_annuitaet(
                investitionsbetrag,
                realisierung.wacc,
                self.lebensdauer,
                realisierung.foerderquote,
            )
            an_v = bedarfsgebundene_annuitaet(
                q_th_mwh,
                self.effizienz(),
                effektiver_energiepreis,
            )
            an_b = betriebsgebundene_annuitaet_fix(
                self.leistung,
                self.betriebskostenFix,
            )

            return (an_k + an_v + an_b) / q_th_mwh

        bedarf = trajektorie.reihe()

        # Auslegung auf den Anfangsbedarf
        leistung = bedarf[0] * 1000.0 / realisierung.volllaststunden
        investition = self.investitionskosten * leistung * (1 - realisierung.foerderquote)
        a_0 = kapitalbarwert_mit_ersatz(
            investition,
            self.lebensdauer,
            len(bedarf),
            realisierung.wacc,
            realisierung.preisaenderung_invest,
        )
        a_b = betriebsgebundene_annuitaet_fix(leistung, self.betriebskostenFix)

        laufende_kosten = [
            bedarfsgebundene_annuitaet(
                q_t, self.effizienz(), effektiver_energiepreis
            ) + a_b
            for q_t in bedarf
        ]

        zaehler = a_0 + diskontierte_summe(laufende_kosten, realisierung.wacc)
        nenner = diskontierte_summe(bedarf, realisierung.wacc)
        return zaehler / nenner


@dataclass
class Biomassefeuerung(Erzeugervariante):
    wirkungsgrad: float
    brennstoff: Brennstoffart

    def effizienz(self) -> float:
        return self.wirkungsgrad


@dataclass
class Gasfeuerung(Erzeugervariante):
    wirkungsgrad: float
    brennstoff: Brennstoffart

    def effizienz(self) -> float:
        return self.wirkungsgrad


@dataclass
class BiomasseKWK(Biomassefeuerung):
    elektrische_leistung: float = 0.0
    elektr_wirkungsgrad: float = 0.0
    stromkennzahl: float = 0.0


@dataclass
class Waermepumpe(Erzeugervariante):
    jahresarbeitszahl: float
    waermequelle: Waermequelle
    quellentemperatur: float

    def effizienz(self) -> float:
        return self.jahresarbeitszahl
