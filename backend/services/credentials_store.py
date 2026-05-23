import os
import sqlite3
from cryptography.fernet import Fernet
from config import CREDENTIALS_DB_PATH

_KEY_PATH = CREDENTIALS_DB_PATH.replace(".db", ".key")


def _get_or_create_key() -> bytes:
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    os.makedirs(os.path.dirname(_KEY_PATH), exist_ok=True)
    with open(_KEY_PATH, "wb") as f:
        f.write(key)
    return key


_fernet = Fernet(_get_or_create_key())


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(CREDENTIALS_DB_PATH), exist_ok=True)
    con = sqlite3.connect(CREDENTIALS_DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS credentials "
        "(domain TEXT PRIMARY KEY, username TEXT, password_enc BLOB)"
    )
    con.commit()
    return con


def upsert(domain: str, username: str, password: str) -> None:
    enc = _fernet.encrypt(password.encode())
    with _conn() as con:
        con.execute(
            "INSERT OR REPLACE INTO credentials VALUES (?, ?, ?)",
            (domain, username, enc),
        )


def get(domain: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT username, password_enc FROM credentials WHERE domain = ?", (domain,)
        ).fetchone()
    if not row:
        return None
    return {"username": row[0], "password": _fernet.decrypt(row[1]).decode()}


def list_domains() -> list[str]:
    with _conn() as con:
        return [r[0] for r in con.execute("SELECT domain FROM credentials").fetchall()]


def delete(domain: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM credentials WHERE domain = ?", (domain,))
        return cur.rowcount > 0
