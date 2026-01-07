import json
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class DifyDatasetClient:
    """
    Dify Dataset 文档管理客户端
    """
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.dify.ai/v1",
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def list_documents(
        self,
        dataset_id: str,
        page: int = 1,
        limit: int = 20,
        keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"page": page, "limit": limit}
        if keyword:
            params["keyword"] = keyword

        url = f"{self.base_url}/datasets/{dataset_id}/documents"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            logger.error(f"Dify document list failed: {exc}")
            return {"documents": [], "error": str(exc)}

    def upload_document(
        self,
        dataset_id: str,
        file_obj,
        filename: str,
        content_type: Optional[str] = None,
        indexing_technique: str = "high_quality",
        process_mode: str = "automatic",
    ) -> Dict[str, Any]:
        # ✅ 注意路径变了！
        url = f"{self.base_url}/datasets/{dataset_id}/document/create-by-file"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        payload = {
            "name": filename,
            "indexing_technique": indexing_technique,
            "process_rule": {"mode": process_mode},
        }

        files = {
            "file": (filename, file_obj, content_type or "application/octet-stream"),
        }

        data = {
            "data": json.dumps(payload)  # Dify 要求 data 是 JSON 字符串
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            logger.debug(f"Dify upload status: {response.status_code}, body: {repr(response.text)}")
            if response.status_code != 200:
                logger.error(f"Dify returned non-200: {response.text}")
                raise Exception("Dify API error")
            return response.json()
        except Exception as exc:
            logger.error(f"Dify document upload failed: {exc}")
            if 'response' in locals():
                logger.debug(f"Raw response: {repr(response.text)}")
            return {"error": str(exc)}
