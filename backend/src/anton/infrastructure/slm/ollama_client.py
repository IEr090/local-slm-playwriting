from typing import TypeVar

from ollama import AsyncClient
from pydantic import BaseModel

from .client import SLMClient


T = TypeVar("T", bound=BaseModel)


class OllamaClient(SLMClient):
    """Implement structured SLM generation with Ollama."""

    def __init__(self, model: str, num_ctx: int) -> None:
        """Initialize the client with an Ollama model name and its context window size in tokens."""
        self.model = model
        self.num_ctx = num_ctx
        self.client = AsyncClient()

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
        think: bool,
    ) -> T:
        """Generate and validate a structured response, optionally letting the model think first."""
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
            think=think,
            options={"num_ctx": self.num_ctx},
        )

        return response_model.model_validate_json(response.message.content)
