from typing import Dict, Any, List
from .base_agent import BaseAgent


class MedicalRetriever(BaseAgent):
    """Agent 2: Multi-source retrieval using FAISS vector store."""

    def __init__(self, vector_store=None, web_search_tool=None):
        super().__init__(
            name="Medical Retriever",
            description="Retrieves relevant clinical evidence from FAISS vector store and optional web sources"
        )
        self.vector_store = vector_store
        self.web_search_tool = web_search_tool

    def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        expanded_query = context.get("expanded_query", context.get("query", ""))
        original_query = context.get("original_query", expanded_query)
        self.log(f"Retrieving evidence for: {expanded_query[:80]}...")

        all_results = []
        existing_ids = set()

        # Primary retrieval from FAISS
        if self.vector_store:
            try:
                primary_results = self.vector_store.search(expanded_query, top_k=15)
                all_results.extend(primary_results)
                existing_ids = {r["id"] for r in all_results}
                self.log(f"FAISS returned {len(primary_results)} results")

                # Also search with original query for diversity
                if original_query != expanded_query:
                    secondary_results = self.vector_store.search(original_query, top_k=10)
                    # Add non-duplicate results
                    for r in secondary_results:
                        if r["id"] not in existing_ids:
                            all_results.append(r)
                            existing_ids.add(r["id"])
                    self.log(f"Secondary search added {len(secondary_results)} more candidates")

                # Search for specific medical concepts
                concepts = context.get("medical_concepts", [])
                for concept in concepts[:3]:
                    concept_results = self.vector_store.search(concept, top_k=5)
                    for r in concept_results:
                        if r["id"] not in existing_ids:
                            all_results.append(r)
                            existing_ids.add(r["id"])

            except Exception as e:
                self.log(f"FAISS search error: {e}")

        # Optional web search for supplementary information
        if context.get("enable_web_search", False):
            # Use pre-fetched results if available (from /api/webscrape)
            pre_fetched = context.get("pre_fetched_web_results", [])
            if pre_fetched:
                web_results = pre_fetched
                self.log(f"Using {len(web_results)} pre-fetched PubMed articles")
            elif self.web_search_tool:
                try:
                    web_results = self.web_search_tool.search(original_query)
                    self.log(f"Web search returned {len(web_results)} results")
                except Exception as e:
                    self.log(f"Web search error: {e}")
                    web_results = []
            else:
                web_results = []

            for wr in web_results:
                if wr.get("id") not in existing_ids:
                    wr["source_type"] = "web"
                    all_results.append(wr)
                    existing_ids.add(wr["id"])
            context["web_results_count"] = len(web_results)

        context["retrieved_chunks"] = all_results
        context["retrieval_count"] = len(all_results)
        self.log(f"Total retrieved: {len(all_results)} evidence chunks")
        return context
