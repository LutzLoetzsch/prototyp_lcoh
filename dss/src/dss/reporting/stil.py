from __future__ import annotations

from dataclasses import dataclass

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure


@dataclass
class ThesisStil:
    skalierung: float = 1.0
    schriftgroesse: float = 9.0
    haupt: str = "0.1"
    neben: str = "0.55"
    flaeche: str = "0.75"

    def anwenden(self) -> None:
        mpl.rcParams.update({
            "figure.dpi": 120,
            "font.size": self.schriftgroesse,
            "axes.grid": True,
            "grid.color": "0.85",
            "grid.linewidth": 0.6,
            "axes.edgecolor": "0.3",
            "axes.linewidth": 0.8,
        })

    def figur(self, breite: float = 7.0, hoehe: float = 4.5) -> tuple[Figure, Axes]:
        self.anwenden()
        return plt.subplots(figsize=(breite * self.skalierung, hoehe * self.skalierung))

    def figur_raster(
        self, zeilen: int, spalten: int, breite: float = 13.0, hoehe: float = 6.5
    ) -> tuple[Figure, "list[Axes]"]:
        self.anwenden()
        fig, achsen = plt.subplots(
            zeilen, spalten,
            figsize=(breite * self.skalierung, hoehe * self.skalierung),
        )
        return fig, achsen
