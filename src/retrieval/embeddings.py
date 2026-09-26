from __future__ import annotations

from functools import lru_cache

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = _load_model(model_name)

    @property
    def dimension(self) -> int:
        get_dimension = getattr(self.model, "get_embedding_dimension", None)
        dimension = (
            get_dimension()
            if get_dimension is not None
            else self.model.get_sentence_embedding_dimension()
        )
        if dimension is None:
            raise RuntimeError(f"Unable to determine embedding dimension for {self.model_name}.")
        return int(dimension)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("All documents must be non-empty strings before embedding.")
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Query must be a non-empty string.")
        embedding = self.model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embedding[0].tolist()
