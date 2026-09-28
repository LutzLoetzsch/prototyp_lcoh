#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

sys.path.insert(0, "rag")
import profil_chunks                              # noqa: E402
import fachwissen                                 # noqa: E402

import profil                                     # noqa: E402
from llm_client import extrahiere                 # noqa: E402
from decision_client import entscheide, schema    # noqa: E402
from antwort import erzeuge_antwort               # noqa: E402
from prompt import PARAMETER                      # noqa: E402
from zahlen import lcoh_befund, de, zahlen_kandidaten   # noqa: E402
import darstellung                                      # noqa: E402

PROMPT_SET = "rag/prompt_set_d.yaml"
SZENARIO_FELDER = {"grundlast_anteil", "co2_preis"}

STUFEN = {
    "V0": {"art": "aufwand", "kontext": None,
           "kurz": "Prototyp, Eingabe von Hand",
           "lang": "DSS-Prototyp, Parametersatz von Hand (kein Sprachmodell)"},
    "LX": {"art": "allein", "kontext": None,
           "kurz": "{modell} allein, ohne DSS",
           "lang": "{modell} (lokal), ohne DSS, ohne Datenanbindung"},
    "V1": {"art": "lokal", "kontext": "keiner",
           "kurz": "Prototyp + {modell}, ohne Daten",
           "lang": "DSS-Prototyp mit {modell} (lokal), ohne Datenanbindung"},
    "V2": {"art": "lokal", "kontext": "voll",
           "kurz": "Prototyp + {modell}, Vollkontext",
           "lang": "DSS-Prototyp mit {modell} (lokal), vollständige Wissensbasis"},
    "V3": {"art": "lokal", "kontext": "retrieval",
           "kurz": "Prototyp + {modell}, Retrieval",
           "lang": "DSS-Prototyp mit {modell} (lokal), Retrieval aus der Wissensbasis"},
    "VX-A-S0": {"art": "extern", "anbieter": "anthropic", "modell": "S", "suche": False,
                "kurz": "Claude Sonnet 5",
                "lang": "Claude Sonnet 5 (API), ohne DSS, ohne Websuche"},
    "VX-A-S1": {"art": "extern", "anbieter": "anthropic", "modell": "S", "suche": True,
                "kurz": "Claude Sonnet 5 + Websuche",
                "lang": "Claude Sonnet 5 (API), ohne DSS, mit Websuche"},
    "VX-A-O0": {"art": "extern", "anbieter": "anthropic", "modell": "O", "suche": False,
                "kurz": "Claude Opus 5",
                "lang": "Claude Opus 5 (API), ohne DSS, ohne Websuche"},
    "VX-A-O1": {"art": "extern", "anbieter": "anthropic", "modell": "O", "suche": True,
                "kurz": "Claude Opus 5 + Websuche",
                "lang": "Claude Opus 5 (API), ohne DSS, mit Websuche"},
    "VX-G-T0": {"art": "extern", "anbieter": "openai", "modell": "T", "suche": False,
                "kurz": "GPT-5.6 Terra",
                "lang": "GPT-5.6 Terra (API), ohne DSS, ohne Websuche"},
    "VX-G-T1": {"art": "extern", "anbieter": "openai", "modell": "T", "suche": True,
                "kurz": "GPT-5.6 Terra + Websuche",
                "lang": "GPT-5.6 Terra (API), ohne DSS, mit Websuche"},
    "VX-G-S0": {"art": "extern", "anbieter": "openai", "modell": "S", "suche": False,
                "kurz": "GPT-5.6 Sol",
                "lang": "GPT-5.6 Sol (API), ohne DSS, ohne Websuche"},
    "VX-G-S1": {"art": "extern", "anbieter": "openai", "modell": "S", "suche": True,
                "kurz": "GPT-5.6 Sol + Websuche",
                "lang": "GPT-5.6 Sol (API), ohne DSS, mit Websuche"},
}


def _lokales_modell() -> str:
    try:
        from config import LLM
        roh = str(LLM.get("model", "")).strip()
    except Exception:
        return "lokalem Sprachmodell"
    if not roh:
        return "lokalem Sprachmodell"
    if ":" in roh:
        name, groesse = roh.split(":", 1)
        name = name.replace("-", " ").strip().title()
        return f"{name} ({groesse.upper()})"
    return roh


