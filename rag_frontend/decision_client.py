from __future__ import annotations

import json
import os
import subprocess

from config import DSS_REPO, DSS_PYTHON


def _lauf(args: list[str], eingabe: str | None = None) -> str:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(
        [DSS_PYTHON, "-m", "dss.cli_entscheidung", *args],
        input=eingabe, text=True, capture_output=True,
        cwd=str(DSS_REPO), env=env, timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Entscheidungs-CLI Fehler (rc={proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def entscheide(params: dict, modus: str | None = None) -> dict:
    args = ["--modus", modus] if modus else []
    return json.loads(_lauf(args, eingabe=json.dumps(params)))


def schema() -> dict:
    return json.loads(_lauf(["--schema"]))
