from abc import ABC, abstractmethod
from typing import List

from app.domain.models.evaluation import RuleEvaluation


class LLMPort(ABC):
    """Port for LLM-based rule evaluation."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def max_context_tokens(self) -> int: ...

    @abstractmethod
    def evaluate_rule(
        self,
        rule: str,
        repomap: str,
        file_contents: List[str],
        repository_url: str,
    ) -> RuleEvaluation: ...

