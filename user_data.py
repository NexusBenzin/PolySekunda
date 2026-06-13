import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "polysekunda.db")


class Database:
    def __init__(self):
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

    def create_market(self, question):
        cursor = self.conn.execute(
            "INSERT INTO markets (question, resolved, winner) VALUES (?, 0, NULL)",
            (question,)
        )
        self.conn.commit()
        return cursor.lastrowid

    def delete_market(self, market_id):
        self.conn.execute("DELETE FROM bets WHERE market_id = ?", (market_id,))
        self.conn.execute("DELETE FROM markets WHERE id = ?", (market_id,))
        self.conn.commit()

    # ---------- BETS ----------

    def add_bet(self, market_id, username, choice, amount):
        self.conn.execute(
            "INSERT INTO bets (market_id, username, choice, amount) VALUES (?, ?, ?, ?)",
            (market_id, username, choice, amount)
        )
        self.conn.commit()

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
