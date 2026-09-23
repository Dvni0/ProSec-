import hashlib
import sqlite3
from pathlib import Path


class UserDatabase:
    def __init__(self):
        self.database_path = Path(__file__).resolve().parents[2] / "users.db"
        self._initialize()

    def _initialize(self):
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    department TEXT NOT NULL,
                    shift TEXT NOT NULL,
                    experience_years INTEGER NOT NULL,
                    compliance TEXT NOT NULL,
                    email TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO users
                (username, password_hash, full_name, role, department, shift,
                 experience_years, compliance, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "teste",
                    self._hash_password("teste123"),
                    "Joao da Silva",
                    "Operador de Seguranca",
                    "Linha de Montagem A",
                    "Manha (06:00 - 14:00)",
                    8,
                    "97%",
                    "joao.silva@prosec.local",
                ),
            )

    @staticmethod
    def _hash_password(password):
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def authenticate(self, username, password):
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM users WHERE username = ? AND password_hash = ?",
                (username.strip(), self._hash_password(password)),
            ).fetchone()
        return dict(row) if row else None