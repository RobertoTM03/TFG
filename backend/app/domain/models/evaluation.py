from dataclasses import dataclass, field
from typing import List


@dataclass
class RuleEvaluation:
    """Structured result from an LLM evaluating a single semantic rule."""

    verdict: str = "fail"  # "pass" | "fail" | "partial"
    confidence: float = 0.0
    explanation: str = ""
    suggestions: List[str] = field(default_factory=list)
    llm_provider: str = ""
    tokens_used: int = 0
