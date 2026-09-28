#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

MODELLE = {
    "e5_base":   "intfloat/multilingual-e5-base",      # MIT
    "bge_m3":    "BAAI/bge-m3",                       # MIT
    "jina_v2_de": "jinaai/jina-embeddings-v2-base-de", # CC-BY-NC prüfen!
}


class SentenceTransformerEmbedder:
    def __init__(self, modell_name: str):
        from sentence_transformers import SentenceTransformer
        self._m = SentenceTransformer(modell_name)

    def embed(self, texte: list[str]) -> list[list[float]]:
        return self._m.encode(list(texte), normalize_embeddings=True).tolist()
