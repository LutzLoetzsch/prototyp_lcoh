from __future__ import annotations

TOPOLOGIEN: dict[str, list[int]] = {
    "betreuer_18-9-4":       [18, 9, 4],
    "expand_taper_32-16-8":  [32, 16, 8],
    "enger_engpass_18-12-8": [18, 12, 8],
    "flach_32":              [32],
    "flach_64":              [64],
    "flach_128":             [128],
    "tief_64-64":            [64, 64],
    "tief_128-64":           [128, 64],
    "tief_64-64-64":         [64, 64, 64],
    "tief_128-128-64":       [128, 128, 64],
}

AKTIVIERUNGEN: list[str] = ["tanh", "gelu"]
