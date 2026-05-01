from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator


class ConnectionProviderPort(ABC):
    @contextmanager
    @abstractmethod
    def connection(self) -> Generator:
        """Yield a database connection from the pool."""
        ...
