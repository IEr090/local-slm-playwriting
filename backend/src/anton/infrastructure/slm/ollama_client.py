from typing import TypeVar

from ollama import AsyncClient
from pydantic import BaseModel

from .client import SLMClient


T = TypeVar("T", bound=BaseModel)


class OllamaClient(SLMClient):
    """Implement structured SLM generation with Ollama."""

    def __init__(self, model: str) -> None:
        """Initialize the client with an Ollama model name."""
        self.model = model
        self.client = AsyncClient()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        """Generate and validate a structured response."""
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
        )

        return response_model.model_validate_json(response.message.content)
