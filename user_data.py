import os
import sys
import psycopg2

class Database:
    def __init__(self):
        """Initializes the database connection using Render environment variables."""
        # Pull the database string from Render's environment dashboard safely
        self.database_url = os.environ.get("DATABASE_URL")

        if not self.database_url:
            print("CRITICAL ERROR: DATABASE_URL environment variable is missing!")
            print("Please add it to your Render Dashboard -> Environment panel.")
            sys.exit(1)
        
        # Automatically run table setup when the app creates the database object
        self.init_db()

    def get_connection(self):
        """Establishes and returns a live connection to your Neon Postgres database."""
        try:
            return psycopg2.connect(self.database_url)
        except Exception as e:
            print(f"Error connecting to PostgreSQL: {e}")
            return None

    def init_db(self):
        """Creates tables if they don't exist yet. Adjust columns as needed!"""
        # Notice: 'SERIAL' replaces SQLite's 'AUTOINCREMENT'
        create_tables_query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            user_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(create_tables_query)
                conn.commit()
                print("Database tables verified/initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize tables: {e}")
                conn.rollback()
            finally:
                conn.close()

    def save_user_data(self, username, data_string):
        """Inserts or updates a user's data string into Neon."""
        # Postgres uses '%s' as placeholders instead of SQLite's '?'
        query = """
        INSERT INTO users (username, user_data) 
        VALUES (%s, %s)
        ON CONFLICT (username) 
        DO UPDATE SET user_data = EXCLUDED.user_data;
        """
        
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (username, data_string))
                conn.commit()
                print(f"Successfully saved data for user: {username}")
            except Exception as e:
                print(f"Error saving data: {e}")
                conn.rollback()
            finally:
                conn.close()

    def get_user_data(self, username):
        """Retrieves data for a specific user."""
        query = "SELECT user_data FROM users WHERE username = %s;"
        
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as cursor:
                    cursor.execute(query, (username,))
                    result = cursor.fetchone()
                    return result[0] if result else None
            except Exception as e:
                print(f"Error fetching data: {e}")
                return None
            finally:
                conn.close()
        return None

# This allows you to test the file standalone by running `python user_data.py`
if __name__ == "__main__":
    print("Testing Database class initialization...")
    db = Database()
