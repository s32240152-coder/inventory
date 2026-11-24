"""Koneksi database MySQL / MariaDB (padanan config/database.php).

Pengaturan default cocok untuk XAMPP (user root, tanpa password).
Ubah lewat environment variable bila perlu:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""
import os
import re

import pymysql
from pymysql.constants import CLIENT, FIELD_TYPE
from pymysql.converters import conversions
from pymysql.err import IntegrityError  # noqa: F401  (dipakai app.py)
from pymysql.err import MySQLError as DBError  # noqa: F401  (dipakai app.py)
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(BASE_DIR, "database.sql")

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "inventory_db")

# Tanggal tetap berupa teks "YYYY-MM-DD HH:MM:SS" (template memotongnya dengan [:16]);
# DECIMAL jadi angka Python biasa (int bila tanpa desimal, float bila ada).
_conv = conversions.copy()
_conv[FIELD_TYPE.DATETIME] = lambda s: s
_conv[FIELD_TYPE.TIMESTAMP] = lambda s: s
_conv[FIELD_TYPE.DATE] = lambda s: s
_conv[FIELD_TYPE.NEWDECIMAL] = lambda s: float(s) if "." in s else int(s)
_conv[FIELD_TYPE.DECIMAL] = _conv[FIELD_TYPE.NEWDECIMAL]


class Row(dict):
    """Baris hasil query: bisa row["kolom"], row.kolom (di template), dan row[0]."""

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _Cursor:
    def __init__(self, cur):
        self._cur = cur

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        row = self._cur.fetchone()
        return Row(row) if row is not None else None

    def fetchall(self):
        return [Row(r) for r in self._cur.fetchall()]


def _convert(sql):
    """Placeholder gaya '?' -> '%s' (tanda % literal diamankan)."""
    return sql.replace("%", "%%").replace("?", "%s")


class _Connection:
    """Pembungkus tipis supaya app.py cukup memakai db.execute(sql, params)."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        if sql.strip().upper() == "BEGIN":
            self._conn.begin()
            return _Cursor(self._conn.cursor())
        cur = self._conn.cursor()
        if params:
            cur.execute(_convert(sql), tuple(params))
        else:
            cur.execute(sql)
        return _Cursor(cur)

    def executemany(self, sql, seq):
        cur = self._conn.cursor()
        cur.executemany(_convert(sql), list(seq))
        return _Cursor(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _connect(database=None):
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        conv=_conv,
        client_flag=CLIENT.FOUND_ROWS,  # rowcount = baris yang cocok, bukan yang berubah
    )


def get_db():
    return _Connection(_connect(DB_NAME))


def _schema_statements():
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r"--[^\n]*", "", text)  # buang komentar
    for stmt in text.split(";"):
        stmt = stmt.strip()
        # CREATE DATABASE / USE hanya untuk import lewat phpMyAdmin
        if stmt and not stmt.upper().startswith(("CREATE DATABASE", "USE ")):
            yield stmt


def init_db():
    """Buat database & tabel (jika belum ada) dan akun admin awal."""
    # Di hosting gratis database dibuat lewat panel dan user tidak boleh CREATE DATABASE,
    # jadi kegagalan di langkah ini diabaikan.
    try:
        server = _connect()
        server.cursor().execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        server.close()
    except DBError:
        pass

    conn = get_db()
    for stmt in _schema_statements():
        conn.execute(stmt)

    if conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0:
        conn.execute(
            "INSERT INTO users (username, full_name, password, role) VALUES (?, ?, ?, 'admin')",
            ("admin", "Administrator", generate_password_hash("admin123")),
        )
    conn.commit()
    conn.close()
