import json
import re
import time
from typing import List

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from loguru import logger

from app.config import Settings
from app.domain.models.evaluation import RuleEvaluation
from app.domain.ports import LLMPort
from app.infrastructure.token_limiter import TokenLimiter

# System prompts

_SYSTEM_PROMPT = """\
Act as an expert software engineering professor evaluating source code.

Your task is to evaluate whether a semantic rule is followed within a repository's codebase.
You will be provided with:
1. A repository map (file structure and extracted code symbols).
2. The relevant source code files found via semantic search.
3. A semantic rule that you must evaluate.

You must respond ONLY with a valid JSON (no markdown, no code blocks) using this exact structure:
{
    "verdict": "pass" | "fail" | "partial",
    "confidence": float between 0.0 and 1.0,
    "explanation": "<detailed explanation of why the rule passes or fails, citing specific files and functions>",
    "suggestions": ["<suggestion 1>", "<suggestion 2>"]
}

Verdict criteria:
- "pass": The rule is completely followed in the analyzed code.
- "fail": The rule is NOT followed in the analyzed code.
- "partial": The rule is partially followed, or there is mixed evidence.

If the "suggestions" field is unneeded (e.g., the rule passes completely), return an empty list [].
The explanation must be concise but specific, mentioning relevant files and functions.
Do not include control characters or line breaks inside JSON strings.\
"""

_SUMMARY_SYSTEM_PROMPT = """\
Act as an expert software engineering professor evaluating source code.

You will be provided with a list of semantic rule evaluations performed on a repository.
Generate an executive summary that includes:
1. An overall assessment of the repository.
2. How many rules passed, failed, or partially passed.
3. Main strengths and weaknesses.
4. Top priority recommendations.

Respond in plain text (no JSON). Use clear formatting with sections.\
"""


class GeminiLLMAdapter(LLMPort):
    """LLM adapter using Google Gemini for rule evaluation."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash",
        max_context_tokens: int = 900_000,
        temperature: float = 0.2,
        max_retries: int = 3,
        retry_base_delay: float = 35.0,
    ) -> None:
        settings = Settings()
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        
        self._model_name = model_name
        self._max_context_tokens = max_context_tokens
        self._temperature = temperature
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._limiter = TokenLimiter(max_context_tokens)
        
        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        self._summary_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=_SUMMARY_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
            ),
        )

    # LLMPort interface

    @property
    def name(self) -> str:
        return f"gemini ({self._model_name})"

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
        """Send a single rule + context to Gemini and parse the response."""

        # Build the user prompt with token-limited context
        prompt = self._build_evaluation_prompt(
            rule, repomap, file_contents, repository_url,
        )

        try:
            raw_text = self._call_with_retry(self._model, prompt)
            tokens_used = self._estimate_tokens(prompt + raw_text)

            evaluation = self._parse_response(raw_text)
            evaluation.llm_provider = self.name
            evaluation.tokens_used = tokens_used
            return evaluation

        except Exception as e:
            logger.error(f"Gemini evaluation failed for rule '{rule[:60]}': {e}")
            return RuleEvaluation(
                verdict="fail",
                confidence=0.0,
                explanation=f"Error evaluating with LLM: {str(e)}",
                suggestions=[],
                llm_provider=self.name,
                tokens_used=0,
            )

    def generate_summary(
        self,
        evaluations: List[RuleEvaluation],
        repository_url: str,
    ) -> str:
        """Generate a summary of all evaluations."""
        prompt = self._build_summary_prompt(evaluations, repository_url)

        try:
            return self._call_with_retry(self._summary_model, prompt)
        except Exception as e:
            logger.error(f"Gemini summary generation failed: {e}")
            return self._fallback_summary(evaluations)

    # Retry logic

    def _call_with_retry(self, model, prompt: str) -> str:
        """Call a Gemini model with exponential backoff on 429 errors."""
        last_exc = None
        for attempt in range(self._max_retries + 1):
            try:
                response = model.generate_content(prompt)
                return response.text.strip()
            except ResourceExhausted as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        f"Gemini 429 rate-limit (attempt {attempt + 1}/"
                        f"{self._max_retries + 1}). "
                        f"Retrying in {delay:.0f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Gemini 429 rate-limit: all {self._max_retries + 1} "
                        f"attempts exhausted."
                    )
        if last_exc:
            raise last_exc
        return ""

    # Prompt builders

    def _build_evaluation_prompt(
        self,
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
    ) -> str:
        """Build the user prompt, truncating context to fit token limits."""
        # Reserve tokens for system prompt, rule, framing, and response
        reserved = 1500
        available = self._max_context_tokens - reserved

        # Rule section (always included in full)
        rule_section = f"## Rule to evaluate\n{rule}"
        rule_tokens = self._estimate_tokens(rule_section)
        available -= rule_tokens

        # Repomap -- cap at 15% of total available
        repomap_budget = int(available * 0.15)
        truncated_repomap = self._limiter.truncate_text(
            repomap, max_tokens=repomap_budget,
        )
        repomap_section = f"## Repository Map\n{truncated_repomap}"
        repomap_tokens = self._estimate_tokens(repomap_section)
        available -= repomap_tokens

        # File contents -- fill the rest of the budget
        files_section = self._limiter.fit_file_contents(
            file_contents, max_tokens=available,
        )

        prompt = (
            f"Repository: {repository_url}\n\n"
            f"{repomap_section}\n\n"
            f"## Relevant code files\n{files_section}\n\n"
            f"{rule_section}"
        )
        return prompt

    def _build_summary_prompt(
        self,
        evaluations: List[RuleEvaluation],
        repository_url: str,
    ) -> str:
        lines = [f"Repository: {repository_url}\n"]
        for i, ev in enumerate(evaluations, 1):
            lines.append(
                f"### Rule {i}\n"
                f"- Verdict: {ev.verdict}\n"
                f"- Confidence: {ev.confidence:.0%}\n"
                f"- Explanation: {ev.explanation}\n"
            )
            if ev.suggestions:
                lines.append("- Suggestions: " + "; ".join(ev.suggestions))
            lines.append("")
        return "\n".join(lines)

    # Response parsing

    @staticmethod
    def _parse_response(raw_text: str) -> RuleEvaluation:
        """Parse the JSON response from Gemini into a RuleEvaluation."""
        try:
            # Strip potential markdown fences
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)

            data = json.loads(cleaned)
            verdict = data.get("verdict", "fail").lower()
            if verdict not in ("pass", "fail", "partial"):
                verdict = "fail"

            confidence = float(data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))

            return RuleEvaluation(
                verdict=verdict,
                confidence=confidence,
                explanation=data.get("explanation", ""),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return RuleEvaluation(
                verdict="fail",
                confidence=0.0,
                explanation=f"Error parsing LLM response: {raw_text[:500]}",
                suggestions=[],
            )

    # Fallback summary

    @staticmethod
    def _fallback_summary(evaluations: List[RuleEvaluation]) -> str:
        """Generate a basic summary without calling the LLM."""
        total = len(evaluations)
        passed = sum(1 for e in evaluations if e.verdict == "pass")
        failed = sum(1 for e in evaluations if e.verdict == "fail")
        partial = sum(1 for e in evaluations if e.verdict == "partial")

        return (
            f"Evaluation Summary\n"
            f"==================\n\n"
            f"Total evaluated rules: {total}\n"
            f"- Passed: {passed}\n"
            f"- Failed: {failed}\n"
            f"- Partially passed: {partial}\n\n"
            f"(Could not generate a detailed summary with the LLM.)"
        )

    # Token estimation

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate: ~4 chars per token for code."""
        return len(text) // 4
