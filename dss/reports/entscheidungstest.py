#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch

from dss.surrogat import Standardisierer, Trainingskonfig, metriken, setze_seed
from dss.surrogat.training_protokoll import trainiere_protokolliert
from dss.surrogat.daten import PARAM_NAMEN
from dss.arme.wp import lcoh_wp
from dss.arme.bio import lcoh_bio
from dss.arme.komposition import kompositionsfaktoren
from dss.entscheidung.ziel_knick import lcoh_dez
from dss.entscheidung.daten_knick import datensatz_knick
from dss.reporting.stil import ThesisStil
from dss.surrogat.persistenz import speichere_modell, schreibe_manifest

SEED        = 42
N_TRAIN     = 20_000
N_VAL       = 5_000
N_TEST      = 5_000
SEED_TRAIN, SEED_VAL, SEED_TEST = 1, 2, 3
ZIEL_LOG1P  = False
DEVICE      = "cpu"
VERSTECKT   = [16, 8, 4]
AKTIV       = "gelu"
KNICK_BAND  = 5.0


def _t(a):
    return torch.tensor(a, dtype=torch.float32)


def _armziele(X):
    wp = np.empty(len(X)); bio = np.empty(len(X))
    for i, z in enumerate(X):
        p = dict(zip(PARAM_NAMEN, z))
        wp[i] = lcoh_wp(p); bio[i] = lcoh_bio(p)
    return wp, bio


def _dezziele(X):
    d = np.empty(len(X))
    for i, z in enumerate(X):
        d[i] = lcoh_dez(dict(zip(PARAM_NAMEN, z)))
    return d


def _faktoren(X):
    s = np.empty(len(X)); vf = np.empty(len(X)); cd = np.empty(len(X))
    for i, z in enumerate(X):
        s[i], vf[i], cd[i] = kompositionsfaktoren(dict(zip(PARAM_NAMEN, z)))
    return s, vf, cd


def _trainiere(ytr, yva, Xtr_s, Xva_s, Xte_s, konfig):
    sy = Standardisierer(log1p=ZIEL_LOG1P).fit(ytr)
    prot = trainiere_protokolliert(
        VERSTECKT, AKTIV, Xtr_s, _t(sy.transform(ytr)), Xva_s, _t(sy.transform(yva)),
        konfig=konfig, device=DEVICE, early_stopping=True,
    )
    prot.modell.eval()
    with torch.no_grad():
        y = sy.inverse(prot.modell(Xte_s).cpu().numpy())
    return np.asarray(y).ravel(), prot.modell, sy


def _speichere_alle(aus_dir, sx, modelle, n_train, n_val, n_test):
    ordner = Path(aus_dir) / "modelle"
    eintraege = []
    for name, modell, sy, ziel in modelle:
        pfad = speichere_modell(
            ordner / f"e07_{name}.pt", modell, sx, sy,
            versteckt=VERSTECKT, aktiv=AKTIV, name=name, ziel=ziel,
            extra={"experiment": "E07", "seed": SEED,
                   "seed_train": SEED_TRAIN, "seed_val": SEED_VAL,
                   "seed_test": SEED_TEST, "n_train": n_train,
                   "n_val": n_val, "n_test": n_test,
                   "ziel_log1p": ZIEL_LOG1P, "knick_band": KNICK_BAND})
        eintraege.append({"name": name, "ziel": ziel, "datei": pfad.name})
    manifest = schreibe_manifest(ordner, eintraege, {
        "experiment": "E07 Entscheidungstest",
        "versteckt": VERSTECKT, "aktiv": AKTIV, "device": DEVICE,
        "seeds": {"global": SEED, "train": SEED_TRAIN,
                  "val": SEED_VAL, "test": SEED_TEST},
        "n": {"train": n_train, "val": n_val, "test": n_test},
        "datensatz": "datensatz_knick(gamma=1.0)",
        "hinweis": ("Die Netze erwarten standardisierte Eingaben. sx und sy "
                    "liegen in jeder .pt-Datei; Anfragen über "
                    "reports/frage_mlp.py."),
    })
    return manifest


def _md_tabelle(df):
    kopf = "| " + " | ".join(df.columns) + " |"
    trenn = "| " + " | ".join("---" for _ in df.columns) + " |"
    zeilen = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([kopf, trenn, *zeilen])


