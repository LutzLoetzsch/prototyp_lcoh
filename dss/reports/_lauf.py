from __future__ import annotations

from pathlib import Path

LAUF = "Experimentierlauf_Wuensdorf"
KLARNAME = "Experimentierlauf Wünsdorf"


def reports(*teile: str) -> str:
    """Pfad unterhalb von reports/<LAUF>/ ."""
    return str(Path("reports") / LAUF / Path(*teile))


def figures(*teile: str) -> str:
    """Pfad unterhalb von figures/<LAUF>/ ."""
    return str(Path("figures") / LAUF / Path(*teile))


def daten(*teile: str) -> str:
    """Pfad unterhalb von daten/<LAUF>/ ."""
    return str(Path("daten") / LAUF / Path(*teile))
