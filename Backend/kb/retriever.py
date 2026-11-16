import json
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
FAISS_INDEX_FILE = PROCESSED_DIR / "bug_chunks.faiss"
METADATA_FILE = PROCESSED_DIR / "bug_metadata.json"

class DefectRetriever:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        self.index = faiss.read_index(str(FAISS_INDEX_FILE))
        self.metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        q_vec = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
        scores, indices = self.index.search(q_vec, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:
                item = dict(self.metadata[idx])
                item["similarity_score"] = round(float(score), 4)
                results.append(item)
        return results

if __name__ == "__main__":
    retriever = DefectRetriever()
    query = "NullPointerException in NetworkClient poll when broker disconnects"
    hits = retriever.search(query, top_k=3)
    print(f"\nTop 3 Matches for: '{query}'")
    for h in hits:
        print(f"- [Score: {h['similarity_score']}] {h['original_bug_id']} ({h['chunk_type']}): {h['content'][:150]}...")