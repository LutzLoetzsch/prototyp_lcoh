#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dss.szenarien.m6 import M6_BASIS, lcoh_m6
import dss.entscheidung.dez_referenz as dz

from e19_toolvergleich import prototyp_parameter

# Fall aus Fachgespräch
LEISTUNG_KW = 5000.0
GEBAEUDE = 300
HA_EUR = 10000.0
VBH = 1850
WAERMEMENGE = LEISTUNG_KW * VBH / 1000.0

ERZ_EUR_KW = 1250.0
ZINS = 0.045
HORIZONT = 20
WART_TOOL = 0.015
P_ETA = 44.125
GEWINNZIEL = 0.0

FOERDERSTUFEN = (0.0, 0.20, 0.30, 0.40)     # BEW
NORMALISIERT = False   # per --normalisiert gesetzt
LAENGEN = list(range(1000, 16001, 250))


def af(i: float = ZINS, n: int = HORIZONT) -> float:
    return i * (1 + i) ** n / ((1 + i) ** n - 1)


def werkzeug(laenge_m: float, kt: float, foerder: float = 0.0) -> float:
    """Waermepreis des Netzes nach der Rechenvorschrift des Werkzeugs."""
    erz = ERZ_EUR_KW + HA_EUR * GEBAEUDE / LEISTUNG_KW
    inv = kt * laenge_m * (1.0 - foerder) + erz * LEISTUNG_KW
    ann = inv * af()
    return (ann * (1.0 + WART_TOOL)) / WAERMEMENGE * (1.0 + GEWINNZIEL) + P_ETA


def _basis(**kw) -> dict:
    p = dict(M6_BASIS)
    p.update({"wacc": ZINS, "betrachtungszeitraum": float(HORIZONT),
              "bedarfsrate": 0.0, "co2_preis": 0.0})
    p.update(kw)
    return p


def rechenkern(laenge_m: float, kt: float, foerder: float = 0.0) -> float:
    p = prototyp_parameter(kt, VBH, "N1", "B")
    p["waermeliniendichte"] = WAERMEMENGE / laenge_m
    p["netz_foerderquote"] = foerder
    if NORMALISIERT:
        # Werkzeugkonventionen
        f = 1.0 - p["verlustanteil"]
        p["capex_bio"] = p["capex_bio"] * f
        p["capex_wp"] = p["capex_wp"] * f
    return lcoh_m6(p)


def dezentral() -> float:
    return dz.lcoh_dez(_basis())

def grenzlaenge(fn, kt: float, foerder: float, ziel: float) -> float | None:
    lo, hi = 200.0, 80000.0
    if fn(lo, kt, foerder) >= ziel:
        return None
    if fn(hi, kt, foerder) <= ziel:
        return None
    for _ in range(90):
        m = 0.5 * (lo + hi)
        if fn(m, kt, foerder) < ziel:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)



sys.path.insert(0, str(Path(__file__).parent / "plots"))


def _rahmen():
    from _stil import setze_stil, SKALIERUNG
    import matplotlib.pyplot as plt
    setze_stil()
    plt.rcParams["figure.autolayout"] = False
    return plt.subplots(figsize=(16 * SKALIERUNG, 10 * SKALIERUNG))


KURVEN = (("0.45", "-"), ("0.45", (0, (6, 2))),
          ("0.6", (0, (6, 2, 1, 2))), ("0.72", (0, (1, 2))))


def _legende(ax, fig, tief: bool = False):
    """tief=True fuer Achsentitel mit Bruch, der zwei Zeilen hoch ist."""
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.26 if tief else -0.16),
              ncol=2, fontsize=8.5, handlelength=3.2)
    fig.subplots_adjust(bottom=0.36 if tief else 0.30)


