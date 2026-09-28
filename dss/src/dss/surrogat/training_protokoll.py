from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

from dss.surrogat.modell import MLP
from dss.surrogat.training import Trainingskonfig


@dataclass
class Protokoll:
    modell: nn.Module
    versteckt: list[int]
    aktiv: str
    epochen: int
    beste_epoche: int
    fit_sekunden: float
    train_loss: list[float] = field(default_factory=list)
    val_loss: list[float] = field(default_factory=list)
    bester_val: float = math.inf


def trainiere_protokolliert(
    versteckt: list[int],
    aktiv: str,
    X_train: torch.Tensor,
    y_train: torch.Tensor,
    X_val: torch.Tensor,
    y_val: torch.Tensor,
    konfig: Trainingskonfig | None = None,
    device: str = "cpu",
    early_stopping: bool = True,
) -> Protokoll:
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
    beste_epoche = 0
    geduld = 0
    epochen = 0
    train_hist: list[float] = []
    val_hist: list[float] = []

    t0 = time.perf_counter()
    for ep in range(1, konfig.max_epochs + 1):
        modell.train()
        summe, n_batches = 0.0, 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            verlust = verlust_fn(modell(xb), yb)
            verlust.backward()
            opt.step()
            summe += verlust.item()
            n_batches += 1
        train_loss_ep = summe / max(n_batches, 1)

        modell.eval()
        with torch.no_grad():
            val = verlust_fn(modell(X_val_d), y_val_d).item()
        sched.step(val)
        epochen = ep
        train_hist.append(train_loss_ep)
        val_hist.append(val)

        if val < bester_val - konfig.min_delta:
            bester_val = val
            beste_gewichte = {k: v.detach().cpu().clone()
                              for k, v in modell.state_dict().items()}
            beste_epoche = ep
            geduld = 0
        else:
            geduld += 1
            if early_stopping and geduld >= konfig.patience:
                break
    fit_sekunden = time.perf_counter() - t0

    if beste_gewichte is not None:
        modell.load_state_dict(beste_gewichte)

    return Protokoll(
        modell=modell,
        versteckt=list(versteckt),
        aktiv=aktiv,
        epochen=epochen,
        beste_epoche=beste_epoche,
        fit_sekunden=fit_sekunden,
        train_loss=train_hist,
        val_loss=val_hist,
        bester_val=bester_val,
    )
