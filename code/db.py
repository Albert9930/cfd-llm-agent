import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "results.db"


def connect():
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS studies (
            study_id   INTEGER PRIMARY KEY,
            method     TEXT,
            request    TEXT,
            started_at TEXT
        )""")
    con.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id     INTEGER PRIMARY KEY,
            study_id   INTEGER REFERENCES studies(study_id),
            aoa        REAL,
            cl         REAL,
            cd         REAL,
            l_d        REAL,
            converged  INTEGER,
            iterations INTEGER,
            status     TEXT,
            note       TEXT,
            created_at TEXT
        )""")
    return con


def start_study(method, request):
    con = connect()
    cur = con.execute(
        "INSERT INTO studies (method, request, started_at) VALUES (?, ?, ?)",
        (method, request, datetime.now().isoformat(timespec="seconds")))
    con.commit()
    return cur.lastrowid


def save_run(study_id, result, note=""):
    con = connect()
    con.execute("""
        INSERT INTO runs (study_id, aoa, cl, cd, l_d, converged,
                          iterations, status, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (study_id, result["aoa"], result.get("cl"), result.get("cd"),
         result.get("l_d"), int(result.get("converged", False)),
         result.get("iterations"), result["status"], note,
         datetime.now().isoformat(timespec="seconds")))
    con.commit()