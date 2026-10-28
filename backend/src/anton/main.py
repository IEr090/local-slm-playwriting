from fastapi import FastAPI

from anton.api.error_handlers import add_error_handlers
from anton.api.routers.character_router import router as character_router
from anton.api.routers.story_router import router as story_router


app = FastAPI(title="Anton")
app.include_router(character_router, prefix="/api")
app.include_router(story_router, prefix="/api")
add_error_handlers(app)
