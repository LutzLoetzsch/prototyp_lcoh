from __future__ import annotations

import torch.nn as nn

_AKTIVIERUNGEN = {
    "tanh": nn.Tanh,
    "gelu": nn.GELU,
    "relu": nn.ReLU,
}


def aktivierung(name: str) -> nn.Module:
    if name not in _AKTIVIERUNGEN:
        raise ValueError(f"Unbekannte Aktivierung: {name!r}. "
                         f"Erlaubt: {sorted(_AKTIVIERUNGEN)}")
    return _AKTIVIERUNGEN[name]()


class MLP(nn.Module):
    def __init__(self, n_eingang: int, versteckt: list[int], aktiv: str = "tanh") -> None:
        super().__init__()
        schichten: list[nn.Module] = []
        davor = n_eingang
        for breite in versteckt:
            schichten.append(nn.Linear(davor, breite))
            schichten.append(aktivierung(aktiv))
            davor = breite
        schichten.append(nn.Linear(davor, 1))
        self.netz = nn.Sequential(*schichten)

    def forward(self, x):
        return self.netz(x).squeeze(-1)


def n_parameter(modell: nn.Module) -> int:
    return sum(p.numel() for p in modell.parameters() if p.requires_grad)
