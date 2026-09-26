from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import chromadb
from chromadb.errors import NotFoundError
import pandas as pd

from core.config import Settings
from core.utils import read_json, safe_slug, write_json
from retrieval.embeddings import MiniLMEmbeddings


REQUIRED_INDEX_COLUMNS = {
    "paper_id",
    "title",
    "text_for_embedding",
    "published",
    "authors_joined",
    "categories_joined",
    "summary",
    "abs_url",
    "pdf_url",
}


@dataclass(frozen=True)
class SearchResult:
    paper_id: str
    title: str
    score: float
    content: str
    metadata: dict[str, Any]


class LocalEmbeddingIndex:
    def __init__(
        self,
        settings: Settings,
        collection_name: str,
        documents: list[dict[str, Any]],
        persist_path: Path,
    ):
        self.settings = settings
        self.collection_name = collection_name
        self.documents = documents
        self.persist_path = persist_path
        self.embedding_backend = "chroma"
        self.embedding_model = MiniLMEmbeddings(settings.embedding_model)
        self.client = chromadb.PersistentClient(path=str(persist_path))
        self.collection = self.client.get_collection(name=collection_name)
        self.documents_by_paper_id = {document["paper_id"].lower(): document for document in documents}
        self.documents_by_title = {document["title"].lower(): document for document in documents}

    @staticmethod
    def _build_documents(df: pd.DataFrame) -> list[dict[str, Any]]:
        missing_columns = sorted(REQUIRED_INDEX_COLUMNS.difference(df.columns))
        if missing_columns:
            raise ValueError(f"Dataframe is missing required index columns: {missing_columns}")
        if df.empty:
            raise ValueError("Cannot build a vector index from an empty dataframe.")

        records = df.to_dict(orient="records")
        documents: list[dict[str, Any]] = []
        for index, row in enumerate(records):
            paper_id = str(row["paper_id"]).strip()
            title = str(row["title"]).strip()
            content = str(row["text_for_embedding"]).strip()
            if not paper_id or not title or not content:
                raise ValueError(
                    f"Row {index} must have non-empty paper_id, title, and text_for_embedding."
                )
            documents.append(
                {
                    "record_id": f"{paper_id}::{index}",
                    "paper_id": paper_id,
                    "title": title,
                    "content": content,
                    "metadata": {
                        "paper_id": paper_id,
                        "title": title,
                        "published": str(row["published"]),
                        "authors_joined": str(row["authors_joined"]),
                        "categories_joined": str(row["categories_joined"]),
                        "summary": str(row["summary"]),
                        "abs_url": str(row["abs_url"]),
                        "pdf_url": str(row["pdf_url"]),
                    },
                }
            )
        return documents

    @staticmethod
    def _portable_persist_path(settings: Settings, persist_path: Path) -> str:
        resolved_path = persist_path.resolve()
        try:
            return resolved_path.relative_to(settings.paths.project_dir.resolve()).as_posix()
        except ValueError:
            return str(resolved_path)

    @staticmethod
    def _resolve_persist_path(settings: Settings, stored_path: str) -> Path:
        persist_path = Path(stored_path)
        if not persist_path.is_absolute():
            persist_path = settings.paths.project_dir / persist_path
        return persist_path.resolve()

    @staticmethod
    def _derive_collection_name(settings: Settings, embeddings_output_path: Path | None) -> str:
        if embeddings_output_path is None:
            return settings.baseline_collection_name

        name_map = {
            settings.paths.embeddings_json.resolve(): settings.baseline_collection_name,
            settings.paths.corrupted_embeddings_json.resolve(): settings.corrupted_collection_name,
            settings.paths.repaired_embeddings_json.resolve(): settings.repaired_collection_name,
        }
        resolved_path = embeddings_output_path.resolve()
        if resolved_path in name_map:
            return name_map[resolved_path]
        return safe_slug(embeddings_output_path.stem)

    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        settings: Settings,
        embeddings_output_path: Path | None = None,
    ) -> "LocalEmbeddingIndex":
        collection_name = cls._derive_collection_name(settings, embeddings_output_path)
        documents = cls._build_documents(df)
        persist_path = settings.paths.chroma_dir
        persist_path.mkdir(parents=True, exist_ok=True)

        embedding_model = MiniLMEmbeddings(settings.embedding_model)
        client = chromadb.PersistentClient(path=str(persist_path))
        try:
            client.delete_collection(name=collection_name)
        except NotFoundError:
            pass
        collection = client.create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
        )
        embeddings = embedding_model.embed_documents([document["content"] for document in documents])
        if len(embeddings) != len(documents):
            raise RuntimeError("Embedding count does not match document count.")
        if any(len(embedding) != embedding_model.dimension for embedding in embeddings):
            raise RuntimeError("Embedding vectors have an unexpected dimension.")
        collection.add(
            ids=[document["record_id"] for document in documents],
            embeddings=embeddings,
            documents=[document["content"] for document in documents],
            metadatas=[document["metadata"] for document in documents],
        )
        if collection.count() != len(documents):
            raise RuntimeError("Persisted Chroma document count does not match the input dataframe.")

        manifest_path = embeddings_output_path or settings.paths.embeddings_json
        write_json(
            manifest_path,
            {
                "backend": "chroma",
                "embedding_model": settings.embedding_model,
                "embedding_dimension": embedding_model.dimension,
                "persist_path": cls._portable_persist_path(settings, persist_path),
                "collection_name": collection_name,
                "document_count": len(documents),
                "documents": documents,
            },
        )
        return cls(
            settings=settings,
            collection_name=collection_name,
            documents=documents,
            persist_path=persist_path,
        )

    @classmethod
    def load(cls, settings: Settings, embeddings_path: Path | None = None) -> "LocalEmbeddingIndex":
        payload = read_json(embeddings_path or settings.paths.embeddings_json)
        if payload.get("backend") != "chroma":
            raise ValueError("Embedding manifest backend must be 'chroma'.")
        if payload.get("embedding_model") != settings.embedding_model:
            raise ValueError("Embedding manifest model does not match the configured model.")

        documents = payload.get("documents") or []
        expected_count = int(payload.get("document_count", len(documents)))
        if expected_count != len(documents):
            raise ValueError("Embedding manifest document_count is inconsistent.")

        index = cls(
            settings=settings,
            collection_name=payload["collection_name"],
            documents=documents,
            persist_path=cls._resolve_persist_path(settings, payload["persist_path"]),
        )
        if index.collection.count() != expected_count:
            raise RuntimeError("Chroma collection count does not match the embedding manifest.")
        return index

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query must be a non-empty string.")
        requested_results = top_k if top_k is not None else self.settings.top_k
        if requested_results <= 0:
            raise ValueError("top_k must be greater than zero.")
        collection_count = self.collection.count()
        if collection_count == 0:
            return []

        query_embedding = self.embedding_model.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(requested_results, collection_count),
            include=["documents", "metadatas", "distances"],
        )
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        scored: list[SearchResult] = []
        for record_id, content, metadata, distance in zip(ids, documents, metadatas, distances, strict=False):
            if not record_id or not metadata or not content:
                continue
            scored.append(
                SearchResult(
                    paper_id=str(metadata["paper_id"]),
                    title=str(metadata["title"]),
                    score=max(
                        0.0,
                        min(1.0, 1.0 - float(distance) if distance is not None else 0.0),
                    ),
                    content=str(content),
                    metadata=dict(metadata),
                )
            )
        return scored

    def lookup(self, value: str) -> dict[str, Any] | None:
        needle = value.strip().lower()
        if needle in self.documents_by_paper_id:
            return self.documents_by_paper_id[needle]
        if needle in self.documents_by_title:
            return self.documents_by_title[needle]
        return None


