from typing import Protocol, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class SLMClient(Protocol):
    """Define an interface for a small language model."""

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        """Generate and validate a structured response."""
        ...