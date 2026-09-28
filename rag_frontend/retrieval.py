#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, "rag")

import profil_chunks
import fachwissen
import profil

MODELL = "intfloat/multilingual-e5-base"
PRAEFIXE = True          # e5 erwartet "query: " bzw. "passage: "
K_STANDARD = 3


class _Embedder:
    def __init__(self, modell_id: str = MODELL, praefixe: bool = PRAEFIXE):
        from sentence_transformers import SentenceTransformer
        self.modell_id = modell_id
        self._praefixe = praefixe
        t0 = time.perf_counter()
        self._m = SentenceTransformer(modell_id)
        self.ladezeit_s = round(time.perf_counter() - t0, 2)

    def _mit_praefix(self, texte, modus):
        return [f"{modus}: {t}" for t in texte] if self._praefixe else list(texte)

    def embed(self, texte, modus: str = "passage"):
        return self._m.encode(self._mit_praefix(texte, modus),
                              normalize_embeddings=True).tolist()

    def revision(self) -> str:
        try:
            auto = getattr(self._m[0], "auto_model", None)
            return getattr(auto.config, "_commit_hash", "unbekannt") if auto else "unbekannt"
        except Exception:
            return "unbekannt"


class Retriever:
    def __init__(self, embedder: _Embedder | None = None, pfad: str = "chromadb"):
        self.emb = embedder or _Embedder()
        self.pfad_wunsch = pfad
        self.pfad_ist = None
        self._chunks = []
        self._vecs = []
        self._col = None
        self.index_zeit_s = None

    def indexiere(self, profil_pfad: str, mit_technikkatalog: bool = True) -> dict:
        prof = profil.lade_profil(profil_pfad)
        chunks = profil_chunks.chunk_profil(prof, kommune_modus="voll", mit_status=True)
        if mit_technikkatalog:
            chunks += fachwissen.lade_technikkatalog()
        self._chunks = chunks

        t0 = time.perf_counter()
        if self.pfad_wunsch == "chromadb":
            try:
                self._index_chromadb(chunks)
                self.pfad_ist = "chromadb"
            except Exception:
                self._index_kosinus(chunks)
                self.pfad_ist = "kosinus (Fallebene)"
        else:
            self._index_kosinus(chunks)
            self.pfad_ist = "kosinus"
        self.index_zeit_s = round(time.perf_counter() - t0, 2)

        return {"chunks": len(chunks), "pfad": self.pfad_ist,
                "index_zeit_s": self.index_zeit_s,
                "modell": self.emb.modell_id, "revision": self.emb.revision(),
                "modell_ladezeit_s": self.emb.ladezeit_s}

    def _index_chromadb(self, chunks):
        import chromadb
        client = chromadb.Client()
        name = f"kb_{int(time.time()*1000)}"
        col = client.create_collection(name)
        col.add(ids=[c["chunk_id"] for c in chunks],
                documents=[c["text"] for c in chunks],
                embeddings=self.emb.embed([c["text"] for c in chunks], "passage"),
                metadatas=[{"block": c["block"],
                            "kommune": c.get("kommune") or ""} for c in chunks])
        self._col = col

    def _index_kosinus(self, chunks):
        self._vecs = self.emb.embed([c["text"] for c in chunks], "passage")
        self._col = None

    def suche(self, frage: str, k: int = K_STANDARD) -> dict:
        t0 = time.perf_counter()
        qv = self.emb.embed([frage], "query")[0]
        t_embed = time.perf_counter() - t0

        t1 = time.perf_counter()
        if self._col is not None:
            res = self._col.query(query_embeddings=[qv], n_results=k)
            ids = res["ids"][0]
            texte = res["documents"][0]
        else:
            import b3_embedding_benchmark as b3
            ids = b3.retrieve(qv, self._vecs, [c["chunk_id"] for c in self._chunks], k)
            nach_id = {c["chunk_id"]: c["text"] for c in self._chunks}
            texte = [nach_id[i] for i in ids]
        t_suche = time.perf_counter() - t1

        kontext = "\n\n".join(texte)
        return {"chunk_ids": ids, "kontext": kontext,
                "kontext_zeichen": len(kontext),
                "kontext_token_grob": len(kontext) // 4,
                "embed_s": round(t_embed, 3), "suche_s": round(t_suche, 3),
                "retrieval_s": round(t_embed + t_suche, 3)}


if __name__ == "__main__":
    r = Retriever()
    info = r.indexiere("wissensbasis/kommune_johanngeorgenstadt.yaml")
    for frage in ("Was kostet so eine Großwärmepumpe eigentlich, und wie lange hält die?",
                  "Woher haben Sie diese Zahlen? Ich muss das im Ausschuss belegen können.",
                  "Was kostet die Wärme aus so einem Netz bei uns ungefähr pro Megawattstunde?"):
        r.suche(frage)
    print(f"{info['chunks']} Chunks indexiert ({info['pfad']})")
