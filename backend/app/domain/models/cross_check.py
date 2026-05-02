from dataclasses import dataclass
from typing import Optional

from app.domain.models.evaluation import RuleEvaluation


@dataclass
class CrossCheckedEvaluation:
    """Log of the cross-check process for a single rule."""

    primary: RuleEvaluation
    secondary: RuleEvaluation
    agreement: bool
    discriminator_used: bool
    discriminator_model: Optional[str] = None
    discriminator_reasoning: Optional[str] = None