def laufe(n_train=N_TRAIN, n_val=N_VAL, n_test=N_TEST, konfig=None,
          aus_dir: Path | None = None):
    konfig = konfig or Trainingskonfig()
    aus_dir = aus_dir or (Path(__file__).resolve().parent / "E07_entscheidung")
    aus_dir.mkdir(parents=True, exist_ok=True)
    stil = ThesisStil()
    setze_seed(SEED)

    Xtr, ytr, _, _ = datensatz_knick(n_train, SEED_TRAIN, gamma=1.0)
    Xva, yva, _, _ = datensatz_knick(n_val,   SEED_VAL,   gamma=1.0)
    Xte, yte, netz, dez = datensatz_knick(n_test, SEED_TEST, gamma=1.0)

    sx = Standardisierer().fit(Xtr)
    Xtr_s, Xva_s, Xte_s = _t(sx.transform(Xtr)), _t(sx.transform(Xva)), _t(sx.transform(Xte)).to(DEVICE)

    yM, modellM, syM = _trainiere(ytr, yva, Xtr_s, Xva_s, Xte_s, konfig)

    wp_tr, bio_tr = _armziele(Xtr); wp_va, bio_va = _armziele(Xva)
    dez_tr, dez_va = _dezziele(Xtr), _dezziele(Xva)
    wp_hat, modellWP, syWP = _trainiere(wp_tr, wp_va, Xtr_s, Xva_s, Xte_s, konfig)
    bio_hat, modellBio, syBio = _trainiere(bio_tr, bio_va, Xtr_s, Xva_s, Xte_s, konfig)
    dez_hat, modellDez, syDez = _trainiere(dez_tr, dez_va, Xtr_s, Xva_s, Xte_s, konfig)

    _speichere_alle(aus_dir, sx,
                    [("M", modellM, syM, "min(lcoh_netz, lcoh_dez)"),
                     ("wp", modellWP, syWP, "lcoh_wp"),
                     ("bio", modellBio, syBio, "lcoh_bio"),
                     ("dez", modellDez, syDez, "lcoh_dez")],
                    n_train, n_val, n_test)

    s, vf, cd = _faktoren(Xte)
    netz_hat = vf * (s * wp_hat + (1.0 - s) * bio_hat) + cd
    yK = np.minimum(netz_hat, dez_hat)

    argmin_true = netz < dez
    argmin_K = netz_hat < dez_hat
    abst_true = np.abs(netz - dez)
    abst_K = np.abs(netz_hat - dez_hat)
    band = abst_true < KNICK_BAND
    treffer = (argmin_K == argmin_true)
    fehl = ~treffer

    quote = treffer.mean()
    quote_band = treffer[band].mean() if band.any() else float("nan")
    quote_aus = treffer[~band].mean() if (~band).any() else float("nan")
    abst_mae = float(np.mean(np.abs(abst_K - abst_true)))
    kosten = abst_true[fehl]

    rmseM = metriken(yte, yM)["RMSE"]; rmseK = metriken(yte, yK)["RMSE"]

    tab = pd.DataFrame([
        {"Architektur": "M (Monolith)", "Wert_RMSE": round(rmseM, 4),
         "Sieger_argmin": "nicht verfügbar", "Abstand": "nicht verfügbar",
         "Ausgabe_zerlegbar": "nein"},
        {"Architektur": "K (komponierbar)", "Wert_RMSE": round(rmseK, 4),
         "Sieger_argmin": f"Trefferquote {quote*100:.2f} %",
         "Abstand": f"MAE {abst_mae:.4f}", "Ausgabe_zerlegbar": "ja"},
    ])

    fig, ax = stil.figur()
    ax.scatter(abst_true[treffer], abst_K[treffer], s=5, c=stil.neben,
               linewidths=0, label="K korrekt")
    ax.scatter(abst_true[fehl], abst_K[fehl], s=14, c=stil.haupt,
               linewidths=0, label="K falsch")
    lim = float(np.percentile(abst_true, 99))
    ax.plot([0, lim], [0, lim], ":", color="0.4", linewidth=1.0)
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_xlabel("wahrer Abstand |netz − dez| (EUR/MWh)")
    ax.set_ylabel("K-Abstand |netz_hat − dez_hat| (EUR/MWh)")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(aus_dir / "entscheidung_abstand.png", dpi=150)

    csv_pfad = aus_dir / "entscheidungstest.csv"
    md_pfad = aus_dir / "entscheidungstest.md"
    tab.to_csv(csv_pfad, index=False)
    md = (
        "# E07 - Entscheidungstest: Fähigkeitsvergleich M vs. K\n\n"
        f"Ziel min(netz, dez), n={n_train}/{n_val}/{n_test}, Seeds "
        f"{SEED_TRAIN}/{SEED_VAL}/{SEED_TEST}, ehrliche LHS; M und Arme {VERSTECKT}·{AKTIV}. "
        "Kein Genauigkeitsrennen, sondern Test der Entscheidungsfähigkeit. "
        "Werte aus dem Lauf abgeleitet.\n\n"
        + _md_tabelle(tab) + "\n\n"
        "## K-Entscheidungsgüte\n\n"
        f"- argmin-Trefferquote: global {quote*100:.2f} %, im Knickband "
        f"(|netz−dez|<{KNICK_BAND}) {quote_band*100:.2f} %, außerhalb {quote_aus*100:.2f} %.\n"
        f"- Abstand-MAE: {abst_mae:.4f} EUR/MWh.\n"
        f"- Fehlentscheidungen: {int(fehl.sum())} von {len(yte)} ({fehl.mean()*100:.2f} %); "
        f"deren wahrer Abstand Median {np.median(kosten):.3f}, Max {kosten.max():.3f} EUR/MWh "
        "= ökonomische Kosten der Fehlwahl (Entscheidung dort ohnehin indifferent).\n"
        f"- M: Sieger und Abstand sind strukturell nicht verfügbar -- das min verwirft den "
        "Verlierer; M gibt nur den Wert aus.\n"
    )
    md_pfad.write_text(md, encoding="utf-8")
    print(f"Gespeichert: {aus_dir}")
    return tab


if __name__ == "__main__":
    laufe()
