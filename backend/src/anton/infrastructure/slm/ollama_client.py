import logging
from typing import TypeVar

from ollama import AsyncClient, ResponseError
from pydantic import BaseModel, ValidationError

from .client import SLMClient
from anton.errors import SLMResponseError, SLMUnavailableError


logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class OllamaClient(SLMClient):
    """Implement structured SLM generation with Ollama."""

    def __init__(self, model: str, num_ctx: int, thinking: bool = True) -> None:
        """Initialize the client with an Ollama model name, its context window size and whether thinking is allowed."""
        self.model = model
        self.num_ctx = num_ctx
        self.thinking = thinking
        self.client = AsyncClient()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        think: bool,
    ) -> T:
        """Generate and validate a structured response, optionally letting the model think first.

        When thinking is switched off in the settings, the model never thinks, whatever the caller asks.
        """
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                format=response_model.model_json_schema(),
                think=think and self.thinking,
                options={"num_ctx": self.num_ctx},
            )
        except ConnectionError as error:
            logger.warning("Ollama is not reachable model=%s", self.model)
            raise SLMUnavailableError("Ollama is not reachable") from error
        except ResponseError as error:
            logger.warning("Ollama returned an error model=%s status_code=%s", self.model, error.status_code)
            raise SLMResponseError(f"Ollama: {error.error}") from error

        try:
            return response_model.model_validate_json(response.message.content)
        except ValidationError as error:
            logger.warning(
                "Model returned an invalid response model=%s schema=%s", self.model, response_model.__name__,
            )
            raise SLMResponseError(f"{self.model} returned an invalid {response_model.__name__}") from error

    async def close(self) -> None:
        """Close the connection to the Ollama server."""
        await self.client.close()