def zeichne(kt: float, dez: float, pfad: Path, xmax_km: float = 10.0) -> None:
    from _stil import speichere
    fig, ax = _rahmen()
    laengen = [L for L in LAENGEN if L <= xmax_km * 1000]
    x = [L / 1000.0 for L in laengen]

    ax.plot(x, [werkzeug(L, kt, 0.0) for L in laengen],
            color="0.0", linestyle="-", linewidth=2.2,
            label="Planungswerkzeug, ohne Förderung")
    for f, (farbe, stil) in zip(FOERDERSTUFEN, KURVEN):
        ax.plot(x, [rechenkern(L, kt, f) for L in laengen],
                color=farbe, linestyle=stil, linewidth=1.5,
                label=f"Rechenkern, Förderung {int(f*100)} %")
    ax.plot([], [], color="0.2", linestyle=(0, (1, 1.6)), linewidth=1.3,
            label=f"dezentrale Luft-Wärmepumpe, {dez:.1f} EUR/MWh")
    ax.axhline(dez, color="0.2", linestyle=(0, (1, 1.6)), linewidth=1.3)
    # 5 km aus Gespräch
    ax.axvline(5.0, color="0.82", linewidth=1.0, zorder=0)
    ax.set_xlabel("Trassenlänge [km]")
    ax.set_ylabel("Wärmegestehungskosten [EUR/MWh]")
    ax.set_xlim(min(x), max(x))
    _legende(ax, fig)
    speichere(fig, str(pfad))


