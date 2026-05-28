from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Any

import mysql.connector
from mysql.connector import MySQLConnection

from src.common.config import get_settings


def quote_identifier(identifier: str) -> str:
    return f"`{identifier.replace('`', '``')}`"


class Database:
    def __init__(self, connection: MySQLConnection):
        self.connection = connection

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def execute(self, query: str, params: Sequence[Any] | None = None):
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query.replace("?", "%s"), params or ())
        return cursor

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()


def connect() -> Database:
    settings = get_settings()
    server_connection = mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        autocommit=True,
    )
    try:
        cursor = server_connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {quote_identifier(settings.mysql_database)}")
    finally:
        server_connection.close()

    connection = mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        autocommit=False,
    )
    return Database(connection)


@contextmanager
def transaction() -> Iterator[Database]:
    db = connect()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
