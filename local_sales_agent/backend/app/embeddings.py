"""Local Sentence Transformers embeddings; never downloads while the app runs."""
from __future__ import annotations
import os
from pathlib import Path
import numpy as np

MODEL_PATH = Path(os.getenv("HARVEY_EMBEDDING_MODEL_PATH", Path(__file__).resolve().parents[1] / "models" / "all-MiniLM-L6-v2"))
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_model = None

class EmbeddingUnavailable(RuntimeError):
    pass

def model():
    global _model
    if _model is None:
        if not MODEL_PATH.is_dir():
            raise EmbeddingUnavailable(f"Local embedding model not found at {MODEL_PATH}. While online, run `python download_embedding_model.py` in backend/. No download or remote inference is attempted by the app.")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(str(MODEL_PATH), device="cpu", local_files_only=True)
        except Exception as exc:
            raise EmbeddingUnavailable(f"Could not load the cached embedding model: {exc}") from exc
    return _model

def encode(text: str) -> np.ndarray:
    if not text.strip(): raise ValueError("Cannot embed empty text")
    return model().encode([text], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)[0].astype(np.float32)
