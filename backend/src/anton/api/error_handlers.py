from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from anton.infrastructure.slm import SLMResponseError, SLMUnavailableError


def add_error_handlers(app: FastAPI) -> None:
    """Turn model failures into responses with a message for the user and a technical detail."""

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
