import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from anton.api.dependencies import get_slm_client
from anton.api.error_handlers import add_error_handlers
from anton.api.routers.act_router import router as act_router
from anton.api.routers.character_router import router as character_router
from anton.api.routers.story_router import router as story_router


logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Close the connection to the model server when the application stops."""
    yield
    if get_slm_client.cache_info().currsize:
        await get_slm_client().close()


app = FastAPI(title="Anton", lifespan=lifespan)
app.include_router(character_router, prefix="/api")
app.include_router(story_router, prefix="/api")
app.include_router(act_router, prefix="/api")
add_error_handlers(app)