def bezeichnung(kennung: str, lang: bool = False) -> str:
    d = STUFEN[kennung]
    text = d["lang"] if lang else d["kurz"]
    return text.replace("{modell}", _lokales_modell())


STANDARD_STUFEN = ["LX", "V1", "V2", "V3",
                   "VX-A-S0", "VX-A-S1", "VX-A-O0", "VX-A-O1"]


def lade_referenzszenario(spec: dict) -> tuple[str, dict]:
    schluessel = spec.get("referenzszenario")
    datei = spec.get("szenarien_datei", "wissensbasis/szenarien.yaml")
    alle = yaml.safe_load(open(datei, encoding="utf-8"))
    if schluessel not in alle:
        raise SystemExit(f"Szenario {schluessel!r} nicht in {datei}")
    return schluessel, {k: float(v) for k, v in alle[schluessel].items()
                        if k in SZENARIO_FELDER}


def wahrheit(profil_pfad: str, szenario: dict) -> dict:
    prof = profil.lade_profil(profil_pfad)
    params, _ = profil.assembliere_parametersatz(prof, szenario)
    a = entscheide(params)
    return {"params": params, "ergebnis": a["ergebnis"],
            "angenommen": a.get("angenommen", []) or []}


def vollkontext(profil_pfad: str) -> str:
    prof = profil.lade_profil(profil_pfad)
    chunks = profil_chunks.chunk_profil(prof, kommune_modus="voll", mit_status=True)
    chunks += fachwissen.lade_technikkatalog()
    return "\n\n".join(c["text"] for c in chunks)


def v0_eingabeaufwand() -> dict:
    s = schema()
    return {"parameter_gesamt": s["anzahl"], "davon_gesampelt": s["davon_gesampelt"],
            "einheiten_zu_kennen": s["anzahl"],
            "baender_zu_kennen": sum(1 for v in s["parameter"].values()
                                     if v.get("min") is not None),
            "eingabeformat": "JSON auf stdin"}


def durchgang_lokal(frage: str, stufe: str, profil_pfad: str, szenario: dict,
                    retriever=None, k: int = 3,
                    modus: str | None = None) -> dict:
    art = STUFEN[stufe]["kontext"]
    z = {"retrieval_s": None, "kontext_zeichen": 0, "chunk_ids": []}

    if art == "keiner":
        kontext = None
    elif art == "voll":
        kontext = vollkontext(profil_pfad)
        z["kontext_zeichen"] = len(kontext)
    else:
        t = retriever.suche(frage, k)
        kontext = t["kontext"]
        z = {"retrieval_s": t["retrieval_s"], "kontext_zeichen": t["kontext_zeichen"],
             "chunk_ids": list(t["chunk_ids"])}

    fehler = None
    satz, ergebnis, angenommen, text = {}, {}, [], ""
    t_ex = t_ant = None
    t0 = time.perf_counter()
    try:
        a0 = time.perf_counter()
        p = extrahiere(frage, kontext)
        satz = p.als_eingabe()
        t_ex = round(time.perf_counter() - a0, 2)

        a1 = time.perf_counter()
        roh = entscheide({**satz, **szenario}, modus)
        ergebnis = roh.get("ergebnis", {})
        if roh.get("zerlegung"):
            ergebnis = {**ergebnis, "zerlegung": roh["zerlegung"]}
            if roh.get("modellherkunft"):
                ergebnis["modellherkunft"] = roh["modellherkunft"]
        angenommen = roh.get("angenommen", []) or []
        t_vertrag = round(time.perf_counter() - a1, 2)

        a2 = time.perf_counter()
        text = erzeuge_antwort(frage, kontext, ergebnis, satz, angenommen)
        t_ant = round(time.perf_counter() - a2, 2)
    except Exception as e:
        fehler = f"{type(e).__name__}: {e}"
        t_vertrag = None

    return {"stufe": stufe, "art": "lokal", "frage": frage, "kontext": kontext,
            "extrahiert": satz, "ergebnis": ergebnis, "angenommen": angenommen,
            "antwort": text, "fehler": fehler,
            "kontext_zeichen": z["kontext_zeichen"],
            "kontext_token_grob": z["kontext_zeichen"] // 4,
            "chunk_ids": z["chunk_ids"], "suchanfragen": [], "anzahl_suchen": 0,
            "verbrauch": {},
            "zeiten": {"retrieval_s": z["retrieval_s"], "extraktion_s": t_ex,
                       "vertrag_s": t_vertrag, "antwort_s": t_ant},
            "latenz_s": round(time.perf_counter() - t0, 2),
            "zeit": datetime.now().isoformat(timespec="seconds")}