def zeichne_ql(kt: float, dez: float, pfad: Path,
               ql_min: float = 0.5, ql_max: float = 3.0) -> None:
    from _stil import speichere
    fig, ax = _rahmen()
    n = 160
    qls = [ql_min + (ql_max - ql_min) * k / (n - 1) for k in range(n)]
    laengen = [WAERMEMENGE / q for q in qls]

    ax.plot(qls, [werkzeug(L, kt, 0.0) for L in laengen],
            color="0.0", linestyle="-", linewidth=2.2,
            label="Planungswerkzeug, ohne Förderung")
    for f, (farbe, stil) in zip(FOERDERSTUFEN, KURVEN):
        ax.plot(qls, [rechenkern(L, kt, f) for L in laengen],
                color=farbe, linestyle=stil, linewidth=1.5,
                label=f"Rechenkern, Förderung {int(f*100)} %")
    ax.plot([], [], color="0.2", linestyle=(0, (1, 1.6)), linewidth=1.3,
            label=f"dezentrale Luft-Wärmepumpe, {dez:.1f} EUR/MWh")

    ax.axhline(dez, color="0.2", linestyle=(0, (1, 1.6)), linewidth=1.3)
    ax.set_xlabel(r"Wärmeliniendichte $\left[\dfrac{\mathrm{MWh}}{\mathrm{m}\cdot\mathrm{a}}\right]$")
    ax.set_ylabel("Wärmegestehungskosten [EUR/MWh]")
    ax.set_xlim(ql_min, ql_max)
    _legende(ax, fig, tief=True)
    speichere(fig, str(pfad))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kt", type=float, default=1850.0,
                    help="spez. Trassenkosten [EUR/m], Praxisband 500 bis 3000")
    ap.add_argument("--normalisiert", action="store_true",
                    help="Konventionen des Werkzeugs uebernehmen: Nutzungsdauer "
                         "des Netzes und Auslegung des Erzeugers")
    ap.add_argument("--xmax", type=float, default=10.0,
                    help="obere Grenze der Laengenachse [km]")
    ap.add_argument("--qlmin", type=float, default=0.5,
                    help="untere Grenze der Dichteachse [MWh/(m*a)]")
    ap.add_argument("--qlmax", type=float, default=3.0,
                    help="obere Grenze der Dichteachse [MWh/(m*a)]")
    ap.add_argument("--out", default="reports/Experimentierlauf_Wuensdorf/"
                                     "E19_toolvergleich")
    a = ap.parse_args()

    global NORMALISIERT
    NORMALISIERT = a.normalisiert

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dez = dezentral()

    zeilen = []
    for L in LAENGEN:
        z = {"laenge_m": L, "waermeliniendichte": round(WAERMEMENGE / L, 4),
             "werkzeug": round(werkzeug(L, a.kt), 3)}
        for f in FOERDERSTUFEN:
            z[f"rechenkern_f{int(f*100)}"] = round(rechenkern(L, a.kt, f), 3)
        zeilen.append(z)

    grenzen = []
    for f in FOERDERSTUFEN:
        lk = grenzlaenge(rechenkern, a.kt, f, dez)
        lw = grenzlaenge(werkzeug, a.kt, f, dez)
        grenzen.append({
            "foerderquote": f,
            "grenzlaenge_rechenkern_m": round(lk) if lk else None,
            "grenzlaenge_werkzeug_m": round(lw) if lw else None,
            "abweichung_prozent": round((lk / lw - 1) * 100, 2) if lk and lw else None,
            "q_l_an_der_grenze": round(WAERMEMENGE / lk, 3) if lk else None,
        })

    d = {"id": "E19-T3", "trassenkosten_eur_pro_m": a.kt,
         "konventionen_angeglichen": NORMALISIERT,
         "waermemenge_mwh_a": WAERMEMENGE, "vollbenutzungsstunden": VBH,
         "leistung_kw": LEISTUNG_KW, "gebaeude": GEBAEUDE,
         "dezentral_eur_pro_mwh": round(dez, 3),
         "grenzlaengen": grenzen, "kurven": zeilen}
    stamm = "e19_grenzlaenge" + ("_angeglichen" if NORMALISIERT else "")
    (out / f"{stamm}.json").write_text(
        json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

    t = [f"# E19-T3 — Grenzlänge, kT = {a.kt:.0f} EUR/m"
         + ("  (Konventionen angeglichen)" if NORMALISIERT else ""), "",
         f"Wärmemenge {WAERMEMENGE:.0f} MWh/a konstant, "
         f"dezentrale Referenz {dez:.2f} EUR/MWh", "",
         "| Förderung | Rechenkern | Werkzeug | Abw. | Q_l an der Grenze |",
         "|---|---:|---:|---:|---:|"]
    for g in grenzen:
        t.append(f"| {int(g['foerderquote']*100)} % | "
                 f"{g['grenzlaenge_rechenkern_m'] or '—'} m | "
                 f"{g['grenzlaenge_werkzeug_m'] or '—'} m | "
                 f"{g['abweichung_prozent'] or '—'} % | "
                 f"{g['q_l_an_der_grenze'] or '—'} |")
    (out / f"{stamm}.md").write_text("\n".join(t) + "\n", encoding="utf-8")

    with (out / f"{stamm}_exceltool_gegen_rechenkern.csv").open("w", newline="", encoding="utf-8") as fh:
        s = csv.writer(fh, delimiter=";")
        s.writerow(["trassenlaenge_m", "waermeliniendichte_mwh_pro_m_a",
                    "EXCELTOOL_SAENA_ohne_foerderung_eur_pro_mwh"]
                   + [f"RECHENKERN_foerderung_{int(f*100)}pct_eur_pro_mwh"
                      for f in FOERDERSTUFEN])
        for z in zeilen:
            s.writerow([z["laenge_m"], f'{z["waermeliniendichte"]:.4f}'.replace(".", ","),
                        f'{z["werkzeug"]:.3f}'.replace(".", ",")]
                       + [f'{z[f"rechenkern_f{int(f*100)}"]:.3f}'.replace(".", ",")
                          for f in FOERDERSTUFEN])

    name = "E19_grenzlaenge" + ("_angeglichen" if NORMALISIERT else "")
    zeichne(a.kt, dez, out / name, a.xmax)

    zeichne_ql(a.kt, dez, out / name.replace("grenzlaenge", "dichte"),
               a.qlmin, a.qlmax)
    print("fertig")


if __name__ == "__main__":
    main()
