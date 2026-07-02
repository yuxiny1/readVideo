from fastapi import APIRouter

from backend.api.controllers.library_controller import router as library_router
from backend.api.controllers.models_controller import router as models_router
from backend.api.controllers.reader_controller import router as reader_router
from backend.api.controllers.system_controller import router as system_router
from backend.api.controllers.tasks_controller import router as tasks_router
from backend.api.controllers.watchlist_controller import router as watchlist_router


router = APIRouter()
for feature_router in (
    tasks_router,
    library_router,
    reader_router,
    watchlist_router,
    system_router,
    models_router,
):
    router.include_router(feature_router)
