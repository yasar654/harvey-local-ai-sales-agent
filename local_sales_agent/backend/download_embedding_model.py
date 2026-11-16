"""One-time online download of the Apache-2.0 MiniLM embedding model."""
from pathlib import Path
from sentence_transformers import SentenceTransformer

target = Path(__file__).resolve().parent / "models" / "all-MiniLM-L6-v2"
target.parent.mkdir(parents=True, exist_ok=True)
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
model.save(str(target))
print(f"Saved local embedding model to: {target}")
