from typing import Any, Dict, List, Optional, Tuple

import psycopg2.extras

from app.domain.ports.connection_provider import ConnectionProviderPort
from app.domain.ports.rule_repository import RuleRepositoryPort

_RULE_SORT_COLUMNS: Dict[str, str] = {
    "position": "position",
    "rule_text": "rule_text",
}
_RULE_SORT_DEFAULT = "position"


class RuleRepository(RuleRepositoryPort):
    def __init__(self, conn_provider: ConnectionProviderPort) -> None:
        self._conn = conn_provider.connection

    def get_rules(
        self,
        user_id: str,
        repo_full_name: str,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "position",
        sort_order: str = "asc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        col = _RULE_SORT_COLUMNS.get(sort_by, _RULE_SORT_DEFAULT)
        order = "ASC" if sort_order.lower() == "asc" else "DESC"
        order_clause = f"{col} {order}"
        offset = (page - 1) * page_size
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""SELECT *, COUNT(*) OVER () AS _total
                        FROM rules
                        WHERE user_id = %s AND repository_full_name = %s
                        ORDER BY {order_clause}
                        LIMIT %s OFFSET %s""",
                    (user_id, repo_full_name, page_size, offset),
                )
                raw = cur.fetchall()
            total = raw[0]["_total"] if raw else 0
            rows = [{k: v for k, v in r.items() if k != "_total"} for r in raw]
            return rows, total

    def count_rules(self, user_id: str, repo_full_name: str) -> int:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*) FROM rules
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                return cur.fetchone()[0]

    def create_rule(
        self, user_id: str, repo_full_name: str, rule_text: str,
    ) -> Dict[str, Any]:
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT COALESCE(MAX(position), -1) + 1 AS next_pos
                       FROM rules
                       WHERE user_id = %s AND repository_full_name = %s""",
                    (user_id, repo_full_name),
                )
                next_pos = cur.fetchone()["next_pos"]
                cur.execute(
                    """INSERT INTO rules
                           (user_id, repository_full_name, rule_text, position, enabled)
                       VALUES (%s, %s, %s, %s, TRUE)
                       RETURNING *""",
                    (user_id, repo_full_name, rule_text, next_pos),
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row)

    def update_rule(
        self,
        rule_id: str,
        user_id: str,
        rule_text: str = None,
        enabled: bool = None,
    ) -> dict | None:
        sets = []
        vals = []
        if rule_text is not None:
            sets.append("rule_text = %s")
            vals.append(rule_text)
        if enabled is not None:
            sets.append("enabled = %s")
            vals.append(enabled)
        if not sets:
            return None
        vals.extend([rule_id, user_id])
        with self._conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    f"""UPDATE rules SET {', '.join(sets)}
                        WHERE id = %s AND user_id = %s
                        RETURNING *""",
                    vals,
                )
                row = cur.fetchone()
            conn.commit()
            return dict(row) if row else None

    def delete_rule(self, rule_id: str, user_id: str) -> bool:
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM rules WHERE id = %s AND user_id = %s",
                    (rule_id, user_id),
                )
                deleted = cur.rowcount > 0
            conn.commit()
            return deleted
