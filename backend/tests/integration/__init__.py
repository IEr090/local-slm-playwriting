from anton.infrastructure.config import Settings
from anton.infrastructure.slm import SLMClient, create_slm_client


def create_test_client() -> SLMClient:
    """Create the model client for integration tests: the configured model, always without thinking."""
    return create_slm_client(Settings(thinking=False))
