from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool
from loguru import logger

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.health_check import HealthCheckPort

_POOL_MIN = 2
_POOL_MAX = 10


class Database(ConnectionProviderPort, HealthCheckPort):
    """Connection pool provider and health check. All SQL logic lives in repositories/."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
    ) -> None:
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=_POOL_MIN,
            maxconn=_POOL_MAX,
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
        )
        logger.info(f"Database connection pool created (min={_POOL_MIN}, max={_POOL_MAX})")

    def close(self) -> None:
        self._pool.closeall()
        logger.info("Database connection pool closed")

    @contextmanager
    def connection(self) -> Generator:
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    def check_health(self) -> bool:
        try:
            with self.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            return True
        except Exception:
            return False
