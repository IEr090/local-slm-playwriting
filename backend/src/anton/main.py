from fastapi import FastAPI

from anton.api.routers.character_router import router as character_router


app = FastAPI(title="Anton")
app.include_router(character_router, prefix="/api")
