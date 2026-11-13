import sqlite3
import os

"""
Diagnostic Script
-----------------
Verifies that the database file exists and contains data.
Run this if the application shows an empty list.
"""

if __name__ == '__main__':
    if os.path.exists('disney.db'):
        print("Database found.")
        conn = sqlite3.connect('disney.db')
        count = conn.execute('SELECT COUNT(*) FROM Content').fetchone()[0]
        print(f"Row count in Content table: {count}")
        conn.close()
    else:
        print("Database file 'disney.db' NOT found. Please run 'criar_database.py'.")