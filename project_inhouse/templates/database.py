import sqlite3
import os
from datetime import datetime

def generate_user_id(full_name, dob):
    name_part = full_name[:4].upper()  # First 4 letters of name in uppercase
    dob_part = dob.replace('-', '')  # Remove hyphens from DOB
    return f"{name_part}{dob_part}"  # Concatenate to form user_id

def calculate_age(dob):
    birth_date = datetime.strptime(dob, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

def delete_db():
    """Deletes the health database if it exists."""
    if os.path.exists('health.db'):
        os.remove('health.db')
        print("Database deleted successfully.")
    else:
        print("No existing database found.")

def init_db():
    delete_db()  # Call delete_db() before creating a new database
    print("Initializing new database...")

    # Create a new database
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()

    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute('''CREATE TABLE IF NOT EXISTS registration (
                        user_id TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        dob TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS profile (
                        user_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        gender TEXT NOT NULL,
                        height REAL,
                        weight REAL,
                        city TEXT,
                        state TEXT,
                        FOREIGN KEY(user_id) REFERENCES registration(user_id)
                      )''')
    
    # Create diet_recommendations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS diet_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            user_id TEXT NOT NULL,
            food_preference TEXT,
            activity_level TEXT,
            diet_pdf TEXT,
            FOREIGN KEY(user_id) REFERENCES registration(user_id)
        )
    ''')

    # Create selected_doctors table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS selected_doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            user_id TEXT NOT NULL,
            name TEXT,
            address TEXT,
            rating REAL,
            FOREIGN KEY(user_id) REFERENCES registration(user_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES registration(user_id)
        )
    ''')

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diet_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES registration(user_id)
        )
    """)

    conn.commit()
    conn.close()

def authenticate_user(email, password):
    """Verify user credentials."""
    conn = sqlite3.connect('health.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM registration WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

init_db()
print("Database and tables created successfully!")