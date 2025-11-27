# memory/interfaces.py
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class IVaultRepository(ABC):
    @abstractmethod
    def store(self, user_id: str, category: str, key_name: str, value: str) -> None:
        pass

    @abstractmethod
    def retrieve(self, user_id: str, category: Optional[str] = None) -> List[str]:
        pass


class IProceduralRepository(ABC):
    @abstractmethod
    def add_procedure(self, proc: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def search(self, query: str, domain: Optional[str] = None, limit: int = 3) -> List[str]:
        pass


class IResourceRepository(ABC):
    @abstractmethod
    def add_document(
        self,
        user_id: str,
        file_path: str,
        summary: str,
        doc_type: str = "unknown",
        source_url: str = ""
    ) -> str:
        pass

    @abstractmethod
    def search(self, query: str, user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        pass