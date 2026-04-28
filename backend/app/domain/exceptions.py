class LLMUnavailableError(Exception):
    """Raised when the LLM service is temporarily unavailable (rate limit or server error)
    and all internal retries have been exhausted."""


class EmbeddingUnavailableError(Exception):
    """Raised when the embedding service is temporarily unavailable and all
    internal retries have been exhausted."""
