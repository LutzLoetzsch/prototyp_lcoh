#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask

W_KONSTANTE = 61.8
W_EXPONENT = -0.15
E_SCHWELLE = 0.15
ZELLE_M2 = 10_000.0

ETA_STANDARD = 0.87
HOTMAPS_BEZUGSJAHR = 2015


def gemeinde_umriss(shapefile: Path, name: str | None,
                    ags: str | None) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(shapefile)

    if "GF" in gdf.columns:
        gdf = gdf[gdf["GF"] == 4]

    if ags:
        treffer = gdf[gdf["AGS"].astype(str).str.zfill(8) == str(ags).zfill(8)]
        gesucht = f"AGS {ags}"
    else:
        feld = "GEN" if "GEN" in gdf.columns else gdf.columns[0]
        treffer = gdf[gdf[feld].astype(str)
                      .str.contains(name, case=False, na=False)]
        gesucht = f"'{name}' in Spalte {feld}"

    if treffer.empty:
        raise SystemExit(f"{gesucht} nicht gefunden. Spalten: {list(gdf.columns)}")

    return treffer.to_crs(3035)


def lies_fenster(tif: Path, geometrien) -> np.ndarray:
    # Gesamtraster nicht vollständig einlesen
    with rasterio.open(tif) as src:
        if src.crs.to_epsg() != 3035:
            raise SystemExit(f"{tif.name}: EPSG {src.crs.to_epsg()}, erwartet 3035")
        daten, _ = mask(src, geometrien, crop=True, filled=True, nodata=0.0)
    return daten[0].astype("float64")


def finde_tif(ordner: Path) -> Path:
    treffer = sorted(ordner.rglob("*.tif"))
    if not treffer:
        raise SystemExit(f"kein .tif unter {ordner}")
    return treffer[0]


def rechne(d_mwh_ha: np.ndarray, gfa_m2_ha: np.ndarray, schwelle: float) -> dict:
    if d_mwh_ha.shape != gfa_m2_ha.shape:
        raise SystemExit(f"Rasterfenster ungleich: {d_mwh_ha.shape} vs {gfa_m2_ha.shape}")

    e = gfa_m2_ha / ZELLE_M2
    qualifiziert = (e >= schwelle) & (d_mwh_ha > 0.0)

    if not qualifiziert.any():
        hoechstes_e = float(e.max()) if e.size else 0.0
        raise SystemExit(
            f"Keine Zelle erreicht e >= {schwelle} (höchstes e im Gebiet: "
            f"{hoechstes_e:.3f}). Gebiet zu dünn besiedelt, Schwelle zu hoch "
            f"oder Umriss falsch.")

    e_q = e[qualifiziert]
    d_q = d_mwh_ha[qualifiziert]
    w = W_KONSTANTE * e_q ** W_EXPONENT
    laenge = ZELLE_M2 / w

    return {
        "zellen_gesamt": int((d_mwh_ha > 0).sum()),
        "zellen_qualifiziert": int(qualifiziert.sum()),
        "d_mittel": float(d_q.mean()),
        "d_gesamtgebiet": float(d_mwh_ha.sum()),
        "e_mittel": float(e_q.mean()),
        "e_max": float(e.max()),
        "w_mittel": float(w.mean()),
        "trassenlaenge_m": float(laenge.sum()),
        "waerme_roh": float(d_q.sum()),
    }


def korrigiere(waerme_roh: float, eta: float,
               rate: float | None, jahre: int) -> dict:
    schritte = [("Rohwert Hotmaps (Endenergie, 2015)", 1.0, waerme_roh)]
    wert = waerme_roh

    wert *= eta
    schritte.append((f"K1 Endenergie -> Nutzwärme (eta = {eta})", eta, wert))

    if rate is not None:
        faktor = (1.0 + rate) ** jahre
        wert *= faktor
        schritte.append(
            (f"K2 Bezugsjahr {HOTMAPS_BEZUGSJAHR} + {jahre} a (r = {rate})",
             faktor, wert))

    return {"wert": wert, "schritte": schritte,
            "faktor_gesamt": wert / waerme_roh if waerme_roh else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemeinde", help="Namensteil, Spalte GEN")
    ap.add_argument("--ags", help="Amtlicher Gemeindeschlüssel, eindeutig")
    ap.add_argument("--shapefile", required=True, type=Path)
    ap.add_argument("--daten", required=True, type=Path,
                    help="Ordner mit heat_tot_curr_density/ und gfa_tot_curr_density/")
    ap.add_argument("--schwelle", type=float, default=E_SCHWELLE,
                    help="plot-ratio-Schwelle; P&W S. 574 nennt 0,15..0,20")
    ap.add_argument("--eta", type=float, default=ETA_STANDARD,
                    help=f"K1 Nutzungsgrad Bestandsanlage (Standard {ETA_STANDARD})")
    ap.add_argument("--rate", type=float, default=None,
                    help="K2 Bedarfsrate p.a. nur bei monotoner Trajektorie")
    ap.add_argument("--jahre", type=int, default=11,
                    help=f"K2 Jahre ab {HOTMAPS_BEZUGSJAHR} (Standard 11 -> 2026)")
    a = ap.parse_args()

    if not (a.gemeinde or a.ags):
        raise SystemExit("--gemeinde oder --ags angeben")

    umriss = gemeinde_umriss(a.shapefile, a.gemeinde, a.ags)
    geom = list(umriss.geometry)

    heat = finde_tif(a.daten / "heat_tot_curr_density")
    gfa = finde_tif(a.daten / "gfa_tot_curr_density")

    r = rechne(lies_fenster(heat, geom), lies_fenster(gfa, geom), a.schwelle)
    k = korrigiere(r["waerme_roh"], a.eta, a.rate, a.jahre)

    trasse = round(r["trassenlaenge_m"], 1)
    waerme_korr = round(k["wert"], 1)

    print(f"trassenlaenge_m={trasse} waermelieferung_mwh_a={waerme_korr}")


if __name__ == "__main__":
    main()
