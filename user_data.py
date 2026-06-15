import os
import sys
import psycopg2
from psycopg2 import extras

# ==========================================
# 1. DATABASE CONFIGURATION & CONNECTION
# ==========================================

# Pull the database string from Render's environment dashboard safely
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    print("CRITICAL ERROR: DATABASE_URL environment variable is missing!")
    print("Please add it to your Render Dashboard -> Environment panel.")
    sys.exit(1)

def get_db_connection():
    """Establishes and returns a connection to your Neon Postgres database."""
    try:
        # Connect to Postgres (SSL mode is automatically handled via the query parameter)
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

# ==========================================
# 2. DATABASE INITIALIZATION (ON STARTUP)
# ==========================================

def init_db():
    """
    Creates tables if they don't exist yet.
    Adjust this schema to match whatever columns your app tracks!
    """
    # Notice: 'SERIAL' replaces SQLite's 'AUTOINCREMENT'
    create_tables_query = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        user_data TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(create_tables_query)
                conn.commit()
                print("Database tables initialized successfully.")
        except Exception as e:
            print(f"Failed to initialize tables: {e}")
            conn.rollback()
        finally:
            conn.close()

# ==========================================
# 3. CORE DATA OPERATIONS (CRUD)
# ==========================================

def save_user_data(username, data_string):
    """Inserts or updates a user's data string into Neon."""
    # Postgres uses '%s' as placeholders instead of SQLite's '?'
    query = """
    INSERT INTO users (username, user_data) 
    VALUES (%s, %s)
    ON CONFLICT (username) 
    DO UPDATE SET user_data = EXCLUDED.user_data;
    """
    
    conn = get_db_connection()
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

def get_user_data(username):
    """Retrieves data for a specific user."""
    query = "SELECT user_data FROM users WHERE username = %s;"
    
    conn = get_db_connection()
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

# ==========================================
# 4. EXECUTION ENTRANCE
# ==========================================

if __name__ == "__main__":
    print("Starting up user data system...")
    
    # Run table initialization on script startup
    init_db()
    
    # --- YOUR APP CONTINUES BELOW ---
    # Put your main loop, API routing, or processing code here.
    # The absolute mess of git add / git commit / git push code is now gone!
    print("System is idle and listening for database updates...")