def durchgang_allein(frage: str, stufe: str) -> dict:
    from antwort_allein import erzeuge_antwort_allein

    t0 = time.perf_counter()
    fehler, text = None, ""
    try:
        text = erzeuge_antwort_allein(frage)
    except Exception as e:
        fehler = f"{type(e).__name__}: {e}"
    latenz = round(time.perf_counter() - t0, 2)

    return {"stufe": stufe, "art": "allein", "frage": frage, "kontext": None,
            "extrahiert": {}, "ergebnis": {}, "angenommen": [],
            "antwort": text, "fehler": fehler,
            "modell": _lokales_modell(), "anbieter": "lokal",
            "kontext_zeichen": 0, "kontext_token_grob": 0,
            "chunk_ids": [], "suchanfragen": [], "anzahl_suchen": 0,
            "verbrauch": {},
            "zeiten": {"retrieval_s": None, "extraktion_s": None,
                       "vertrag_s": None, "antwort_s": latenz},
            "latenz_s": latenz,
            "zeit": datetime.now().isoformat(timespec="seconds")}


def durchgang_extern(frage: str, stufe: str) -> dict:
    s = STUFEN[stufe]
    if s["anbieter"] == "anthropic":
        from extern import frage_extern
        r = frage_extern(frage, s["modell"], s["suche"])
    else:
        from extern_openai import frage_extern_openai
        r = frage_extern_openai(frage, s["modell"], s["suche"])

    return {"stufe": stufe, "art": "extern", "frage": frage, "kontext": None,
            "extrahiert": {}, "ergebnis": {}, "angenommen": [],
            "antwort": r["antwort"], "fehler": r["fehler"],
            "modell": r["modell"], "anbieter": r["anbieter"],
            "kontext_zeichen": 0,
            "kontext_token_grob": (r.get("verbrauch") or {}).get("eingabe_token"),
            "chunk_ids": [], "suchanfragen": r["suchanfragen"],
            "anzahl_suchen": r["anzahl_suchen"], "verbrauch": r["verbrauch"],
            "zeiten": {"retrieval_s": None, "extraktion_s": None,
                       "vertrag_s": None, "antwort_s": r["latenz_s"]},
            "latenz_s": r["latenz_s"],
            "zeit": datetime.now().isoformat(timespec="seconds")}


def m8_attribution(text: str, marken: list[str], kontext: str | None) -> float:
    if not text:
        return 0.0
    bezug = ([m for m in marken if m.lower() in kontext.lower()]
             if kontext else list(marken))
    if not bezug:
        return 0.0
    return round(sum(1 for m in bezug if m.lower() in text.lower()) / len(bezug), 3)


def genannte_quellen(text: str, marken: list[str]) -> list[str]:
    return sorted(m for m in marken if m and m.lower() in (text or "").lower())


def attributionstreue(text: str, kontext: str | None, marken: list[str]) -> float | None:
    genannt = genannte_quellen(text, marken)
    if not genannt:
        return None
    if kontext is None:
        return None
    k = kontext.lower()
    return round(sum(1 for m in genannt if m.lower() in k) / len(genannt), 3)


def m3_kanalisierung(text: str, ergebnis: dict, art: str) -> int | None:
    if art in ("extern", "allein"):
        return 0
    wert = ergebnis.get("lcoh")
    if wert is None or not text:
        return None
    b = lcoh_befund(text)
    if b["vertreter"] is None:
        return 0
    return int(any(abs(w - wert) < 0.6 for w in b["werte"]))


def m1_numerisch(text: str, ergebnis: dict, soll: dict, art: str) -> float | None:
    b = soll.get("lcoh")
    if not b:
        return None
    ist = ergebnis.get("lcoh") if art == "lokal" else lcoh_befund(text)["vertreter"]
    return None if ist is None else round(abs(ist - b) / abs(b), 4)


def datenherkunft(satz: dict, szenario: dict, art: str) -> float:
    if art in ("extern", "allein"):
        return 0.0
    return round(len((set(satz) - set(szenario)) & set(PARAMETER)) / len(PARAMETER), 3)


