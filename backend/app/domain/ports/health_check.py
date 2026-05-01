from abc import ABC, abstractmethod


class HealthCheckPort(ABC):
    @abstractmethod
    def check_health(self) -> bool: ...
