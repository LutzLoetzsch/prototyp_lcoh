from __future__ import annotations

import sys
from pathlib import Path

for _p in Path(__file__).resolve().parents:
    if (_p / "src" / "dss").is_dir():
        sys.path.insert(0, str(_p / "src"))
        break

import numpy as np

from dss.szenarien import screening_netz_dezentral as scr
from dss.kommunen import weisswasser as ww
from dss.fachmodell.bedarf import Bedarfstrajektorie, Segment
from dss.reporting.stil import ThesisStil

RASTER_EUR = 0.5
RASTER_GRAU = "0.85"
RASTER_STAERKE = 0.4


def _industrie_reihe(anschlussjahr: int) -> list[float]:
    reihe = []
    for jahr in range(1, ww.BETRACHTUNGSZEITRAUM + 1):
        if jahr < anschlussjahr:
            reihe.append(ww._INDUSTRIE_BESTAND)
        else:
            reihe.append(ww._INDUSTRIE_NEU * (1.0 + ww._INDUSTRIE_WACHSTUM) ** (jahr - anschlussjahr))
    return reihe


def _trajektorie(anschlussjahr: int) -> Bedarfstrajektorie:
    return Bedarfstrajektorie(
        T=ww.BETRACHTUNGSZEITRAUM,
        segmente=(
            Segment.geometrisch("Haushalt", 9000.0, rate=-0.012, T=ww.BETRACHTUNGSZEITRAUM),
            Segment.aus_reihe("Industrie-Neuansiedlung", _industrie_reihe(anschlussjahr)),
        ),
    )


def _lcoh(anschlussjahr: int) -> float:
    return ww.erzeuger.waermegestehungskosten(ww.realisierung, _trajektorie(anschlussjahr))


def abbildung_knick(stil: ThesisStil, ausgabe: Path,
                    mit_approximation: bool = False) -> Path:
    import matplotlib.pyplot as plt

    fig, ax = stil.figur(4.2, 3.2)
    qs, zentral, dezentral = scr.kurve(foerderung=True)
    minkurve = np.minimum(zentral, dezentral)
    schw = scr.schwelle(foerderung=True)

    ax.plot(qs, minkurve, "-", color="0.12", linewidth=1.6,
            label="Rechenkern, min(zentral, dezentral)")
    if mit_approximation:
        beta = 0.5
        softmin = -1.0 / beta * np.log(np.exp(-beta * zentral)
                                       + np.exp(-beta * dezentral))
        ax.plot(qs, softmin, "--", color="0.55", linewidth=1.3,
                label="glatte Approximation (Softmin)")
    if schw is not None:
        yk = float(np.interp(schw, qs, minkurve))
        ax.plot([schw], [yk], "o", color="0.12", markersize=4)

    ax.set_xlabel("Wärmeliniendichte [MWh/(m a)]")
    ax.set_ylabel("Wärmegestehungskosten [EUR/MWh]")
    ax.set_ylim(130, 160)
    if mit_approximation:
        ax.legend(fontsize=7, loc="upper right")

    fig.tight_layout()
    stamm = "abb_knick_entscheidung" + ("_approx" if mit_approximation else "")
    for e in ("pdf", "png"):
        fig.savefig(ausgabe / f"{stamm}.{e}", dpi=150)
    plt.close(fig)

    return ausgabe / f"{stamm}.pdf"


def abbildung_sprung(stil: ThesisStil, ausgabe: Path) -> Path:
    import matplotlib.pyplot as plt

    fig, ax = stil.figur(4.6, 3.2)

    # Ab Jahr 2 einheitliche Auslegungsbasis von 9600 MWh
    ajs = np.arange(2, ww.BETRACHTUNGSZEITRAUM + 1)
    lcohs = np.array([_lcoh(int(a)) for a in ajs])
    ax.step(ajs, lcohs, where="post", color="0.12", linewidth=1.6)
    ax.plot(ajs, lcohs, "o", color="0.12", markersize=3)

    ax.set_xlabel("Anschlussjahr des Großanschlusses")
    ax.set_ylabel("Erzeugerkosten [EUR/MWh]")

    from matplotlib.ticker import MultipleLocator
    ax.yaxis.set_minor_locator(MultipleLocator(RASTER_EUR))
    ax.grid(axis="y", which="minor", color=RASTER_GRAU,
            linewidth=RASTER_STAERKE, zorder=0)
    ax.grid(axis="y", which="major", color=RASTER_GRAU,
            linewidth=RASTER_STAERKE, zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(ausgabe / f"abb_sprung_grossanschluss.{e}", dpi=150)
    plt.close(fig)

    return ausgabe / "abb_sprung_grossanschluss.pdf"


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--mit-approximation", action="store_true",
                    help="Softmin-Kurve mitzeichnen, für Abschnitt 6.3")
    a = ap.parse_args()

    stil = ThesisStil()
    stil.anwenden()
    ausgabe = Path(__file__).resolve().parent / "abbildungen"
    ausgabe.mkdir(exist_ok=True)

    p1 = abbildung_knick(stil, ausgabe, a.mit_approximation)
    p2 = abbildung_sprung(stil, ausgabe)
    print("erzeugt:", p1, p2)


if __name__ == "__main__":
    main()
