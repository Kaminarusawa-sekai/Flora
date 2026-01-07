import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class DifyRagClient:
    """
    Dify RAG 检索客户端
    """
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.dify.ai/v1",
        dataset_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        timeout: int = 15,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.dataset_id = dataset_id
        self.endpoint = endpoint or self._default_endpoint()
        self.timeout = timeout

    def _default_endpoint(self) -> str:
        if not self.dataset_id:
            return f"{self.base_url}/datasets/retrieve"
        return f"{self.base_url}/datasets/{self.dataset_id}/retrieve"

    def search(self, query: str, user_id: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "query": query,
            "top_k": top_k,
        }
        if user_id:
            payload["user"] = user_id

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.error(f"Dify RAG search failed: {exc}")
            return []

        records = data.get("records") or data.get("data") or data.get("documents") or []
        results: List[Dict[str, Any]] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            text = (
                item.get("content")
                or item.get("segment")
                or item.get("text")
                or item.get("document")
                or ""
            )
            if not text:
                continue
            results.append({
                "text": text,
                "score": item.get("score"),
                "metadata": item.get("metadata", {}),
            })
        return results
