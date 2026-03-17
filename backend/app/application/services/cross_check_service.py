from app.domain.models.cross_check import CrossCheckedEvaluation
from app.domain.models.evaluation import RuleEvaluation

# Higher rank = worse verdict (conservative strategy picks the highest rank)
_VERDICT_RANK = {"pass": 0, "partial": 1, "fail": 2}

_CONFIDENCE_GAP_THRESHOLD = 0.3


class CrossCheckService:
    """Reconciles two independent LLM evaluations of the same rule.

    Strategy selection:
      - "consensus"    : both models agree on the verdict -> use primary.
      - "confidence"   : confidence gap > 0.3 -> use the more confident model.
      - "conservative" : disagreement with no clear winner -> use the worst verdict.
    """

    def reconcile(
        self,
        primary: RuleEvaluation,
        secondary: RuleEvaluation,
    ) -> CrossCheckedEvaluation:
        agreement = primary.verdict == secondary.verdict

        if agreement:
            strategy = "consensus"
            final = primary

        elif abs(primary.confidence - secondary.confidence) > _CONFIDENCE_GAP_THRESHOLD:
            strategy = "confidence"
            final = (
                primary
                if primary.confidence >= secondary.confidence
                else secondary
            )

        else:
            strategy = "conservative"
            primary_rank = _VERDICT_RANK.get(primary.verdict, 1)
            secondary_rank = _VERDICT_RANK.get(secondary.verdict, 1)
            final = primary if primary_rank >= secondary_rank else secondary

        return CrossCheckedEvaluation(
            final=final,
            primary=primary,
            secondary=secondary,
            strategy_used=strategy,
            agreement=agreement,
        )
