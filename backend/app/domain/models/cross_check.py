from dataclasses import dataclass

from app.domain.models.evaluation import RuleEvaluation


@dataclass
class CrossCheckedEvaluation:
    """Result of reconciling two independent LLM evaluations of the same rule."""

    final: RuleEvaluation      # Reconciled evaluation used as the official result
    primary: RuleEvaluation    # Raw output from the primary model
    secondary: RuleEvaluation  # Raw output from the secondary model
    strategy_used: str         # "consensus" | "confidence" | "conservative"
    agreement: bool            # True when both models returned the same verdict
