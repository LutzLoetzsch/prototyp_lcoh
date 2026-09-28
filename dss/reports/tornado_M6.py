from __future__ import annotations

import sys
from pathlib import Path

for _p in Path(__file__).resolve().parents:
    if (_p / "src" / "dss").is_dir():
        sys.path.insert(0, str(_p / "src"))
        break

from dss.szenarien import m6
from dss.reporting.stil import ThesisStil

ANZAHL = 10
BALKENDICKE = 0.34
ZEILENHOEHE = 0.21   # Zoll je Balken
RAND_OBEN = 0.20
RAND_UNTEN = 0.20
BREITE = 5.2
BANDABSTAND = 0.025
LINIENGRAU = "0.80"
LINIENSTAERKE = 0.4
PUNKTE = 200
AUSGABE = Path(__file__).resolve().parent / "abbildungen"

LABELS: dict[str, tuple[str, str, float, int]] = {
    "waermeliniendichte": ("Wärmeliniendichte", "MWh/(m a)", 1.0, 1),
    "netz_invest": ("Netzkosten", "EUR/m", 1.0, 0),
    "jaz": ("Jahresarbeitszahl", "", 1.0, 1),
    "brennstoffpreis": ("Brennstoffpreis", "EUR/MWh", 1.0, 0),
    "netz_lebensdauer": ("Netz-Lebensdauer", "a", 1.0, 0),
    "betrachtungszeitraum": ("Betrachtungszeitraum", "a", 1.0, 0),
    "capex_wp": ("CAPEX Wärmepumpe", "EUR/kW", 1.0, 0),
    "capex_bio": ("CAPEX Biomasse", "EUR/kW", 1.0, 0),
    "strompreis": ("Strompreis", "EUR/MWh", 1.0, 0),
    "vlh_wp": ("Volllaststunden WP", "h/a", 1.0, 0),
    "vlh_bio": ("Volllaststunden Biomasse", "h/a", 1.0, 0),
    "nutzungsgrad": ("Nutzungsgrad Biomasse", "%", 100.0, 0),
    "verlustanteil": ("Netzverluste", "%", 100.0, 1),
    "hausanschluss": ("Hausanschluss", "EUR/(MWh a)", 1.0, 0),
    "wacc": ("WACC", "%", 100.0, 1),
    "co2_preis": ("CO2-Preis", "EUR/t", 1.0, 0),
    "foerderquote": ("Förderquote Erzeuger", "%", 100.0, 0),
    "netz_foerderquote": ("Netzförderung", "%", 100.0, 0),
    "grundlast_anteil": ("Grundlastanteil WP", "%", 100.0, 0),
    "bedarfsrate": ("Bedarfsrate", "%/a", 100.0, 1),
}


def _bandtext(p: str, x) -> str:
    _, einheit, faktor, stellen = LABELS[p]
    lo, hi = min(x) * faktor, max(x) * faktor
    z = f"{lo:.{stellen}f} bis {hi:.{stellen}f}".replace(".", ",")
    return f"{z} {einheit}".strip()


def main() -> None:
    wirkungen: dict[str, float] = {}
    baender: dict[str, str] = {}
    for p in LABELS:
        try:
            x, y = m6.parameter_sweep(p, punkte=PUNKTE)
        except Exception:
            continue
        wirkungen[p] = float(y[-1]) - float(y[0])
        baender[p] = _bandtext(p, x)

    rang = sorted(wirkungen.items(), key=lambda kv: abs(kv[1]), reverse=True)
    auswahl = rang[:ANZAHL]

    import matplotlib.pyplot as plt

    stil = ThesisStil()
    stil.anwenden()
    items = sorted(auswahl, key=lambda kv: abs(kv[1]))
    namen = [LABELS[p][0] for p, _ in items]
    werte = [w for _, w in items]
    bandtexte = [baender[p] for p, _ in items]

    n = len(namen)
    hoehe = ZEILENHOEHE * n + RAND_OBEN + RAND_UNTEN + 0.55
    fig, ax = stil.figur(BREITE, hoehe)

    for i in range(len(namen)):
        ax.axhline(i, color=LINIENGRAU, linewidth=LINIENSTAERKE, zorder=0)

    ax.barh(namen, werte, height=BALKENDICKE,
            color=stil.flaeche, edgecolor="0.3", linewidth=0.6, zorder=2)
    ax.axvline(0.0, color="0.3", linewidth=0.7, zorder=1)
    ax.set_xlabel("Wirkung über das Band [EUR/MWh]", fontsize=8)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=7.5)
    ax.tick_params(axis="x", labelsize=6.5)
    ax.set_ylim(-0.5 - RAND_UNTEN / ZEILENHOEHE,
                n - 0.5 + RAND_OBEN / ZEILENHOEHE)

    for i, txt in enumerate(bandtexte):
        ax.text(1.0 + BANDABSTAND, i, txt,
                transform=ax.get_yaxis_transform(),
                va="center", ha="left", fontsize=6.5, color="0.25",
                clip_on=False)

    fig.tight_layout(pad=0.4)

    AUSGABE.mkdir(exist_ok=True)
    stamm = AUSGABE / "m6_tornado_baender"
    for e in ("pdf", "png"):
        fig.savefig(f"{stamm}.{e}", bbox_inches="tight")
    plt.close(fig)
    print("erzeugt:", stamm)


if __name__ == "__main__":
    main()
