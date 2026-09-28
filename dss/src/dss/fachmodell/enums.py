from __future__ import annotations

from enum import Enum

class Brennstoffart(Enum):
    HOLZPELLET = "Holzpellet"
    HOLZHACKSCHNITZEL = "Holzhackschnitzel"
    STROH = "Stroh"
    BIOGAS = "Biogas"
    ERDGAS = "Erdgas"


class Waermequelle(Enum):
    LUFT = "Luft"
    GRUNDWASSER = "Grundwasser"
    ERDWAERMESONDE = "Erdwaermesonde"
    ABWAERME = "Abwaerme"
    GEWAESSER = "Gewaesser"
    KLAERWASSER = "Klaerwasser"
    GRUBENWASSER = "Grubenwasser"


class Groessenklasse(Enum):
    DEZENTRAL = "dezentral"
    NETZGEBUNDEN = "netzgebunden"


class Netztyp(Enum):
    FERNWAERME = "Fernwaerme"
    NAHWAERME = "Nahwaerme"
    NIEDERTEMPERATUR = "Niedertemperatur"
    KALTE_NAHWAERME = "KalteNahwaerme"
