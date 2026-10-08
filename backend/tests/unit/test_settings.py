import os
from unittest import TestCase
from unittest.mock import patch

from anton.infrastructure.config import Settings
from anton.infrastructure.slm import OllamaClient, create_slm_client


class SettingsTest(TestCase):
    """Test reading the settings from the environment."""

    def test_defaults(self) -> None:
        """Use qwen3:4b with thinking when nothing is configured."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings(_env_file=None)

        self.assertEqual(settings.ollama_model, "qwen3:4b")
        self.assertEqual(settings.ollama_num_ctx, 16384)
        self.assertTrue(settings.thinking)

    def test_reads_environment(self) -> None:
        """Switch thinking off and change the model through ANTON_* variables."""
        environment = {"ANTON_THINKING": "false", "ANTON_OLLAMA_MODEL": "qwen3:1.7b"}
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings(_env_file=None)

        self.assertFalse(settings.thinking)
        self.assertEqual(settings.ollama_model, "qwen3:1.7b")

    def test_client_follows_settings(self) -> None:
        """Create the Ollama client with the configured model and thinking switch."""
        client = create_slm_client(Settings(_env_file=None, ollama_model="qwen3:1.7b", ollama_num_ctx=2048, thinking=False))

        self.assertIsInstance(client, OllamaClient)
        self.assertEqual((client.model, client.num_ctx, client.thinking), ("qwen3:1.7b", 2048, False))
