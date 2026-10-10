class SLMError(Exception):
    """Represent a failure of the small language model."""


class SLMUnavailableError(SLMError):
    """Represent a model server that cannot be reached."""


class SLMResponseError(SLMError):
    """Represent a model server or model that returned an unusable response."""


class NotFoundError(Exception):
    """Represent something the user asked for that does not exist."""


class CastNotFoundError(NotFoundError):
    """Represent a cast that has not been generated yet."""


class CharacterNotFoundError(NotFoundError):
    """Represent a character id that is not in the saved cast."""
