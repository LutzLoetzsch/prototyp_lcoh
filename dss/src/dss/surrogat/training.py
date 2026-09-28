from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from dss.surrogat.modell import MLP


@dataclass
class Trainingskonfig:
    lr: float = 1e-3
    batch_size: int = 512
    max_epochs: int = 1000
    patience: int = 25
    min_delta: float = 1e-5
    lr_factor: float = 0.5
    lr_patience: int = 8


def setze_seed(seed: int) -> None:
    import numpy as np
    np.random.seed(seed)
    torch.manual_seed(seed)


def trainiere(
    versteckt: list[int],
    aktiv: str,
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    konfig: Trainingskonfig | None = None,
    device: str = "cpu",
) -> tuple[nn.Module, int]:
    konfig = konfig or Trainingskonfig()
    loader = DataLoader(
        TensorDataset(X_train, y_train),
        batch_size=konfig.batch_size,
        shuffle=True,
    )

    modell = MLP(X_train.shape[1], versteckt, aktiv).to(device)
    opt = torch.optim.Adam(modell.parameters(), lr=konfig.lr)
    sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
        opt, factor=konfig.lr_factor, patience=konfig.lr_patience
    )
    verlust_fn = nn.MSELoss()

    X_val_d, y_val_d = X_val.to(device), y_val.to(device)
    bester_val = math.inf
    beste_gewichte = None
    geduld = 0
    epochen = 0

    for ep in range(1, konfig.max_epochs + 1):
        modell.train()
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            verlust_fn(modell(xb), yb).backward()
            opt.step()

        modell.eval()
        with torch.no_grad():
            val = verlust_fn(modell(X_val_d), y_val_d).item()
        sched.step(val)
        epochen = ep

        if val < bester_val - konfig.min_delta:
            bester_val = val
            beste_gewichte = {k: v.detach().cpu().clone()
                              for k, v in modell.state_dict().items()}
            geduld = 0
        else:
            geduld += 1
            if geduld >= konfig.patience:
                break

    if beste_gewichte is not None:
        modell.load_state_dict(beste_gewichte)
    return modell, epochen
