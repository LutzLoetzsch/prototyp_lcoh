#!/usr/bin/env python3
"""Monochromer Thesis-Stil (Konvention Uebergabe-Notiz 2026-06-07, Sec. 6):
monochrom/grau, SKALIERUNG=0.5. Unterscheidung ueber Grauton + Linienstil +
Marker (Linien) bzw. Grauton + Schraffur (Balken) -- keine Farbe."""
import matplotlib as mpl
import matplotlib.pyplot as plt

SKALIERUNG = 0.5

def setze_stil():
    mpl.rcParams.update({
        "font.family": "serif", "font.size": 10, "axes.titlesize": 10.5,
        "axes.labelsize": 10, "figure.dpi": 120, "savefig.dpi": 300,
        "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5, "grid.color": "0.6",
        "axes.spines.top": False, "axes.spines.right": False,
        "legend.frameon": False, "figure.autolayout": True,
        "axes.edgecolor": "0.2", "image.cmap": "gray",
        "axes.prop_cycle": mpl.cycler(color=["0.0", "0.4", "0.6", "0.8"]),
    })

# monochrome Linienstile (Grauton, Linienstil, Marker)
LINIEN = [("0.0", "-", "o"), ("0.35", "--", "s"), ("0.55", "-.", "^"),
          ("0.7", ":", "D"), ("0.45", "-", "v")]
# monochrome Balkenfuellungen (Grauton, Schraffur)
BALKEN = [("0.75", ""), ("0.5", "///"), ("0.25", "xxx"), ("white", "...")]

def speichere(fig, pfad, herkunft=""):
    import pathlib
    pathlib.Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    if herkunft:
        fig.text(0.99, 0.01, herkunft, ha="right", va="bottom", fontsize=6, color="0.5")
    fig.savefig(pfad + ".pdf"); fig.savefig(pfad + ".png"); plt.close(fig)
