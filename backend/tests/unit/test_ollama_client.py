from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from ollama import ResponseError

from anton.application.llm_schemas.character_generation import GeneratedCard
from anton.infrastructure.slm import OllamaClient, SLMResponseError, SLMUnavailableError
from tests.unit.fakes import CARD


class OllamaClientErrorTest(IsolatedAsyncioTestCase):
    """Test how Ollama failures are turned into SLM errors."""

    async def asyncSetUp(self) -> None:
        """Create the client with a replaced Ollama chat call."""
        self.client = OllamaClient(model="qwen3:4b", num_ctx=1024)
        self.client.client.chat = AsyncMock()

    async def generate(self) -> GeneratedCard:
        """Generate a card with the replaced chat call."""
        return await self.client.generate("system", "user", GeneratedCard, think=False)

    async def test_returns_validated_response(self) -> None:
        """Parse the model answer into the response model."""
        self.client.client.chat.return_value = SimpleNamespace(message=SimpleNamespace(content=CARD.model_dump_json()))

        self.assertEqual(await self.generate(), CARD)

    async def test_connection_error_becomes_unavailable(self) -> None:
        """Report an unreachable Ollama server."""
        self.client.client.chat.side_effect = ConnectionError("Failed to connect to Ollama.")

        with self.assertRaises(SLMUnavailableError):
            await self.generate()

    async def test_response_error_becomes_response_error(self) -> None:
        """Keep the reason Ollama gives, e.g. a missing model."""
        self.client.client.chat.side_effect = ResponseError('{"error": "model \\"qwen3:4b\\" not found"}', 404)

        with self.assertRaisesRegex(SLMResponseError, 'model "qwen3:4b" not found'):
            await self.generate()

    async def test_invalid_answer_becomes_response_error(self) -> None:
        """Report an answer that does not match the response model."""
        self.client.client.chat.return_value = SimpleNamespace(message=SimpleNamespace(content='{"tagline": 1}'))

        with self.assertRaisesRegex(SLMResponseError, "invalid GeneratedCard"):
            await self.generate()