def mittel(w):
    v = [x for x in w if x is not None]
    return round(sum(v) / len(v), 4) if v else None


def anteil_haeufigster(werte) -> float | None:
    w = [json.dumps(x, sort_keys=True) if isinstance(x, (list, dict)) else x
         for x in werte if x is not None]
    return round(Counter(w).most_common(1)[0][1] / len(w), 3) if w else None


def protokoll(d: dict, pid: str, m: dict, nr: int, f) -> None:
    b = "─" * 74
    w = f.write
    w(f"\n{b}\n{pid} · Lauf {nr} · {d['zeit']}\n"
      f"{bezeichnung(d['stufe'], lang=True)}\n{b}\n")
    if d.get("modell"):
        w(f"Modell: {d['modell']} ({d.get('anbieter')})\n")
    w("\nFRAGE\n  " + " ".join(d["frage"].split()) + "\n")

    w("\nKONTEXT\n")
    if d["kontext"]:
        w(f"  {de(d['kontext_zeichen'], 0)} Zeichen ≈ "
          f"{de(d['kontext_token_grob'], 0)} Token\n")
        if d["chunk_ids"]:
            w("  retrievt: " + ", ".join(d["chunk_ids"]) + "\n")
        for zeile in d["kontext"].split("\n\n"):
            w("  " + zeile[:300] + ("…" if len(zeile) > 300 else "") + "\n")
    elif d["art"] == "extern":
        w("  (kein lokaler Kontext — externes Modell)\n")
        if d["suchanfragen"]:
            w("  Suchanfragen:\n")
            for q in d["suchanfragen"]:
                w(f"    · {q}\n")
        if d["verbrauch"]:
            w(f"  Tokenverbrauch: {darstellung.verbrauch_text(d['verbrauch'])}\n")
    else:
        w("  (keiner — Stufe ohne Datenanbindung)\n")

    if d["art"] == "lokal":
        w("\nAUS DER FRAGE UND DEN DATEN ÜBERNOMMENE WERTE\n")
        for z in darstellung.satz(d["extrahiert"], einzug="  "):
            w(z + "\n")
        if d["ergebnis"]:
            w("\nERGEBNIS DES ENTSCHEIDUNGSSYSTEMS\n")
            for z in darstellung.satz(d["ergebnis"], einzug="  "):
                w(z + "\n")
            for z in darstellung.angenommen_text(d["angenommen"], einzug="  "):
                w(z + "\n")

    if d["fehler"]:
        w(f"\nFEHLER\n  {d['fehler'][:400]}\n")
    else:
        w("\nANTWORT DES SYSTEMS\n")
        for zeile in (d["antwort"] or "(leer)").split("\n"):
            w("  " + zeile + "\n")

    w("\nMESSWERTE\n  " + " | ".join(
        f"{k} {de(v, 0 if k in ('Kontext_Token', 'Suchen') else 3)}"
        for k, v in m.items() if v is not None) + "\n")
    z = {k: v for k, v in d["zeiten"].items() if v is not None}
    w("  Zeiten: " + " | ".join(f"{k} {de(v, 2)} s" for k, v in z.items())
      + f" | gesamt {de(d['latenz_s'], 2)} s\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wiederholungen", type=int, default=3)
    ap.add_argument("--stufen", nargs="+", default=STANDARD_STUFEN)
    ap.add_argument("--k", type=int, default=3, help="Chunks bei V3")
    ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()

    unbekannt = [s for s in a.stufen if s not in STUFEN]
    if unbekannt:
        raise SystemExit(f"Unbekannte Stufen: {unbekannt}\nVerfügbar: {list(STUFEN)}")

    spec = yaml.safe_load(open(PROMPT_SET, encoding="utf-8"))
    kommunen, prompts = spec["kommunen"], spec["prompts"]
    marken = spec["quellenmarken"]
    szen_name, szenario = lade_referenzszenario(spec)

    v0 = v0_eingabeaufwand()
    gold = {}
    for name, kk in kommunen.items():
        gold[name] = wahrheit(kk["profil"], szenario)

    braucht_retrieval = "V3" in a.stufen
    retriever = None
    if braucht_retrieval and not a.trocken:
        from retrieval import Retriever
        retriever = Retriever()

    if a.trocken:
        print("Trockenlauf beendet — kein Modell aufgerufen.")
        return

    Path("reports").mkdir(exist_ok=True)
    stempel = datetime.now().strftime("%Y-%m-%d_%H%M")
    pfad_prot = Path(f"reports/RAG-B_Protokoll_{stempel}.txt")
    zeilen, roh_alle = [], []
    index_info = {}

    with open(pfad_prot, "w", encoding="utf-8") as f:
        f.write(f"Benchmark RAG-B — Protokoll\n{datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Szenario {szen_name}\n")
        for z in darstellung.satz(szenario, einzug="  "):
            f.write(z + "\n")
        f.write("Stufen:\n")
        for s_ in a.stufen:
            f.write(f"  {s_:<10} {bezeichnung(s_, lang=True)}\n")
        f.write("Vollständige Wortlaute für den Anhang der Arbeit.\n")

        for stufe in a.stufen:
            art = STUFEN[stufe]["art"]
            for p in prompts:
                kom = p["kommune"]
                pfad = kommunen[kom]["profil"]
                soll = gold[kom]["ergebnis"]
                frage = " ".join(p["prompt"].split())

                if stufe == "V3" and index_info.get("kommune") != kom:
                    index_info = retriever.indexiere(pfad)
                    index_info["kommune"] = kom

                wdh = []
                for i in range(a.wiederholungen):
                    if art == "allein":
                        d = durchgang_allein(frage, stufe)
                    elif art == "extern":
                        d = durchgang_extern(frage, stufe)
                    else:
                        d = durchgang_lokal(frage, stufe, pfad, szenario,
                                            retriever, a.k)
                    b = lcoh_befund(d["antwort"])
                    m = {
                        "Attribution": m8_attribution(d["antwort"], marken, d["kontext"]),
                        "Attributionstreue": attributionstreue(
                            d["antwort"], d["kontext"], marken),
                        "Datenherkunft": datenherkunft(d["extrahiert"], szenario, art),
                        "Kanalisierung": m3_kanalisierung(d["antwort"],
                                                          d["ergebnis"], art),
                        "relFehler": m1_numerisch(d["antwort"], d["ergebnis"],
                                                  soll, art),
                        "Latenz_s": d["latenz_s"],
                        "Kontext_Token": d["kontext_token_grob"],
                        "Suchen": d["anzahl_suchen"],
                    }
                    d["metriken"] = m
                    d["zahlbefund"] = b
                    d["quellen"] = genannte_quellen(d["antwort"], marken)
                    wdh.append(d)
                    roh_alle.append({**d, "prompt": p["id"], "kommune": kom})
                    protokoll(d, p["id"], m, i + 1, f)

                gueltig = [x for x in wdh if not x["fehler"]]
                zeilen.append({
                    "prompt": p["id"], "leistung": p["leistung"], "kommune": kom,
                    "stufe": stufe, "bezeichnung": bezeichnung(stufe),
                    "art": art, "n": len(wdh), "ok": len(gueltig),
                    **{kk: mittel([x["metriken"][kk] for x in gueltig])
                       for kk in ("Attribution", "Attributionstreue", "Datenherkunft",
                                  "Kanalisierung", "relFehler", "Latenz_s",
                                  "Kontext_Token", "Suchen")},
                    "stabil_zahl": anteil_haeufigster(
                        [x["zahlbefund"]["vertreter"] for x in gueltig]),
                    "stabil_quellen": anteil_haeufigster(
                        [x["quellen"] for x in gueltig]),
                })

    ergebnis_pfad = f"reports/RAG-B_Ergebnis_{stempel}.json"
    with open(ergebnis_pfad, "w", encoding="utf-8") as f:
        json.dump({"v0": v0, "szenario": {szen_name: szenario},
                   "k": a.k,
                   "stufen": {s_: {**STUFEN[s_],
                                   "bezeichnung_kurz": bezeichnung(s_),
                                   "bezeichnung_lang": bezeichnung(s_, lang=True)}
                              for s_ in a.stufen},
                   "lokales_modell": _lokales_modell(),
                   "index": index_info,
                   "gold": {k: v["ergebnis"] for k, v in gold.items()},
                   "zeilen": zeilen}, f, indent=2, ensure_ascii=False)

    print(f"Gespeichert: {pfad_prot}, {ergebnis_pfad}")


if __name__ == "__main__":
    main()
