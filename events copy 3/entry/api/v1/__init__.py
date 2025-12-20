from fastapi import APIRouter
from .commands import router as commands_router
from .queries import router as queries_router

router = APIRouter(prefix="/v1")
router.include_router(commands_router, tags=["commands"])
router.include_router(queries_router, tags=["queries"])

__all__ = ["router"]