import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional
from .embeddings import EmbeddingEngine
from .chunking import SectionAwareChunker


class FAISSVectorStore:
    """FAISS-based vector store with section-aware indexing."""

    def __init__(self, store_path: str = "./data/faiss_index",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 512, chunk_overlap: int = 50):
        self.store_path = store_path
        self.embedding_engine = EmbeddingEngine(embedding_model)
        self.chunker = SectionAwareChunker(chunk_size, chunk_overlap)
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: List[Dict[str, Any]] = []
        self._loaded = False

    def build_from_documents(self, documents: List[Dict[str, Any]]) -> int:
        """Build the vector store from clinical documents."""
        print("Chunking documents...")
        self.chunks = self.chunker.chunk_documents(documents)
        print(f"Created {len(self.chunks)} chunks from {len(documents)} documents.")

        if not self.chunks:
            raise ValueError("No chunks created from documents.")

        texts = [chunk["text"] for chunk in self.chunks]
        print("Computing embeddings...")
        embeddings = self.embedding_engine.embed(texts)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)

        self.save()
        self._loaded = True
        print(f"Vector store built with {len(self.chunks)} chunks.")
        return len(self.chunks)

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search the vector store."""
        if not self._loaded:
            self.load()

        query_embedding = self.embedding_engine.embed_query(query)
        query_embedding = query_embedding.reshape(1, -1)

        distances, indices = self.index.search(query_embedding, min(top_k, len(self.chunks)))

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            chunk = self.chunks[idx].copy()
            chunk["similarity_score"] = float(dist)
            results.append(chunk)

        return results

    def save(self):
        """Save index and chunks to disk."""
        os.makedirs(self.store_path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(self.store_path, "index.faiss"))
        with open(os.path.join(self.store_path, "chunks.json"), "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, indent=2, ensure_ascii=False)
        print(f"Vector store saved to {self.store_path}")

    def load(self) -> bool:
        """Load index and chunks from disk."""
        index_path = os.path.join(self.store_path, "index.faiss")
        chunks_path = os.path.join(self.store_path, "chunks.json")

        if not os.path.exists(index_path) or not os.path.exists(chunks_path):
            return False

        self.index = faiss.read_index(index_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            self.chunks = json.load(f)
        self._loaded = True
        print(f"Vector store loaded: {len(self.chunks)} chunks.")
        return True

    def is_built(self) -> bool:
        """Check if vector store exists on disk."""
        return (os.path.exists(os.path.join(self.store_path, "index.faiss"))
                and os.path.exists(os.path.join(self.store_path, "chunks.json")))
