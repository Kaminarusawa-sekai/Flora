from fastapi import APIRouter
from .v1 import router as v1_router

router = APIRouter()
router.include_router(v1_router)

from .deps import (
    get_cache,
    get_broker,
    get_event_definition_repo,
    get_event_instance_repo,
    get_connection_manager,
    get_lifecycle_service,
    get_signal_service,
    get_observer_service,
    connection_manager_instance
)

__all__ = [
    "router",
    "get_cache",
    "get_broker",
    "get_event_definition_repo",
    "get_event_instance_repo",
    "get_connection_manager",
    "get_lifecycle_service",
    "get_signal_service",
    "get_observer_service",
    "connection_manager_instance"
]