import sqlite3
import os
import base64
import requests

DB_FILE = os.path.join(os.path.dirname(__file__), "polysekunda.db")

# ---------- GITHUB CONFIG ----------
# Set these as environment variables on Render (Settings > Environment)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")        # Personal Access Token with repo scope
GITHUB_REPO = os.environ.get("GITHUB_REPO", "NexusBenzin/PolySekunda")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
DB_PATH_IN_REPO = "polysekunda.db"


def push_db_to_github():
    """Upload the current polysekunda.db file to GitHub so data survives restarts."""
    if not GITHUB_TOKEN:
        # No token configured (e.g. running locally) - skip silently
        return

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_PATH_IN_REPO}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    try:
        with open(DB_FILE, "rb") as f:
            content = base64.b64encode(f.read()).decode("utf-8")

        # Need the current file's SHA to update it (GitHub requires this)
        get_resp = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH})
        sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

        payload = {
            "message": "Auto-update database",
            "content": content,
            "branch": GITHUB_BRANCH,
        }
        if sha:
            payload["sha"] = sha

        put_resp = requests.put(api_url, headers=headers, json=payload)

        if put_resp.status_code not in (200, 201):
            print(f"GitHub push failed: {put_resp.status_code} {put_resp.text}")

    except Exception as e:
        print(f"GitHub push error: {e}")


def pull_db_from_github():
    """Download the latest polysekunda.db from GitHub on startup, if it exists."""
    if not GITHUB_TOKEN:
        return

    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DB_PATH_IN_REPO}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    try:
        resp = requests.get(api_url, headers=headers, params={"ref": GITHUB_BRANCH})
        if resp.status_code == 200:
            content = base64.b64decode(resp.json()["content"])
            with open(DB_FILE, "wb") as f:
                f.write(content)
            print("Loaded database from GitHub.")
        else:
            print("No existing database found on GitHub, starting fresh.")
    except Exception as e:
        print(f"GitHub pull error: {e}")


class Database:
    def __init__(self):
        # Try to restore the latest DB from GitHub before connecting
        pull_db_from_github()

        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                balance  INTEGER NOT NULL DEFAULT 1000,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                id       INTEGER PRIMARY KEY,
                question TEXT NOT NULL,
                resolved INTEGER NOT NULL DEFAULT 0,
                winner   TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id INTEGER NOT NULL,
                username  TEXT NOT NULL,
                choice    TEXT NOT NULL,
                amount    INTEGER NOT NULL
            )
        """)
        self.conn.commit()

    # ---------- USERS ----------

    def add_user(self, name, password, is_admin=False):
        try:
            self.conn.execute(
                "INSERT INTO users (username, password, balance, is_admin) VALUES (?, ?, 1000, ?)",
                (name, password, 1 if is_admin else 0)
            )
            self.conn.commit()
            push_db_to_github()
            return True
        except sqlite3.IntegrityError:
            return False  # username already exists

    def find_user(self, name):
        row = self.conn.execute(
            "SELECT * FROM users WHERE username = ?", (name,)
        ).fetchone()
        return dict(row) if row else None

    def update_balance(self, name, new_balance):
        self.conn.execute(
            "UPDATE users SET balance = ? WHERE username = ?",
            (new_balance, name)
        )
        self.conn.commit()
        push_db_to_github()

    def get_all_users(self):
        rows = self.conn.execute("SELECT * FROM users").fetchall()
        return [dict(row) for row in rows]

    # ---------- MARKETS ----------

    def add_market(self, market_id, question):
        # Only insert if it doesn't exist yet (so restarts don't duplicate)
        existing = self.conn.execute(
            "SELECT id FROM markets WHERE id = ?", (market_id,)
        ).fetchone()
        if existing is None:
            self.conn.execute(
                "INSERT INTO markets (id, question, resolved, winner) VALUES (?, ?, 0, NULL)",
                (market_id, question)
            )
            self.conn.commit()
            push_db_to_github()

    def get_market(self, market_id):
        row = self.conn.execute(
            "SELECT * FROM markets WHERE id = ?", (market_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_markets(self):
        rows = self.conn.execute("SELECT * FROM markets ORDER BY id").fetchall()
        return [dict(row) for row in rows]

    def resolve_market(self, market_id, winner):
        self.conn.execute(
            "UPDATE markets SET resolved = 1, winner = ? WHERE id = ?",
            (winner, market_id)
        )
        self.conn.commit()
        push_db_to_github()

    def create_market(self, question):
        cursor = self.conn.execute(
            "INSERT INTO markets (question, resolved, winner) VALUES (?, 0, NULL)",
            (question,)
        )
        self.conn.commit()
        market_id = cursor.lastrowid
        push_db_to_github()
        return market_id

    def delete_market(self, market_id):
        self.conn.execute("DELETE FROM bets WHERE market_id = ?", (market_id,))
        self.conn.execute("DELETE FROM markets WHERE id = ?", (market_id,))
        self.conn.commit()
        push_db_to_github()

    # ---------- BETS ----------

    def add_bet(self, market_id, username, choice, amount):
        self.conn.execute(
            "INSERT INTO bets (market_id, username, choice, amount) VALUES (?, ?, ?, ?)",
            (market_id, username, choice, amount)
        )
        self.conn.commit()
        push_db_to_github()

    def get_bets_for_market(self, market_id):
        rows = self.conn.execute(
            "SELECT * FROM bets WHERE market_id = ?", (market_id,)
        ).fetchall()
        return [dict(row) for row in rows]

    def get_bets_for_user(self, username):
        rows = self.conn.execute(
            "SELECT * FROM bets WHERE username = ?", (username,)
        ).fetchall()
        return [dict(row) for row in rows]

    def read_database(self):
        print(self.get_all_users())