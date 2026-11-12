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


class StoryNotFoundError(NotFoundError):
    """Represent a play that has not been started yet."""


class ActNotFoundError(NotFoundError):
    """Represent an act number that is not in the Story Bible."""


class SceneNotFoundError(NotFoundError):
    """Represent a scene number that is not in the act."""


class PlaceNotFoundError(NotFoundError):
    """Represent a place id that is not in the Story Bible."""


class StoryOrderError(Exception):
    """Represent a step of the Story Bible that is not possible in the current state, e.g. writing text before all scenes are approved."""


class PdfRenderError(Exception):
    """Represent a play that the PDF renderer could not typeset."""
