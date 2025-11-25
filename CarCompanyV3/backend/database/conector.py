from typing import Any, Optional
import psycopg2
from psycopg2.extras import DictCursor


class DatabaseManager:
    """Classe de Gerenciamento do database"""

    def __init__(self) -> None:
        self.conn = psycopg2.connect(
            dbname="carcompany",
            user="postgres",
            host="127.0.0.1",
            password="0205",
            port=5432,
            client_encoding='utf8'
        )
        self.cursor = self.conn.cursor(cursor_factory=DictCursor)
        self.cursor.execute("SET search_path TO aluguel;")
        self.conn.commit()

    def _exec(self, query: str, params: Optional[tuple] = None):
        try:
            self.cursor.execute(query, params)
            return True
        except Exception as e:
            print("Erro ao executar:", e)
            self.conn.rollback()
            return False

    def execute_statement(self, query: str, params: Optional[tuple] = None) -> bool:
        if not self._exec(query, params):
            return False
        self.conn.commit()
        return True

    def execute_select_all(self, query: str, params: Optional[tuple] = None):
        self._exec(query, params)
        return [dict(row) for row in self.cursor.fetchall()]

    def execute_select_one(self, query: str, params: Optional[tuple] = None):
        self._exec(query, params)
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def execute_insert_returning(self, query: str, params: Optional[tuple] = None):
        try:
            self.cursor.execute(query, params)
            row = self.cursor.fetchone()
            self.conn.commit()
            return dict(row) if row else None
        except Exception as e:
            print("Erro ao executar (RETURNING):", e)
            self.conn.rollback()
            return None
