from __future__ import annotations

import sys
from pathlib import Path

for _p in Path(__file__).resolve().parents:
    if (_p / "src" / "dss").is_dir():
        sys.path.insert(0, str(_p / "src"))
        break

from dss.szenarien import m6
from dss.reporting.stil import ThesisStil

SPALTEN = 2
REIHEN = 3
BREITE = 6.3
PANEL_HOEHE = 1.7
PUNKTE = 400
AUSGABE = Path(__file__).resolve().parent / "abbildungen"

ANZEIGE: dict[str, str] = {
    "betrachtungszeitraum": "Betrachtungszeitraum [a]",
    "netz_lebensdauer": "Netz-Lebensdauer [a]",
    "waermeliniendichte": "Wärmeliniendichte [MWh/(m a)]",
    "jaz": "Jahresarbeitszahl Wärmepumpe",
    "brennstoffpreis": "Brennstoffpreis [EUR/MWh]",
    "netz_invest": "Netzkosten [EUR/m]",
}
REIHENFOLGE = list(ANZEIGE)
Y_TITEL = "Wärmegestehungskosten [EUR/MWh]"


def main() -> None:
    import matplotlib.pyplot as plt

    stil = ThesisStil()
    stil.anwenden()

    sweeps = {p: m6.parameter_sweep(p, punkte=PUNKTE) for p in REIHENFOLGE}

    fig, achsen = plt.subplots(
        REIHEN, SPALTEN,
        figsize=(BREITE, PANEL_HOEHE * REIHEN),
    )
    for ax, p in zip(achsen.flat, REIHENFOLGE):
        x, y = sweeps[p]
        ax.plot(x, y, "-", color="0.12", linewidth=1.5)
        ax.set_xlabel(ANZEIGE[p], fontsize=8)
        ax.tick_params(labelsize=7)

    fig.supylabel(Y_TITEL, fontsize=8)
    fig.subplots_adjust(wspace=0.28, hspace=0.62,
                        left=0.115, right=0.985, top=0.985, bottom=0.09)

    AUSGABE.mkdir(exist_ok=True)
    stamm = AUSGABE / "m6_funktionsplots_kern_2sp"
    for e in ("pdf", "png"):
        fig.savefig(f"{stamm}.{e}", dpi=300)
    plt.close(fig)
    print("erzeugt:", f"{stamm}.pdf", f"{stamm}.png")


if __name__ == "__main__":
    main()
