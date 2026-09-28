#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np

from dss.arme.komposition import komponiere, kompositionsfaktoren, voll
from dss.entscheidung.dez_referenz import JAZ_DEZ
from dss.surrogat.daten import PARAM_NAMEN
from dss.surrogat.persistenz import lade_modell, vorhersage
from dss.szenarien.m6 import EMIS_HOLZ, EMIS_STROM, M6_BASIS, SWEEP_BEREICHE

STANDARD_MODELLORDNER = Path("reports/E07_entscheidung/modelle")
ARMNAMEN: tuple[str, ...] = ("wp", "bio", "dez")
RAHMEN_AUSSERHALB: tuple[str, ...] = ("co2_preis", "betrachtungszeitraum", "hausanschluss")
WIRKUNGSSCHWELLE: float = 1e-9

CO2_TRAINING: float = float(M6_BASIS["co2_preis"])
ANALYTISCH_KORRIGIERT: tuple[str, ...] = ("co2_preis",)


def modellpfad(ordner: Path | str, name: str) -> Path:
    return Path(ordner) / f"e07_{name}.pt"


def co2_korrektur(p: dict) -> dict[str, float]:
    pv = voll(p)
    d = float(pv["co2_preis"]) - CO2_TRAINING
    return {
        "wp": EMIS_STROM / float(pv["jaz"]) * d,
        "bio": EMIS_HOLZ / float(pv["nutzungsgrad"]) * d,
        "dez": EMIS_STROM / float(JAZ_DEZ) * d,
    }


def wirkung_auf_arme(schluessel: str, p: dict | None = None) -> dict:
    from dss.arme.bio import lcoh_bio
    from dss.arme.wp import lcoh_wp

    basis = voll(dict(p or {}))
    a = float(M6_BASIS[schluessel])
    lo, hi = SWEEP_BEREICHE[schluessel]
    b = float(lo) if abs(a - lo) >= abs(hi - a) else float(hi)

    p_a = {**basis, schluessel: a}
    p_b = {**basis, schluessel: b}

    aenderungen: dict[str, float] = {}
    for name, funktion in (("wp", lcoh_wp), ("bio", lcoh_bio)):
        va, vb = float(funktion(p_a)), float(funktion(p_b))
        aenderungen[name] = abs(vb - va) / abs(va) if va else float("inf")

    return {
        "parameter": schluessel,
        "stuetzstellen": {"default": a, "vergleich": b},
        "relative_aenderung": aenderungen,
        "wirksam": max(aenderungen.values()) > WIRKUNGSSCHWELLE,
    }


def trainingsraum_bericht(p: dict | None = None) -> dict:
    return {k: wirkung_auf_arme(k, p) for k in RAHMEN_AUSSERHALB}


def pruefe_trainingsraum(bereinigt: dict, bericht: dict | None = None) -> tuple[list[str], list[str]]:
    bericht = bericht if bericht is not None else trainingsraum_bericht()
    sperren: list[str] = []
    hinweise: list[str] = []

    if bereinigt.get("bedarfsreihe"):
        sperren.append(
            "bedarfsreihe: Der Kompositionspfad baut die Trajektorie aus "
            "bedarfsrate und einer festen Ausgangsmenge; die explizite "
            "Jahresreihe wird nicht gelesen. Ein nicht-monotoner Bedarf ist "
            "im Modus surrogat nicht abbildbar.")

    for k in RAHMEN_AUSSERHALB:
        if k not in bereinigt:
            continue
        default = float(M6_BASIS[k])
        wert = float(bereinigt[k])
        if abs(wert - default) <= 1e-12:
            continue
        if k in ANALYTISCH_KORRIGIERT:
            hinweise.append(
                f"{k} = {_de(wert)} weicht vom Trainingsdefault {_de(default)} ab. "
                f"Die Größe bewegt die Arm-LCOH, geht aber in geschlossener "
                f"Form ein und wird analytisch nachgetragen. Der Nachtrag ist "
                f"exakt und fügt keinen Approximationsfehler hinzu.")
            continue
        if bericht[k]["wirksam"]:
            sperren.append(
                f"{k} = {_de(wert)} weicht vom Trainingsdefault {_de(default)} ab. "
                f"Die Größe bewegt die Arm-LCOH (gemessen: "
                f"{_de(100 * max(bericht[k]['relative_aenderung'].values()), 3)} % "
                f"über die Szenarienspanne), das Surrogat hat sie jedoch als "
                f"Konstante gelernt. Ein Vergleich über diese Achse ist im "
                f"Modus surrogat nicht rechenbar.")
        else:
            hinweise.append(
                f"{k} = {_de(wert)} weicht vom Trainingsdefault {_de(default)} ab, "
                f"geht aber nicht in die Arme ein, sondern analytisch in den "
                f"Netzterm. Der Wert wird korrekt berücksichtigt.")
    return sperren, hinweise


