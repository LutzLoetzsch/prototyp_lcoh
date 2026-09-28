#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dss.szenarien.m6 import lcoh_m6
from e19_toolvergleich import prototyp_parameter

# Werte aus dem Werkzeug
LEISTUNG_KW, GEBAEUDE, HA_EUR = 5000.0, 300, 10000.0
TRASSE_M = 5000.0
ERZ_EUR_KW, ZINS, HORIZONT, WART_TOOL, P_ETA = 1250.0, 0.045, 20, 0.015, 44.125
AF = ZINS * (1 + ZINS) ** HORIZONT / ((1 + ZINS) ** HORIZONT - 1)

KT_STUFEN = (500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3000.0)
VBH_STUFEN = (1500, 1850, 2200)
VARIANTEN = ("A", "B")



def werkzeug(kt: float, vbh: int, variante: str) -> float:
    q = LEISTUNG_KW * vbh / 1000.0
    erz = ERZ_EUR_KW + (HA_EUR * GEBAEUDE / LEISTUNG_KW if variante == "B" else 0.0)
    inv = kt * TRASSE_M + erz * LEISTUNG_KW
    return (inv * AF * (1 + WART_TOOL)) / q + P_ETA


def rechenkern(kt: float, vbh: int, variante: str, L: bool, K: bool) -> float:
    p = prototyp_parameter(kt, vbh, "N1", variante)
    if L:
        p["netz_lebensdauer"] = float(HORIZONT)
        p["hausanschluss_lebensdauer"] = float(HORIZONT)
    if K:
        f = 1.0 - p["verlustanteil"]
        p["capex_bio"] = p["capex_bio"] * f
        p["capex_wp"] = p["capex_wp"] * f
    return lcoh_m6(p)


def lauf(L: bool, K: bool) -> tuple[float, float, int]:
    ab = []
    for var in VARIANTEN:
        for vbh in VBH_STUFEN:
            for kt in KT_STUFEN:
                w = werkzeug(kt, vbh, var)
                r = rechenkern(kt, vbh, var, L, K)
                ab.append((r / w - 1.0) * 100.0)
    mittel = sum(abs(x) for x in ab) / len(ab)
    groesste = max(abs(x) for x in ab)
    unter1 = sum(1 for x in ab if abs(x) <= 1.0)
    return mittel, groesste, unter1

def werkzeug_zerlegt(kt: float, vbh: int, variante: str) -> dict:
    """Die drei Kostenarten des Werkzeugs, wie sie seine Matrix ausweist."""
    q = LEISTUNG_KW * vbh / 1000.0
    erz = ERZ_EUR_KW + (HA_EUR * GEBAEUDE / LEISTUNG_KW if variante == "B" else 0.0)
    ann = (kt * TRASSE_M + erz * LEISTUNG_KW) * AF
    return {"kapital": ann / q, "betrieb": ann * WART_TOOL / q, "bedarf": P_ETA}



def kern_zerlegt(kt: float, vbh: int, variante: str) -> dict:
    from dss.szenarien.m6 import lcoh_m6
    p = prototyp_parameter(kt, vbh, "N1", variante)
    p["netz_lebensdauer"] = float(HORIZONT)
    p["hausanschluss_lebensdauer"] = float(HORIZONT)
    f = 1.0 - p["verlustanteil"]
    p["capex_bio"] = p["capex_bio"] * f
    p["capex_wp"] = p["capex_wp"] * f

    voll = lcoh_m6(p)
    ohne_bed = lcoh_m6({**p, "brennstoffpreis": 0.0, "strompreis": 0.0})
    ohne_bet = lcoh_m6({**p, "wartung_bio": 0.0, "wartung_wp": 0.0})
    nur_kap = lcoh_m6({**p, "brennstoffpreis": 0.0, "strompreis": 0.0,
                       "wartung_bio": 0.0, "wartung_wp": 0.0})
    bedarf, betrieb = voll - ohne_bed, voll - ohne_bet
    kapital = voll - bedarf - betrieb
    if abs(kapital - nur_kap) > 1e-6:
        raise SystemExit("Zerlegung nicht additiv, Rest "
                         f"{kapital - nur_kap:.9f} EUR/MWh")
    return {"kapital": kapital, "bedarf": bedarf, "betrieb": betrieb,
            "gesamt": voll}


