class LLMUnavailableError(Exception):
    """Raised when the LLM service is temporarily unavailable (rate limit or server error)
    and all internal retries have been exhausted."""