class TitleRerankedIndex:
    """Rerank semantic candidates with lexical title relevance.

    The wrapper never searches the full corpus by exact title. It only reorders
    candidates already returned by vector search, so evaluation still measures
    semantic retrieval while making the final top-1 selection more precise.
    """

    def __init__(self, base_index: LocalEmbeddingIndex):
        self.base_index = base_index

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return set(re.findall(r"\w+", value.casefold()))

    @classmethod
    def _title_relevance(cls, query: str, title: str) -> float:
        quoted_match = re.search(r"(['\"])(.+?)\1", query)
        quoted_title = quoted_match.group(2) if quoted_match else ""
        title_tokens = cls._tokens(title)
        target_tokens = cls._tokens(quoted_title or query)
        if not title_tokens or not target_tokens:
            return 0.0

        overlap = len(title_tokens & target_tokens) / len(title_tokens | target_tokens)
        if quoted_title and " ".join(quoted_title.casefold().split()) == " ".join(
            title.casefold().split()
        ):
            return 2.0
        return overlap

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        candidates = self.base_index.search(query, top_k=top_k)
        return sorted(
            candidates,
            key=lambda item: (self._title_relevance(query, item.title), item.score),
            reverse=True,
        )

    def lookup(self, value: str) -> dict[str, Any] | None:
        return self.base_index.lookup(value)