def tabelle_zerlegung(out: Path, kt: float = 1500.0, vbh: int = 1850,
                      variante: str = "B") -> None:
    w, k = werkzeug_zerlegt(kt, vbh, variante), kern_zerlegt(kt, vbh, variante)
    wg = w["kapital"] + w["bedarf"] + w["betrieb"]

    def dz(x: float, n: int = 2, vz: bool = False) -> str:
        return (f"{x:+.{n}f}" if vz else f"{x:.{n}f}").replace(".", "{,}")

    z = [r"\begin{table}[htbp]", r"\centering", r"\footnotesize",
         r"\renewcommand{\arraystretch}{1.1}%",
         r"\begin{tabular}{p{5.2cm}rrr}", r"\toprule",
         r"\textbf{Kostenart} & \textbf{Planungs\-werkzeug} & "
         r"\textbf{Rechen\-kern} & \textbf{Differenz} \\",
         r"& [EUR/MWh] & [EUR/MWh] & [EUR/MWh] \\", r"\midrule"]
    for art, name in (("kapital", "kapitalgebunden"),
                      ("bedarf", "bedarfsgebunden"),
                      ("betrieb", "betriebsgebunden")):
        farbe = r"\rowcolor{gray!8}" if art != "bedarf" else ""
        z.append(f"{farbe}{name} & {dz(w[art])} & {dz(k[art])} & "
                 f"${dz(k[art]-w[art], 2, True)}$ \\\\")
    z += [r"\midrule",
          f"Summe & {dz(wg)} & {dz(k['gesamt'])} & "
          f"${dz(k['gesamt']-wg, 2, True)}$ \\\\",
          r"\bottomrule", r"\end{tabular}",
          r"\caption[Zerlegung eines Vergleichspunktes]{Die drei Kostenarten "
          r"an einem Punkt des Vergleichs, Trassenkosten "
          + f"\\num{{{kt:.0f}}}" + r"~EUR je Meter und "
          + f"\\num{{{vbh}}}" + r" Vollbenutzungsstunden. "
          r"Quelle: eigene Berechnung}",
          r"\label{tab:e19-zerlegung}", r"\end{table}"]
    (out / "e19_zerlegung.tex").write_text("\n".join(z) + "\n",
                                           encoding="utf-8")


# Plot
def zeichne(out: Path) -> None:
    sys.path.insert(0, str(Path(__file__).parent / "plots"))
    from _stil import setze_stil, speichere, SKALIERUNG
    import matplotlib.pyplot as plt

    setze_stil()
    plt.rcParams["figure.autolayout"] = False
    fig, ax = plt.subplots(figsize=(16 * SKALIERUNG, 9.5 * SKALIERUNG))
    stile = (("0.0", "-"), ("0.42", (0, (6, 2))), ("0.62", (0, (1, 2))))

    for vbh, (farbe, stil) in zip(VBH_STUFEN, stile):
        y = [(rechenkern(kt, vbh, "B", True, True) / werkzeug(kt, vbh, "B")
              - 1.0) * 100.0 for kt in KT_STUFEN]
        ax.plot(KT_STUFEN, y, color=farbe, linestyle=stil, linewidth=1.5,
                marker="o", markersize=4, markerfacecolor="white",
                label=f"{vbh} Vollbenutzungsstunden")
    ax.axhline(0.0, color="0.35", linewidth=1.0)

    ax.set_xlabel("spezifische Trassenkosten [EUR/m]")
    ax.set_ylabel("relative Abweichung [%]")
    ax.set_xlim(min(KT_STUFEN), max(KT_STUFEN))
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3,
              fontsize=8.5, handlelength=3.2)
    fig.subplots_adjust(bottom=0.28)
    speichere(fig, str(out / "E19_abweichung"))


