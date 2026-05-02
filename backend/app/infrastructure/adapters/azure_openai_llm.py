import json
import re
import time
from typing import List

from openai import AzureOpenAI, APIStatusError, APIConnectionError
from loguru import logger

from app.domain.exceptions import LLMUnavailableError
from app.domain.models.evaluation import RuleEvaluation
from app.domain.ports import LLMPort
from app.infrastructure.token_limiter import TokenLimiter
from app.domain.llm_prompts import LLM_SYSTEM_PROMPT as _SYSTEM_PROMPT

_SERVER_ERROR_MAX_RETRIES = 2


class AzureOpenAILLMAdapter(LLMPort):
    """LLM adapter using Azure OpenAI for rule evaluation.

    Receives a shared AzureOpenAI client — do not instantiate the client here.
    Multiple instances (different deployments) safely share the same client.
    """

    def __init__(
        self,
        client: AzureOpenAI,
        deployment: str,
        max_context_tokens: int = 200_000,
        temperature: float = 0.2,
        supports_temperature: bool = False,
        max_retries: int = 3,
        retry_base_delay: float = 35.0,
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._max_context_tokens = max_context_tokens
        self._temperature = temperature
        self._supports_temperature = supports_temperature
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._limiter = TokenLimiter(max_context_tokens)

    # LLMPort interface

    @property
    def name(self) -> str:
        return f"azure ({self._deployment})"

    @property
    def max_context_tokens(self) -> int:
        return self._max_context_tokens

    def evaluate_rule(
        self,
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
    ) -> RuleEvaluation:
        prompt = self._build_evaluation_prompt(rule, repomap, file_contents, repository_url)

        try:
            raw_text = self._call_with_retry(prompt)
            tokens_used = self._estimate_tokens(prompt + raw_text)
            evaluation = self._parse_response(raw_text)
            evaluation.llm_provider = self.name
            evaluation.tokens_used = tokens_used
            return evaluation

        except LLMUnavailableError:
            raise
        except Exception as e:
            logger.error(f"Azure OpenAI evaluation failed for rule '{rule[:60]}': {e}")
            return RuleEvaluation(
                verdict="fail",
                explanation=f"Error evaluating with LLM: {str(e)}",
                suggestions=[],
                llm_provider=self.name,
                tokens_used=0,
            )

    # Retry logic

    def _call_with_retry(self, prompt: str) -> str:
        rate_limit_attempts = 0
        server_error_attempts = 0

        while True:
            try:
                kwargs = dict(
                    model=self._deployment,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_completion_tokens=8000,
                )
                if self._supports_temperature:
                    kwargs["temperature"] = self._temperature
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()

            except APIStatusError as exc:
                if exc.status_code == 429:
                    if rate_limit_attempts >= self._max_retries:
                        logger.error(
                            f"Azure OpenAI 429 rate-limit: all {self._max_retries + 1} "
                            f"attempts exhausted."
                        )
                        raise LLMUnavailableError(str(exc)) from exc
                    delay = self._retry_base_delay * (2 ** rate_limit_attempts)
                    rate_limit_attempts += 1
                    logger.warning(
                        f"Azure OpenAI 429 rate-limit (attempt {rate_limit_attempts}/"
                        f"{self._max_retries + 1}). Retrying in {delay:.0f}s..."
                    )
                    time.sleep(delay)
                elif exc.status_code in (500, 503):
                    if server_error_attempts >= _SERVER_ERROR_MAX_RETRIES:
                        logger.error(
                            f"Azure OpenAI {exc.status_code} server error: all "
                            f"{_SERVER_ERROR_MAX_RETRIES + 1} attempts exhausted."
                        )
                        raise LLMUnavailableError(str(exc)) from exc
                    delay = 5.0 * (2 ** server_error_attempts)
                    server_error_attempts += 1
                    logger.warning(
                        f"Azure OpenAI {exc.status_code} server error "
                        f"(attempt {server_error_attempts}/"
                        f"{_SERVER_ERROR_MAX_RETRIES + 1}). Retrying in {delay:.0f}s..."
                    )
                    time.sleep(delay)
                else:
                    raise

            except APIConnectionError as exc:
                if server_error_attempts >= _SERVER_ERROR_MAX_RETRIES:
                    raise LLMUnavailableError(str(exc)) from exc
                delay = 5.0 * (2 ** server_error_attempts)
                server_error_attempts += 1
                logger.warning(
                    f"Azure OpenAI connection error (attempt {server_error_attempts}/"
                    f"{_SERVER_ERROR_MAX_RETRIES + 1}). Retrying in {delay:.0f}s..."
                )
                time.sleep(delay)

    # Prompt builder (same logic as GeminiLLMAdapter)

    def _build_evaluation_prompt(
        self,
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
    ) -> str:
        reserved = 1500
        available = self._max_context_tokens - reserved

        rule_section = f"## Rule to evaluate\n{rule}"
        available -= self._estimate_tokens(rule_section)

        repomap_budget = int(available * 0.15)
        truncated_repomap = self._limiter.truncate_text(repomap, max_tokens=repomap_budget)
        repomap_section = f"## Repository Map\n{truncated_repomap}"
        available -= self._estimate_tokens(repomap_section)

        files_section = self._limiter.fit_file_contents(file_contents, max_tokens=available)

        return (
            f"Repository: {repository_url}\n\n"
            f"{repomap_section}\n\n"
            f"## Relevant code files\n{files_section}\n\n"
            f"{rule_section}"
        )

    # Response parsing (same logic as GeminiLLMAdapter)

    @staticmethod
    def _parse_response(raw_text: str) -> RuleEvaluation:
        try:
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            data = json.loads(cleaned)
            verdict = data.get("verdict", "fail").lower()
            if verdict not in ("pass", "fail", "partial"):
                verdict = "fail"

            return RuleEvaluation(
                verdict=verdict,
                explanation=data.get("explanation", ""),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse Azure OpenAI response: {e}")
            return RuleEvaluation(
                verdict="fail",
                explanation=f"Error parsing LLM response: {raw_text[:500]}",
                suggestions=[],
            )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return len(text) // 4
