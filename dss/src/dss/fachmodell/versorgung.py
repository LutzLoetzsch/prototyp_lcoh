from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dss.fachmodell.bedarf import Bedarfstrajektorie
from dss.fachmodell.enums import Netztyp
from dss.fachmodell.erzeugervariante import Erzeugervariante
from dss.fachmodell.realisierung import Realisierung
from dss.wirtschaftlichkeit.annuitaet import (
    annuitaetsfaktor,
    diskontierte_summe,
    kapitalbarwert_mit_ersatz,
)


class Rolle(Enum):
    GRUNDLAST = "Grundlast"
    SPITZENLAST = "Spitzenlast"
    ERGAENZUNG = "Ergaenzung"


@dataclass(frozen=True)
class Versorgungsoption:
    erzeuger: Erzeugervariante
    realisierung: Realisierung

    def waermegestehungskosten(self, trajektorie: Bedarfstrajektorie | None = None) -> float:
        return self.erzeuger.waermegestehungskosten(self.realisierung, trajektorie)


@dataclass(frozen=True)
class Versorgungsanteil:
    option: Versorgungsoption
    deckungsanteil: float
    rolle: Rolle = Rolle.GRUNDLAST
    anzahl: int = 1

    def __post_init__(self):
        if not (0.0 < self.deckungsanteil <= 1.0):
            raise ValueError(f"Deckungsanteil muss in (0, 1] liegen: {self.deckungsanteil}")
        if self.anzahl < 1:
            raise ValueError(f"Anzahl muss >= 1 sein: {self.anzahl}")


@dataclass(frozen=True)
class Netz:
    netztyp: Netztyp
    investition_eur_pro_m: float
    waermeliniendichte_mwh_pro_m: float
    lebensdauer: int = 40
    betriebskostenanteil: float = 0.01
    verlustanteil: float = 0.0
    foerderquote: float = 0.0
    hausanschluss_eur_pro_mwh_a: float = 0.0
    hausanschluss_lebensdauer: int = 20

    def __post_init__(self):
        if self.investition_eur_pro_m < 0:
            raise ValueError("Investition je Meter < 0")
        if self.waermeliniendichte_mwh_pro_m <= 0:
            raise ValueError("Waermeliniendichte muss > 0 sein")
        if not (0.0 <= self.verlustanteil < 1.0):
            raise ValueError(f"Verlustanteil muss in [0, 1) liegen: {self.verlustanteil}")
        if not (0.0 <= self.foerderquote < 1.0):
            raise ValueError(f"Foerderquote muss in [0, 1) liegen: {self.foerderquote}")
        if self.hausanschluss_eur_pro_mwh_a < 0:
            raise ValueError("Hausanschlusskosten < 0")
        if self.hausanschluss_lebensdauer <= 0:
            raise ValueError("Hausanschluss-Lebensdauer muss > 0 sein")

    @classmethod
    def mit_anschlussgrad(
            cls,
            netztyp: Netztyp,
            investition_eur_pro_m: float,
            potenzial_waermeliniendichte: float,
            anschlussgrad: float,
            **kwargs,
    ) -> "Netz":
        if not (0.0 < anschlussgrad <= 1.0):
            raise ValueError(f"Anschlussgrad muss in (0, 1] liegen: {anschlussgrad}")
        return cls(
            netztyp=netztyp,
            investition_eur_pro_m=investition_eur_pro_m,
            waermeliniendichte_mwh_pro_m=anschlussgrad * potenzial_waermeliniendichte,
            **kwargs,
        )

    @property
    def verlustfaktor(self) -> float:
        return 1.0 / (1.0 - self.verlustanteil)

    def spezifische_kosten(
            self,
            wacc: float,
            trajektorie: Bedarfstrajektorie | None = None,
            preisaenderung_invest: float = 1.0,
    ) -> float:
        trasse_je_jahreswaerme = (
            self.investition_eur_pro_m / self.waermeliniendichte_mwh_pro_m
        )
        haus_je_jahreswaerme = self.hausanschluss_eur_pro_mwh_a
        foerder = 1.0 - self.foerderquote

        if trajektorie is None:
            a_netz = annuitaetsfaktor(wacc, self.lebensdauer)
            a_haus = annuitaetsfaktor(wacc, self.hausanschluss_lebensdauer)
            kapital = foerder * (
                a_netz * trasse_je_jahreswaerme + a_haus * haus_je_jahreswaerme
            )
            betrieb = self.betriebskostenanteil * trasse_je_jahreswaerme
            return kapital + betrieb

        bedarf = trajektorie.reihe()
        # Netz und Hausanschluss auf den Anfangsbedarf ausgelegt.
        trasse_brutto = trasse_je_jahreswaerme * bedarf[0]
        haus_brutto = haus_je_jahreswaerme * bedarf[0]
        rbf = diskontierte_summe([1.0] * len(bedarf), wacc)
        pv_kapital = foerder * (
            kapitalbarwert_mit_ersatz(
                trasse_brutto, self.lebensdauer, len(bedarf), wacc, preisaenderung_invest
            )
            + kapitalbarwert_mit_ersatz(
                haus_brutto, self.hausanschluss_lebensdauer, len(bedarf), wacc,
                preisaenderung_invest,
            )
        )
        pv_betrieb = self.betriebskostenanteil * trasse_brutto * rbf
        diskontierte_waerme = diskontierte_summe(bedarf, wacc)
        return (pv_kapital + pv_betrieb) / diskontierte_waerme


@dataclass(frozen=True)
class Versorgungsszenario:
    anteile: tuple[Versorgungsanteil, ...]
    netz: Netz | None = None

    def __post_init__(self):
        if len(self.anteile) == 0:
            raise ValueError("Versorgungsszenario braucht mindestens einen Anteil")
        summe = sum(a.deckungsanteil for a in self.anteile)
        if abs(summe - 1.0) > 1e-9:
            raise ValueError(f"Deckungsanteile summieren zu {summe}, erwartet 1")

    def waermegestehungskosten(self, trajektorie: Bedarfstrajektorie | None = None) -> float:
        erzeugung = sum(
            a.deckungsanteil * a.option.waermegestehungskosten(trajektorie)
            for a in self.anteile
        )
        if self.netz is None:
            return erzeugung

        leitend = self.anteile[0].option.realisierung
        c_d = self.netz.spezifische_kosten(
            leitend.wacc, trajektorie, leitend.preisaenderung_invest
        )
        return erzeugung * self.netz.verlustfaktor + c_d
