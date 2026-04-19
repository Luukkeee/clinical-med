import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "3000"))
    MODE: str = os.getenv("MODE", "demo")
    VECTOR_STORE_PATH: str = os.getenv("VECTOR_STORE_PATH", "./data/faiss_index")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    ENABLE_WEB_SEARCH: bool = os.getenv("ENABLE_WEB_SEARCH", "false").lower() == "true"
    DOCUMENTS_PATH: str = os.getenv("DOCUMENTS_PATH", "./documents")

    @classmethod
    def is_demo_mode(cls) -> bool:
        return cls.MODE == "demo" or not cls.OPENAI_API_KEY or cls.OPENAI_API_KEY == "your-openai-api-key-here"


config = Config()
