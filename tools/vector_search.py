from typing import List, Dict, Any


class VectorSearchTool:
    """Tool for searching the FAISS vector store."""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Search the vector store for relevant documents."""
        return self.vector_store.search(query, top_k=top_k)

    def multi_search(self, queries: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search with multiple queries and merge results."""
        all_results = []
        seen_ids = set()

        for query in queries:
            results = self.vector_store.search(query, top_k=top_k)
            for r in results:
                if r["id"] not in seen_ids:
                    all_results.append(r)
                    seen_ids.add(r["id"])

        return all_results
