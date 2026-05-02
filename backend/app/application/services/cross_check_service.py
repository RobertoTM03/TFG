from loguru import logger

from app.domain.models.cross_check import CrossCheckedEvaluation
from app.domain.models.evaluation import RuleEvaluation
from app.infrastructure.adapters.langsmith_discriminator import LangSmithDiscriminator

_VERDICT_RANK = {"pass": 0, "partial": 1, "fail": 2}


class CrossCheckService:
    """Reconciles two independent LLM evaluations of the same rule.

    If both models agree: consensus — primary evaluation is authoritative.
    If they disagree: discriminator LLM from LangSmith Hub breaks the tie.
    """

    def __init__(self, discriminator: LangSmithDiscriminator) -> None:
        self._discriminator = discriminator

    def reconcile(
        self,
        rule: str,
        primary: RuleEvaluation,
        secondary: RuleEvaluation,
    ) -> tuple[RuleEvaluation, CrossCheckedEvaluation]:
        """Return (final_evaluation, cross_check_log).

        final_evaluation is the authoritative result to store in RuleValidation.
        cross_check_log is the audit trail.
        """
        agreement = primary.verdict == secondary.verdict

        if agreement:
            return primary, CrossCheckedEvaluation(
                primary=primary,
                secondary=secondary,
                agreement=True,
                discriminator_used=False,
            )

        try:
            discriminator_eval = self._discriminator.adjudicate(rule, primary, secondary)
            cross_check = CrossCheckedEvaluation(
                primary=primary,
                secondary=secondary,
                agreement=False,
                discriminator_used=True,
                discriminator_model=discriminator_eval.llm_provider,
                discriminator_reasoning=discriminator_eval.explanation,
            )
            return discriminator_eval, cross_check
        except Exception as exc:
            logger.error(f"Discriminator unavailable, falling back to conservative verdict: {exc}")
            fallback = max(primary, secondary, key=lambda e: _VERDICT_RANK.get(e.verdict, 1))
            cross_check = CrossCheckedEvaluation(
                primary=primary,
                secondary=secondary,
                agreement=False,
                discriminator_used=False,
                discriminator_reasoning=f"Discriminator unavailable: {exc}",
            )
            return fallback, cross_check
