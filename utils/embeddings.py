import os
import ssl
import numpy as np
from typing import List

# Fix SSL certificate issues in corporate environments
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""

try:
    _default_ctx = ssl._create_default_https_context
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

# Patch httpx to skip SSL verification
try:
    import httpx
    _original_client_init = httpx.Client.__init__

    def _patched_client_init(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _original_client_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_client_init

    _original_async_init = httpx.AsyncClient.__init__

    def _patched_async_init(self, *args, **kwargs):
        kwargs.setdefault("verify", False)
        _original_async_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = _patched_async_init
except Exception:
    pass

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from sentence_transformers import SentenceTransformer


class EmbeddingEngine:
    """Embedding engine using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name, trust_remote_code=True)
            print("Embedding model loaded.")
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed a list of texts."""
        if not texts:
            return np.array([])
        embeddings = self.model.encode(
            texts,
            show_progress_bar=len(texts) > 50,
            normalize_embeddings=True,
            batch_size=32
        )
        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query."""
        return self.embed([query])[0]

    @property
    def dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()
