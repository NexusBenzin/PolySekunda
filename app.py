import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

class Database:
    def __init__(self):
        """Initializes connection details and sets up Postgres tables."""
        self.database_url = os.environ.get("DATABASE_URL")

        if not self.database_url:
            print("CRITICAL ERROR: DATABASE_URL environment variable is missing!")
            print("Please add it to your Render Dashboard -> Environment panel.")
            sys.exit(1)
        
        # Build tables if they don't exist yet
        self.init_db()

    def get_connection(self):
        """Establishes a live connection to Neon PostgreSQL using Dict cursors."""
        try:
            # RealDictCursor makes rows act like Python dictionaries: user["balance"]
            return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
        except Exception as e:
            print(f"Database connection failure: {e}")
            return None

    def init_db(self):
        """Creates the structural tables for your prediction market application."""
        conn = self.get_connection()
        if not conn:
            return

        # Table definitions optimized for PostgreSQL syntax
        queries = [
            """
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                password TEXT NOT NULL,
                balance INT DEFAULT 1000,
                is_admin BOOLEAN DEFAULT FALSE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS markets (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                resolved BOOLEAN DEFAULT FALSE,
                winner VARCHAR(10) DEFAULT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS bets (
                id SERIAL PRIMARY KEY,
                market_id INT REFERENCES markets(id) ON DELETE CASCADE,
                username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE,
                choice VARCHAR(10) NOT NULL,
                amount INT NOT NULL
            );
            """
        ]

        try:
            with conn.cursor() as cursor:
                for query in queries:
                    cursor.execute(query)
            conn.commit()
            print("PostgreSQL tables successfully verified/created.")
        except Exception as e:
            print(f"Error initializing schema: {e}")
            conn.rollback()
        finally:
            conn.close()

    # ==========================================
    # USER MANAGEMENT METHODS
    # ==========================================

    def find_user(self, username):
        """Finds a user by username. Returns a dictionary or None."""
        query = "SELECT username, password, balance, is_admin FROM users WHERE username = %s;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (username.lower(),))
                    return cursor.fetchone()
            except Exception as e:
                print(f"Error in find_user: {e}")
            finally:
                conn.close()
        return None

    def add_user(self, username, password, is_admin=False):
        """Creates a new user account. Returns True if successful, False if taken."""
        query = """
        INSERT INTO users (username, password, balance, is_admin) 
        VALUES (%s, %s, 1000, %s) 
        ON CONFLICT (username) DO NOTHING;
        """
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (username.lower().strip(), password, is_admin))
                    # rowcount will be 1 if inserted, 0 if conflict hit DO NOTHING
                    success = cursor.rowcount > 0
                conn.commit()
                return success
            except Exception as e:
                print(f"Error in add_user: {e}")
                conn.rollback()
            finally:
                conn.close()
        return False

    def update_balance(self, username, new_balance):
        """Updates a specific user's token balance."""
        query = "UPDATE users SET balance = %s WHERE username = %s;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (new_balance, username.lower()))
                conn.commit()
            except Exception as e:
                print(f"Error updating balance: {e}")
                conn.rollback()
            finally:
                conn.close()

    def get_all_users(self):
        """Fetches all users for the leaderboard calculation."""
        query = "SELECT username, balance FROM users;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    return cursor.fetchall()
            except Exception as e:
                print(f"Error fetching leaderboard: {e}")
            finally:
                conn.close()
        return []

    # ==========================================
    # MARKET MANAGEMENT METHODS
    # ==========================================

    def get_all_markets(self):
        """Returns a list of all existing markets."""
        query = "SELECT id, question, resolved, winner FROM markets ORDER BY id DESC;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    return cursor.fetchall()
            except Exception as e:
                print(f"Error fetching markets: {e}")
            finally:
                conn.close()
        return []

    def get_market(self, market_id):
        """Fetches details for a singular target prediction market."""
        query = "SELECT id, question, resolved, winner FROM markets WHERE id = %s;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (market_id,))
                    return cursor.fetchone()
            except Exception as e:
                print(f"Error fetching market {market_id}: {e}")
            finally:
                conn.close()
        return None

    def create_market(self, question):
        """Generates a brand new prediction market. Returns its assigned entry ID."""
        query = "INSERT INTO markets (question) VALUES (%s) RETURNING id;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (question.strip(),))
                    new_id = cursor.fetchone()["id"]
                conn.commit()
                return new_id
            except Exception as e:
                print(f"Error creating market: {e}")
                conn.rollback()
            finally:
                conn.close()
        return None

    def delete_market(self, market_id):
        """Deletes a specific market endpoint."""
        query = "DELETE FROM markets WHERE id = %s;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (market_id,))
                conn.commit()
            except Exception as e:
                print(f"Error deleting market: {e}")
                conn.rollback()
            finally:
                conn.close()

    def resolve_market(self, market_id, outcome):
        """Closes out a market state and applies a final resolution win choice."""
        query = "UPDATE markets SET resolved = TRUE, winner = %s WHERE id = %s;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (outcome, market_id))
                conn.commit()
            except Exception as e:
                print(f"Error resolving market: {e}")
                conn.rollback()
            finally:
                conn.close()

    # ==========================================
    # BET MANAGEMENT METHODS
    # ==========================================

    def get_bets_for_market(self, market_id):
        """Fetches all player bets associated with a target market ID."""
        query = "SELECT username, choice, amount FROM bets WHERE market_id = %s;"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (market_id,))
                    return cursor.fetchall()
            except Exception as e:
                print(f"Error fetching bets for market {market_id}: {e}")
            finally:
                conn.close()
        return []

    def add_bet(self, market_id, username, choice, amount):
        """Logs a brand new structural bet entry tracking user token investments."""
        query = "INSERT INTO bets (market_id, username, choice, amount) VALUES (%s, %s, %s, %s);"
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (market_id, username.lower(), choice, amount))
                conn.commit()
            except Exception as e:
                print(f"Error logging bet: {e}")
                conn.rollback()
            finally:
                conn.close()