def tabelle(out: Path) -> None:
    sp = r">{\raggedleft\arraybackslash}p"
    z = [r"\begin{table}[htbp]", r"\centering", r"\footnotesize",
         r"\renewcommand{\arraystretch}{1.1}%",
         r"\setlength{\tabcolsep}{4pt}%",
         r"\begin{tabular}{l" + sp + "{2.2cm}" + sp + "{2.4cm}" + sp + "{2.4cm}"
         + sp + "{2.2cm}" + sp + "{2.4cm}}",
         r"\toprule",
         r"\textbf{Nr.} & \textbf{Trassen\-kosten} & "
         r"\textbf{Vollbe\-nutzungs\-stunden} & \textbf{Planungs\-werkzeug} & "
         r"\textbf{Rechen\-kern} & \textbf{rel. Abweichung} \\",
         r"{}& [EUR/m] & [h/a] & [EUR/MWh] & [EUR/MWh] & [\%] \\",
         r"\midrule"]

    def dz(x: float, n: int, vz: bool = False) -> str:
        s = f"{x:+.{n}f}" if vz else f"{x:.{n}f}"
        return s.replace(".", "{,}")

    nr = 0
    for var in VARIANTEN:
        z.append(r"\multicolumn{6}{l}{\itshape "
                 + ("ohne Hausanschluss" if var == "A" else "mit Hausanschluss")
                 + r"} \\")
        for vbh in VBH_STUFEN:
            for kt in KT_STUFEN:
                nr += 1
                w = werkzeug(kt, vbh, var)
                r1 = rechenkern(kt, vbh, var, True, True)
                farbe = r"\rowcolor{gray!8}" if nr % 2 else ""
                z.append(
                    f"{farbe}{nr} & \\num{{{kt:.0f}}} & \\num{{{vbh}}} & "
                    f"{dz(w, 2)} & {dz(r1, 2)} & "
                    f"${dz((r1/w-1)*100, 2, True)}$ \\\\")
    z += [r"\bottomrule", r"\end{tabular}",
          r"\caption[Punktvergleich gegen das Planungswerkzeug]{Die "
          + str(nr) + r" Punkte des Vergleichs. Quelle: eigene Berechnung}",
          r"\label{tab:e19-punktvergleich}", r"\end{table}"]
    (out / "e19_punktvergleich.tex").write_text("\n".join(z) + "\n",
                                                encoding="utf-8")


def main() -> None:
    # einmal rechnen, damit die Varianten hier auch direkt geprüft werden
    for L, K in ((False, False), (True, False), (False, True), (True, True)):
        lauf(L, K)

    out = Path("reports/Experimentierlauf_Wuensdorf/E19_toolvergleich")
    out.mkdir(parents=True, exist_ok=True)

    pfad = out / "e19_punktvergleich_exceltool_gegen_rechenkern.csv"
    with pfad.open("w", newline="", encoding="utf-8") as fh:
        s = csv.writer(fh, delimiter=";")
        s.writerow([
            "variante", "vollbenutzungsstunden",
            "waermeliniendichte_mwh_pro_m_a", "trassenkosten_eur_pro_m",
            "EXCELTOOL_SAENA_eur_pro_mwh", "RECHENKERN_roh_eur_pro_mwh",
            "abweichung_roh_prozent", "RECHENKERN_angeglichen_eur_pro_mwh",
            "abweichung_angeglichen_prozent"
        ])

        for var in VARIANTEN:
            for vbh in VBH_STUFEN:
                for kt in KT_STUFEN:
                    w = werkzeug(kt, vbh, var)
                    r0 = rechenkern(kt, vbh, var, False, False)
                    r1 = rechenkern(kt, vbh, var, True, True)

                    s.writerow([
                        var, vbh,
                        f"{vbh/1000:.3f}".replace(".", ","),
                        f"{kt:.0f}",
                        f"{w:.3f}".replace(".", ","),
                        f"{r0:.3f}".replace(".", ","),
                        f"{(r0/w-1)*100:+.2f}".replace(".", ","),
                        f"{r1:.3f}".replace(".", ","),
                        f"{(r1/w-1)*100:+.2f}".replace(".", ",")
                    ])

    zeichne(out)
    tabelle(out)

    tabelle_zerlegung(out)
    print("fertig")


if __name__ == "__main__":
    main()
