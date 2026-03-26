"""ChromaDB vector store for semantic search.

Why ChromaDB instead of SQL for logs/incidents?
- Logs are TEXT. "BGP peer dropped" and "BGP session timeout" mean the SAME thing.
- SQL can't understand meaning: WHERE message LIKE '%BGP%' misses "routing protocol failed".
- ChromaDB converts text to vectors (numbers) where SIMILAR MEANINGS are CLOSE together.
- So searching "CPU spike caused BGP drop" finds "High CPU led to routing failure" too.
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings


class SentenceTransformerEmbedding(chromadb.EmbeddingFunction):
    """Custom embedding function using sentence-transformers.

    ChromaDB's default model download is unreliable. We use sentence-transformers
    directly which handles caching properly via HuggingFace Hub.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model = None
        self._model_name = model_name

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    @staticmethod
    def name() -> str:
        return "sentence-transformers"

    def __call__(self, input: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(input, show_progress_bar=False)
        return embeddings.tolist()


class VectorStore:
    """ChromaDB wrapper for semantic search over network data."""

    def __init__(self, persist_dir: str | None = None):
        """Initialize ChromaDB.

        Args:
            persist_dir: Directory to persist data. None = in-memory (fast, no disk).
        """
        if persist_dir:
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
        else:
            self.client = chromadb.Client(
                settings=Settings(anonymized_telemetry=False),
            )

        # Use our custom embedding function
        self._embedding_fn = SentenceTransformerEmbedding()

        # Create collections for each data type
        self.syslog = self.client.get_or_create_collection(
            name="syslog_chunks",
            metadata={"description": "Router syslog events grouped by time window"},
            embedding_function=self._embedding_fn,
        )
        self.devices = self.client.get_or_create_collection(
            name="device_metadata",
            metadata={"description": "Device inventory descriptions"},
            embedding_function=self._embedding_fn,
        )
        self.topology = self.client.get_or_create_collection(
            name="topology_facts",
            metadata={"description": "Network topology connections and facts"},
            embedding_function=self._embedding_fn,
        )
        self.incidents = self.client.get_or_create_collection(
            name="incidents",
            metadata={"description": "Historical incident reports and resolutions"},
            embedding_function=self._embedding_fn,
        )
        self.security = self.client.get_or_create_collection(
            name="security_events",
            metadata={"description": "Security events and alerts"},
            embedding_function=self._embedding_fn,
        )

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ):
        """Add documents to a named collection.

        Args:
            collection_name: One of: syslog_chunks, device_metadata, topology_facts,
                           incidents, security_events
            documents: List of text strings to embed and store
            metadatas: Optional metadata dicts for each document
            ids: Optional unique IDs. Auto-generated if not provided.
        """
        collection = self.client.get_collection(
            collection_name, embedding_function=self._embedding_fn
        )

        if ids is None:
            existing = collection.count()
            ids = [f"{collection_name}_{existing + i}" for i in range(len(documents))]

        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def search(
        self,
        collection_name: str,
        query: str,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Semantic search over a collection.

        Args:
            collection_name: Which collection to search
            query: Natural language query string
            top_k: Number of results to return
            where: Optional metadata filter (e.g., {"device": "ROUTER-LAB-01"})

        Returns:
            List of dicts with: document, metadata, distance (lower = more similar)
        """
        collection = self.client.get_collection(
            collection_name, embedding_function=self._embedding_fn
        )

        kwargs = {
            "query_texts": [query],
            "n_results": min(top_k, collection.count()) if collection.count() > 0 else 1,
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        output = []
        if results and results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                output.append(
                    {
                        "document": results["documents"][0][i],
                        "metadata": (
                            results["metadatas"][0][i] if results["metadatas"] else {}
                        ),
                        "distance": (
                            results["distances"][0][i] if results["distances"] else 0
                        ),
                        "id": results["ids"][0][i] if results["ids"] else "",
                    }
                )

        return output

    def get_all(self, collection_name: str) -> list[dict]:
        """Get all documents from a collection."""
        collection = self.client.get_collection(
            collection_name, embedding_function=self._embedding_fn
        )
        if collection.count() == 0:
            return []
        results = collection.get()
        output = []
        for i in range(len(results["documents"])):
            output.append(
                {
                    "document": results["documents"][i],
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    "id": results["ids"][i],
                }
            )
        return output

    def get_stats(self) -> dict:
        """Get document counts per collection."""
        return {
            "syslog_chunks": self.syslog.count(),
            "device_metadata": self.devices.count(),
            "topology_facts": self.topology.count(),
            "incidents": self.incidents.count(),
            "security_events": self.security.count(),
        }
