import sqlite3, json, uuid
from datetime import datetime, timezone
from .config import settings

def connect():
    db = sqlite3.connect(settings.DATABASE_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, topic TEXT NOT NULL, stack TEXT NOT NULL,
            files_json TEXT NOT NULL, created_at TEXT NOT NULL
        )""")

def save_project(topic, stack, files):
    pid = str(uuid.uuid4())
    with connect() as db:
        db.execute("INSERT INTO projects VALUES (?, ?, ?, ?, ?)",
                   (pid, topic, stack, json.dumps(files), datetime.now(timezone.utc).isoformat()))
    return pid

def get_project(pid):
    with connect() as db:
        row = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not row: return None
    return {"id": row["id"], "topic": row["topic"], "stack": row["stack"],
            "files": json.loads(row["files_json"]), "created_at": row["created_at"]}


def save_github_token(session_id, token, username):
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS github_sessions (
            session_id TEXT PRIMARY KEY, access_token TEXT NOT NULL, username TEXT NOT NULL
        )""")
        db.execute("INSERT OR REPLACE INTO github_sessions VALUES (?, ?, ?)",
                   (session_id, token, username))

def get_github_token(session_id):
    if not session_id: return None
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS github_sessions (
            session_id TEXT PRIMARY KEY, access_token TEXT NOT NULL, username TEXT NOT NULL
        )""")
        row = db.execute("SELECT access_token FROM github_sessions WHERE session_id=?",
                         (session_id,)).fetchone()
    return row["access_token"] if row else None
