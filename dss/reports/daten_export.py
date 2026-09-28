from __future__ import annotations

import sys
from pathlib import Path

for _p in Path(__file__).resolve().parents:
    if (_p / "src" / "dss").is_dir():
        WURZEL = _p
        sys.path.insert(0, str(_p / "src"))
        break

import numpy as np




from dss.surrogat.daten import datensatz, PARAM_NAMEN

# Datensätze wie im Training
TEILE = (
    ("training", 20000, 1),
    ("validierung", 5000, 2),
    ("test", 5000, 3),
)
ZIEL = Path("daten/records")
TRENNER = ";"
NACHKOMMA = 6


def _zeile(werte) -> str:
    return TRENNER.join(f"{v:.{NACHKOMMA}f}".replace(".", ",") for v in werte)

################


def main() -> None:
    ziel = WURZEL / ZIEL
    ziel.mkdir(parents=True, exist_ok=True)
    kopf = TRENNER.join([*PARAM_NAMEN, "lcoh_eur_pro_mwh"])

    saetze = {}
    for name, n, seed in TEILE:
        X, y = datensatz(n, seed=seed)
        saetze[name] = X
        pfad = ziel / f"{name}_n{n}_seed{seed}.csv"
        with pfad.open("w", encoding="utf-8", newline="\n") as f:
            f.write(kopf + "\n")
            for zeile, wert in zip(X, np.ravel(y)):
                f.write(_zeile([*zeile, wert]) + "\n")
        print(f"geschrieben: {pfad}  ({n} Zeilen, "
              f"{pfad.stat().st_size / 1e6:.1f} MB)")

    # kurz prüfen, ob sich Punkte überschneiden
    print("\nÜberschneidungen:")
    namen = list(saetze)
    for i in range(len(namen)):
        for j in range(i + 1, len(namen)):
            a = {tuple(np.round(r, 12)) for r in saetze[namen[i]]}
            b = {tuple(np.round(r, 12)) for r in saetze[namen[j]]}
            print(f"  {namen[i]:12s} gegen {namen[j]:12s} {len(a & b)}")

    print("\nRandabweichung:")
    schlimmste = ("", 0.0)
    for k, p in enumerate(PARAM_NAMEN):
        spalten = [saetze[n][:, k] for n in namen]
        lo = [s.min() for s in spalten]
        hi = [s.max() for s in spalten]
        band = max(hi) - min(lo)
        d = max(max(lo) - min(lo), max(hi) - min(hi)) / band if band else 0.0
        if d > schlimmste[1]:
            schlimmste = (p, d)
    print(f"  {schlimmste[0]}: {schlimmste[1] * 1000:.3f} Promille des Bandes")


if __name__ == "__main__":
    main()
