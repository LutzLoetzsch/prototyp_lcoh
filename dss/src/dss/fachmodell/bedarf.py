from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    name: str
    reihe: tuple[float, ...]

    @classmethod
    def geometrisch(cls, name: str, anfangsmenge: float, rate: float,
                    T: int, start_jahr: int = 1) -> "Segment":
        if anfangsmenge < 0:
            raise ValueError("anfangsmenge darf nicht negativ sein")
        if T <= 0:
            raise ValueError("T muss positiv sein")
        if start_jahr < 1:
            raise ValueError("start_jahr muss >= 1 sein")
        werte = []
        for jahr in range(1, T + 1):
            if jahr < start_jahr:
                werte.append(0.0)
            else:
                werte.append(anfangsmenge * (1.0 + rate) ** (jahr - start_jahr))
        return cls(name, tuple(werte))

    @classmethod
    def aus_reihe(cls, name: str, reihe) -> "Segment":
        werte = tuple(float(x) for x in reihe)
        if any(x < 0 for x in werte):
            raise ValueError("Bedarfswerte dürfen nicht negativ sein")
        if len(werte) == 0:
            raise ValueError("Reihe darf nicht leer sein")
        return cls(name, werte)


@dataclass(frozen=True)
class Bedarfstrajektorie:
    T: int
    segmente: tuple[Segment, ...] = field(default_factory=tuple)

    def __post_init__(self):
        for s in self.segmente:
            if len(s.reihe) != self.T:
                raise ValueError(
                    f"Segment '{s.name}' hat Länge {len(s.reihe)}, erwartet {self.T}"
                )

    def reihe(self) -> list[float]:
        return [sum(s.reihe[t] for s in self.segmente) for t in range(self.T)]

    def q0(self) -> float:
        return self.reihe()[0]
