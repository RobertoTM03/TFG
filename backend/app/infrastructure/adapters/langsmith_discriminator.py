import json
from typing import TYPE_CHECKING

from loguru import logger

from app.domain.models.evaluation import RuleEvaluation

if TYPE_CHECKING:
    from app.domain.ports import LLMPort


class LangSmithDiscriminator:
    """Adjudicates disagreements between primary and secondary LLM evaluations."""

    def __init__(self, discriminator_llm: "LLMPort", prompt_name: str) -> None:
        self._llm = discriminator_llm
        self._prompt_name = prompt_name
        self._prompt_template = self._load_prompt(prompt_name)

    @staticmethod
    def _load_prompt(prompt_name: str) -> object:
        try:
            from langsmith import Client
            client = Client()
            prompt = client.pull_prompt(prompt_name)
            logger.info(f"Loaded discriminator prompt '{prompt_name}' from LangSmith Hub")
            return prompt
        except Exception as exc:
            logger.warning(
                f"Could not load discriminator prompt '{prompt_name}' from LangSmith "
                f"({exc}). Built-in fallback template will be used."
            )
            return None

    def adjudicate(
        self,
        rule: str,
        primary: RuleEvaluation,
        secondary: RuleEvaluation,
    ) -> RuleEvaluation:
        """Invoke the discriminator and return a RuleEvaluation with its verdict."""
        prompt_text = self._render_prompt(rule, primary, secondary)

        try:
            raw = self._llm.evaluate_rule(
                rule=prompt_text,
                repomap="",
                file_contents=[],
                repository_url="",
            )
            # The discriminator model returns its own RuleEvaluation; attach metadata.
            raw.llm_provider = self._llm.name
            return raw
        except Exception as exc:
            raise RuntimeError(f"Discriminator adjudication failed: {exc}") from exc

    def _render_prompt(
        self,
        rule: str,
        primary: RuleEvaluation,
        secondary: RuleEvaluation,
    ) -> str:
        """Format the LangSmith prompt template with evaluation data.

        Falls back to a built-in template if the hub prompt does not expose
        a plain-text format method.
        """
        try:
            if self._prompt_template and hasattr(self._prompt_template, "format"):
                return self._prompt_template.format(
                    rule=rule,
                    primary_verdict=primary.verdict,
                    primary_explanation=primary.explanation,
                    secondary_verdict=secondary.verdict,
                    secondary_explanation=secondary.explanation,
                )
        except Exception:
            pass

        # Built-in fallback
        return (
            f"You are a senior software engineering expert adjudicating two conflicting "
            f"evaluations of the same semantic rule.\n\n"
            f"Rule: {rule}\n\n"
            f"Evaluation A (verdict: {primary.verdict}):\n{primary.explanation}\n\n"
            f"Evaluation B (verdict: {secondary.verdict}):\n{secondary.explanation}\n\n"
            f"Respond ONLY with valid JSON:\n"
            f'{{"verdict": "pass"|"fail"|"partial", '
            f'"explanation": "<your reasoning>", '
            f'"suggestions": []}}'
        )
