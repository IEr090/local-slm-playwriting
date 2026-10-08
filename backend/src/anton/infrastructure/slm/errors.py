class SLMError(Exception):
    """Represent a failure of the small language model."""


class SLMUnavailableError(SLMError):
    """Represent a model server that cannot be reached."""


class SLMResponseError(SLMError):
    """Represent a model server or model that returned an unusable response."""
