from typing import List

CHARS_PER_TOKEN = 4


class TokenLimiter:
    """Manages token budgets for LLM context windows."""

    def __init__(self, max_tokens: int) -> None:
        self._max_tokens = max_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate the number of tokens in a text string."""
        return len(text) // CHARS_PER_TOKEN

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within a token budget."""
        max_chars = max_tokens * CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        
        # Cut at last newline to avoid breaking mid-line
        last_nl = truncated.rfind("\n")
        if last_nl > max_chars * 0.5:
            truncated = truncated[:last_nl]

        return truncated + "\n... (content truncated due to token limit)"

    def fit_file_contents(
        self,
        file_contents: List[str],
        max_tokens: int,
    ) -> str:
        """Fit as many file contents as possible within a token budget."""
        if not file_contents:
            return "(No relevant files found)"

        max_chars = max_tokens * CHARS_PER_TOKEN
        result_parts: List[str] = []
        chars_used = 0
        skipped_files: List[str] = []

        for content in file_contents:
            content_chars = len(content)

            if chars_used + content_chars <= max_chars:
                # Fits entirely
                result_parts.append(content)
                chars_used += content_chars
                
            elif chars_used < max_chars:
                # Partial fit -- truncate this file
                remaining = max_chars - chars_used
                truncated = content[:remaining]
                
                last_nl = truncated.rfind("\n")
                if last_nl > remaining * 0.3:
                    truncated = truncated[:last_nl]
                    
                result_parts.append(
                    truncated + "\n... (file truncated due to token limit)"
                )
                chars_used = max_chars
                
            else:
                # No space left -- extract filename from header if possible
                first_line = content.split("\n", 1)[0]
                skipped_files.append(first_line)

        result = "\n\n".join(result_parts)

        if skipped_files:
            result += (
                "\n\n--- Files skipped due to token limit ---\n"
                + "\n".join(skipped_files)
            )

        return result
