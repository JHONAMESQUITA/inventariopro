import sqlite3
import threading
from typing import Optional


class DatabaseConnection:
    _instances: dict = {}
    _lock = threading.Lock()

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path: str) -> "DatabaseConnection":
        if db_path not in cls._instances:
            with cls._lock:
                if db_path not in cls._instances:
                    cls._instances[db_path] = cls(db_path)
        return cls._instances[db_path]

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    @classmethod
    def close_all(cls) -> None:
        for inst in cls._instances.values():
            inst.close()
        cls._instances.clear()

    @classmethod
    def close_path(cls, db_path: str) -> None:
        if db_path in cls._instances:
            cls._instances[db_path].close()
            del cls._instances[db_path]


def db_query(sql: str, params: tuple = (), fetchall: bool = True, db_path: Optional[str] = None):
    from config import DB_PATH
    path = db_path or DB_PATH
    conn = DatabaseConnection.get_instance(path).get_connection()
    c = conn.cursor()
    c.execute(sql, params)
    if fetchall:
        return c.fetchall()
    return c.fetchone()


def db_execute(sql: str, params: tuple = (), db_path: Optional[str] = None):
    from config import DB_PATH
    path = db_path or DB_PATH
    conn = DatabaseConnection.get_instance(path).get_connection()
    try:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()
        return c.lastrowid
    except sqlite3.Error as e:
        conn.rollback()
        raise e
