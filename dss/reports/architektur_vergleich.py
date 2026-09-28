#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from dss.surrogat import Standardisierer, Trainingskonfig, datensatz, setze_seed
from dss.surrogat.daten import PARAM_NAMEN
from dss.surrogat.metriken import metriken
from dss.surrogat.modell import n_parameter
from dss.surrogat.training_protokoll import trainiere_protokolliert
from dss.arme.wp import lcoh_wp
from dss.arme.bio import lcoh_bio
from dss.arme.komposition import kompositionsfaktoren
from dss.surrogat.persistenz import speichere_modell, schreibe_manifest

SEED        = 42
N_TRAIN     = 20_000
N_VAL       = 5_000
N_TEST      = 5_000
S_TR, S_VA, S_TE = 1, 2, 3
ZIEL_LOG1P  = False
DEVICE      = "cpu"
VERSTECKT   = [16, 8, 4]        # E02-Sieger; je Netz identisch (Variante alpha)
AKTIV       = "gelu"


def _t(a: np.ndarray) -> torch.Tensor:
    return torch.tensor(a, dtype=torch.float32)



def _armziele(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ywp = np.empty(len(X)); ybio = np.empty(len(X))
    for i, zeile in enumerate(X):
        p = dict(zip(PARAM_NAMEN, zeile))
        ywp[i] = lcoh_wp(p)
        ybio[i] = lcoh_bio(p)
    return ywp, ybio


def _faktoren(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Analytische Kompositionsfaktoren (s, verlustfaktor, c_d) je Zeile."""
    s = np.empty(len(X)); vf = np.empty(len(X)); cd = np.empty(len(X))
    for i, zeile in enumerate(X):
        s[i], vf[i], cd[i] = kompositionsfaktoren(dict(zip(PARAM_NAMEN, zeile)))
    return s, vf, cd


def _trainiere_ziel(ytr, yva, Xtr_s, Xva_s, Xte_s, konfig):
    sy = Standardisierer(log1p=ZIEL_LOG1P).fit(ytr)
    prot = trainiere_protokolliert(
        VERSTECKT, AKTIV,
        Xtr_s, _t(sy.transform(ytr)), Xva_s, _t(sy.transform(yva)),
        konfig=konfig, device=DEVICE, early_stopping=True,
    )
    prot.modell.eval()
    with torch.no_grad():
        y_pred = sy.inverse(prot.modell(Xte_s).cpu().numpy())
    return np.asarray(y_pred).ravel(), prot.modell, prot.fit_sekunden, sy


def _infer_zeit_ms(modell, Xte_s, wiederholungen: int = 5) -> float:
    modell.eval()
    with torch.no_grad():
        t0 = time.perf_counter()
        for _ in range(wiederholungen):
            modell(Xte_s).cpu().numpy()
        return (time.perf_counter() - t0) / wiederholungen * 1e3


def _md(df: pd.DataFrame, zusatz: str) -> str:
    kopf = "| " + " | ".join(df.columns) + " |\n"
    trenn = "| " + " | ".join("---" for _ in df.columns) + " |\n"
    zeilen = "".join("| " + " | ".join(str(v) for v in row) + " |\n"
                     for row in df.itertuples(index=False))
    return ("# E05 - Architektur-Vergleich A (glatt): M vs. K\n\n"
            f"Referenz E01 (Seeds {S_TR}/{S_VA}/{S_TE}), Test Seed {S_TE}; "
            f"Topologie {VERSTECKT} - {AKTIV} je Netz (Variante alpha); "
            f"log1p={ZIEL_LOG1P}. Werte aus dem Lauf abgeleitet.\n\n"
            + kopf + trenn + zeilen + "\n" + zusatz)



def main(aus_dir: Path | None = None,
         n_train: int = N_TRAIN, n_val: int = N_VAL, n_test: int = N_TEST) -> None:
    import matplotlib.pyplot as plt
    from dss.reporting.stil import ThesisStil

    aus_dir = aus_dir or (Path(__file__).resolve().parent / "E05_architektur")
    aus_dir.mkdir(parents=True, exist_ok=True)
    setze_seed(SEED)
    print("Training...")

    Xtr, ytr = datensatz(n_train, S_TR)
    Xva, yva = datensatz(n_val, S_VA)
    Xte, yte = datensatz(n_test, S_TE)
    ywp_tr, ybio_tr = _armziele(Xtr)
    ywp_va, ybio_va = _armziele(Xva)
    ywp_te, ybio_te = _armziele(Xte)

    sx = Standardisierer().fit(Xtr)
    Xtr_s, Xva_s, Xte_s = _t(sx.transform(Xtr)), _t(sx.transform(Xva)), _t(sx.transform(Xte))
    konfig = Trainingskonfig()

    yM, modellM, fitM, syM = _trainiere_ziel(ytr, yva, Xtr_s, Xva_s, Xte_s, konfig)
    inferM = _infer_zeit_ms(modellM, Xte_s)

    ywp_hat, modellWP, fitWP, syWP = _trainiere_ziel(ywp_tr, ywp_va, Xtr_s, Xva_s, Xte_s, konfig)
    ybio_hat, modellBio, fitBio, syBio = _trainiere_ziel(ybio_tr, ybio_va, Xtr_s, Xva_s, Xte_s, konfig)
    t0 = time.perf_counter()
    s, vf, cd = _faktoren(Xte)                       # analytischer Teil von K
    yK = (s * ywp_hat + (1.0 - s) * ybio_hat) * vf + cd
    komp_ms = (time.perf_counter() - t0) * 1e3
    inferK = _infer_zeit_ms(modellWP, Xte_s) + _infer_zeit_ms(modellBio, Xte_s) + komp_ms

    _ordner = aus_dir / "modelle"
    _eintraege = []
    for _name, _mod, _sy, _ziel in [("M", modellM, syM, "m6.lcoh_m6"),
                                    ("wp", modellWP, syWP, "lcoh_wp"),
                                    ("bio", modellBio, syBio, "lcoh_bio")]:
        _p = speichere_modell(_ordner / f"e05_{_name}.pt", _mod, sx, _sy,
                              versteckt=VERSTECKT, aktiv=AKTIV, name=_name,
                              ziel=_ziel,
                              extra={"experiment": "E05", "seed": SEED,
                                     "seed_train": S_TR, "seed_val": S_VA,
                                     "seed_test": S_TE, "n_train": n_train,
                                     "n_val": n_val, "n_test": n_test,
                                     "ziel_log1p": ZIEL_LOG1P})
        _eintraege.append({"name": _name, "ziel": _ziel, "datei": _p.name})
    schreibe_manifest(_ordner, _eintraege, {
        "experiment": "E05 Architektur-Vergleich (glatt)",
        "versteckt": VERSTECKT, "aktiv": AKTIV, "device": DEVICE,
        "seeds": {"global": SEED, "train": S_TR, "val": S_VA, "test": S_TE},
        "n": {"train": n_train, "val": n_val, "test": n_test},
        "datensatz": "surrogat.daten.datensatz (m6.lhs_ensemble)",
        "hinweis": ("Die Netze standardisierte Eingaben. sx und sy "
                    "liegen in jeder .pt-Datei; Anfragen ueber "
                    "reports/frage_mlp.py."),
    })
    print(f"Modelle -> {_ordner}")

    mM, mK = metriken(yte, yM), metriken(yte, yK)
    mWP, mBio = metriken(ywp_te, ywp_hat), metriken(ybio_te, ybio_hat)
    pM, pWP, pBio = n_parameter(modellM), n_parameter(modellWP), n_parameter(modellBio)

    spalten = ["Architektur", "n_Param", "R2", "RMSE", "MAE", "MaxFehler",
               "P95_wahr", "P95_pred", "P95_Fehler", "Tail_MAE_oberes_Dezil",
               "Train_Zeit_s", "Infer_Zeit_ms"]
    def zeile(name, m, npar, fit, infer):
        return {"Architektur": name, "n_Param": npar,
                "R2": round(m["R2"], 6), "RMSE": round(m["RMSE"], 4),
                "MAE": round(m["MAE"], 4), "MaxFehler": round(m["MaxFehler"], 4),
                "P95_wahr": round(m["P95_wahr"], 3), "P95_pred": round(m["P95_pred"], 3),
                "P95_Fehler": round(m["P95_Fehler"], 4),
                "Tail_MAE_oberes_Dezil": round(m["Tail_MAE_oberes_Dezil"], 4),
                "Train_Zeit_s": round(fit, 2), "Infer_Zeit_ms": round(infer, 2)}
    tab = pd.DataFrame([
        zeile("M (Monolith)", mM, pM, fitM, inferM),
        zeile("K (WP+Bio)", mK, pWP + pBio, fitWP + fitBio, inferK),
    ], columns=spalten)

    e_wp, e_bio = ywp_te - ywp_hat, ybio_te - ybio_hat
    e_K_aus_armen = vf * (s * e_wp + (1.0 - s) * e_bio)
    e_K_direkt = yte - yK
    identitaet = float(np.max(np.abs(e_K_aus_armen - e_K_direkt)))
    rmse_wp, rmse_bio = float(np.sqrt(np.mean(e_wp**2))), float(np.sqrt(np.mean(e_bio**2)))

    zusatz = (
        "## Fehlerfortpflanzung\n\n"
        f"- Arm-RMSE: WP {rmse_wp:.4f} · Bio {rmse_bio:.4f} EUR/MWh "
        f"(R2 WP {mWP['R2']:.6f}, Bio {mBio['R2']:.6f}).\n"
        f"- Identitaetspruefung |(y-yK) - verlustfaktor*(s*e_WP+(1-s)*e_Bio)| "
        f"= {identitaet:.3e} EUR/MWh -> K-Fehler ist exakt der faktorgewichtete "
        "Arm-Fehler (Netzterm c_d exakt, traegt keinen Fehler).\n"
        f"- Verstaerkung: verlustfaktor 1/(1-v) im Test {vf.min():.3f}..{vf.max():.3f}.\n"
    )

    csv_pfad = aus_dir / "arch_vergleich_glatt.csv"
    tab.to_csv(csv_pfad, index=False)
    (aus_dir / "arch_vergleich_glatt.md").write_text(_md(tab, zusatz), encoding="utf-8")

    stil = ThesisStil(); stil.anwenden()
    fig, ax = stil.figur(breite=6.8, hoehe=4.4)
    ax.scatter(yte, np.abs(yte - yM), s=4, color=stil.neben, alpha=0.4,
               label="Monolith")
    ax.scatter(yte, np.abs(yte - yK), s=4, color=stil.haupt, alpha=0.4,
               label="Komposition")

    ax.set_yscale("log")
    ax.set_xlabel("Wärmegestehungskosten des Rechenkerns [EUR/MWh]",
                  fontsize=stil.schriftgroesse)
    ax.set_ylabel("Betrag der Abweichung [EUR/MWh]",
                  fontsize=stil.schriftgroesse)
    ax.legend(frameon=False, fontsize=stil.schriftgroesse - 1, loc="upper left")
    fig.tight_layout()
    for _e in ("pdf", "png"):
        fig.savefig(aus_dir / f"arch_vergleich_glatt_fehler.{_e}", dpi=300)

    print(tab.to_string(index=False))
    print("\n" + zusatz)
    print("fertig")


if __name__ == "__main__":
    main()
