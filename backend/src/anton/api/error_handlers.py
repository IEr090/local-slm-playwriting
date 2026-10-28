from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from anton.api.disconnect import ClientDisconnectedError
from anton.errors import (
    ActNotFoundError,
    NotFoundError,
    PlaceNotFoundError,
    SceneNotFoundError,
    SLMResponseError,
    SLMUnavailableError,
    StoryNotFoundError,
    StoryOrderError,
)


def add_error_handlers(app: FastAPI) -> None:
    """Turn application errors into responses with a message for the user and a technical detail."""

    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, error: NotFoundError) -> JSONResponse:
        """Answer 404 when the requested cast or character does not exist."""
        return JSONResponse(
            status_code=404,
            content={"message": "Nothing found. Generate or create characters first.", "detail": str(error)},
        )

    @app.exception_handler(StoryNotFoundError)
    async def story_not_found(request: Request, error: StoryNotFoundError) -> JSONResponse:
        """Answer 404 when no play has been started yet."""
        return JSONResponse(
            status_code=404,
            content={"message": "No play yet. Generate the characters first.", "detail": str(error)},
        )

    @app.exception_handler(ActNotFoundError)
    async def act_not_found(request: Request, error: ActNotFoundError) -> JSONResponse:
        """Answer 404 when the requested act does not exist."""
        return JSONResponse(
            status_code=404,
            content={"message": "This act does not exist.", "detail": str(error)},
        )

    @app.exception_handler(SceneNotFoundError)
    async def scene_not_found(request: Request, error: SceneNotFoundError) -> JSONResponse:
        """Answer 404 when the requested scene does not exist."""
        return JSONResponse(
            status_code=404,
            content={"message": "This scene does not exist.", "detail": str(error)},
        )

    @app.exception_handler(PlaceNotFoundError)
    async def place_not_found(request: Request, error: PlaceNotFoundError) -> JSONResponse:
        """Answer 404 when a scene names a place that does not exist."""
        return JSONResponse(
            status_code=404,
            content={"message": "This place does not exist.", "detail": str(error)},
        )

    @app.exception_handler(StoryOrderError)
    async def story_order(request: Request, error: StoryOrderError) -> JSONResponse:
        """Answer 409 when a step is asked for before the steps it builds on are done."""
        return JSONResponse(
            status_code=409,
            content={"message": str(error), "detail": type(error).__name__},
        )

    @app.exception_handler(ClientDisconnectedError)
    async def client_disconnected(request: Request, error: ClientDisconnectedError) -> Response:
        """Answer 499 (client closed request) for the log; nobody is left to read it."""
        return Response(status_code=499)

    @app.exception_handler(SLMUnavailableError)
    async def slm_unavailable(request: Request, error: SLMUnavailableError) -> JSONResponse:
        """Answer 503 when the model server cannot be reached."""
        return JSONResponse(
            status_code=503,
            content={"message": "Could not reach the local model. Is Ollama running?", "detail": str(error)},
        )

    @app.exception_handler(SLMResponseError)
    async def slm_response(request: Request, error: SLMResponseError) -> JSONResponse:
        """Answer 502 when the model server or the model returned an unusable response."""
        return JSONResponse(
            status_code=502,
            content={"message": "The local model returned an unusable answer. Please try again.", "detail": str(error)},
        )
