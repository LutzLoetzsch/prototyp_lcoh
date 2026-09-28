"""MLP-Surrogat fuer die LCOH-Funktion.

Surrogat (Metamodell i. S. v. Davis et al. 2007) der bekannten, aber fuer
massiv-wiederholte Auswertung zu teuren LCOH-Funktion. Theoretischer Rahmen:
universelle Approximation (Hornik, Stinchcombe, White 1989, Thm 2.1). Der exakte
Generator (`dss.szenarien.m6`) bleibt fuer die finale Bewertung erhalten.
"""

from dss.surrogat.daten import PARAM_NAMEN, Standardisierer, datensatz
from dss.surrogat.metriken import metriken
from dss.surrogat.modell import MLP, aktivierung, n_parameter
from dss.surrogat.topologien import AKTIVIERUNGEN, TOPOLOGIEN
from dss.surrogat.training import Trainingskonfig, setze_seed, trainiere

__all__ = [
    "PARAM_NAMEN",
    "Standardisierer",
    "datensatz",
    "metriken",
    "MLP",
    "aktivierung",
    "n_parameter",
    "AKTIVIERUNGEN",
    "TOPOLOGIEN",
    "Trainingskonfig",
    "setze_seed",
    "trainiere",
]
