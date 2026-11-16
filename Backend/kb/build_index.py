import json
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
CHUNKS_FILE = PROCESSED_DIR / "processed_chunks.json"
FAISS_INDEX_FILE = PROCESSED_DIR / "bug_chunks.faiss"
METADATA_FILE = PROCESSED_DIR / "bug_metadata.json"

def build_faiss_index():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    print("Loading CPU embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    texts = [c["content"] for c in chunks]
    print(f"Encoding {len(texts)} chunks on CPU...")
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(FAISS_INDEX_FILE))
    METADATA_FILE.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"Indexed {index.ntotal} vectors -> {FAISS_INDEX_FILE}")

if __name__ == "__main__":
    build_faiss_index()