def _de(x: float, stellen: int = 4) -> str:
    s = f"{x:,.{stellen}f}".rstrip("0").rstrip(".")
    if not s or s in ("-", ""):
        s = f"{x:,.{stellen}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


class Surrogatarme:
    def __init__(self, ordner: Path | str | None = None, device: str = "cpu") -> None:
        self.ordner = Path(ordner) if ordner else STANDARD_MODELLORDNER
        self.device = device
        self.netze: dict[str, tuple] = {}
        fehlend = [n for n in ARMNAMEN if not modellpfad(self.ordner, n).exists()]
        if fehlend:
            raise FileNotFoundError(
                f"Armmodelle nicht gefunden in {self.ordner}: "
                f"{', '.join('e07_' + n + '.pt' for n in fehlend)}. "
                f"Ordner über --modelle angeben oder aus dem Repo-Wurzelverzeichnis aufrufen.")
        for name in ARMNAMEN:
            self.netze[name] = lade_modell(modellpfad(self.ordner, name), device=device)

    @property
    def herkunft(self) -> dict:
        return {
            name: {
                "datei": str(modellpfad(self.ordner, name)),
                "ziel": self.netze[name][3].get("ziel"),
                "datum": self.netze[name][3].get("datum"),
                "topologie": self.netze[name][3].get("versteckt"),
                "n_parameter": self.netze[name][3].get("n_parameter"),
                "experiment": self.netze[name][3].get("extra", {}).get("experiment"),
            }
            for name in ARMNAMEN
        }

    def _eingang(self, p: dict) -> np.ndarray:
        pv = voll(p)
        fehlend = [k for k in PARAM_NAMEN if k not in pv]
        if fehlend:
            raise KeyError(f"Parameter fehlen und stehen nicht in M6_BASIS: {fehlend}")
        return np.array([[float(pv[k]) for k in PARAM_NAMEN]], dtype=np.float64)

    def arm_lcoh(self, p: dict) -> dict[str, float]:
        pv = voll(p)
        X = self._eingang(pv)
        nachtrag = co2_korrektur(pv)
        return {
            name: float(vorhersage(*self.netze[name][:3], X, device=self.device)[0])
            + nachtrag[name]
            for name in ARMNAMEN
        }

    def arme(self, p: dict) -> tuple[float, float]:
        werte = self.arm_lcoh(p)
        return komponiere(werte["wp"], werte["bio"], voll(p)), werte["dez"]

    def zerlegung(self, p: dict) -> dict:
        pv = voll(p)
        werte = self.arm_lcoh(pv)
        s, verlustfaktor, c_d = kompositionsfaktoren(pv)
        erzeugung = s * werte["wp"] + (1.0 - s) * werte["bio"]
        return {
            "arm_wp": round(werte["wp"], 4),
            "arm_bio": round(werte["bio"], 4),
            "arm_dezentral": round(werte["dez"], 4),
            "grundlast_anteil": round(float(s), 4),
            "erzeugungsterm": round(float(erzeugung), 4),
            "verlustfaktor": round(float(verlustfaktor), 6),
            "netzterm_c_d": round(float(c_d), 4),
            "quelle": {
                "arme": "Surrogat (MLP, E07)",
                "mischung_verluste_netzterm": "analytisch",
            },
        }
