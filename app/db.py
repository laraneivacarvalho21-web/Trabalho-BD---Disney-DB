import logging
import sqlite3
import re
from flask import g

"""
Database Abstraction Layer
--------------------------
Handles the connection, execution, and closing of the SQLite database
within the Flask application context.
"""

def get_db():
    """
    Opens a new database connection if there is none yet for the
    current application context.
    
    Returns:
        sqlite3.Connection: The database connection object.
    """
    if 'db' not in g:
        g.db = sqlite3.connect("disney.db")
        # row_factory=sqlite3.Row allows accessing columns by name 
        # (e.g., row['title']) instead of just index (row[1])
        g.db.row_factory = sqlite3.Row
        logging.info("Connected to disney.db")
    return g.db

def get_cursor():
    """Helper to get a cursor from the current connection."""
    return get_db().cursor()

def execute(sql, args=None):
    """
    Executes a SQL command with optional arguments.
    
    Args:
        sql (str): The SQL query string.
        args (list/tuple, optional): Parameters to substitute into the query.
        
    Returns:
        sqlite3.Cursor: Result cursor (can be used to fetchone() or fetchall()).
    """
    # Normalize whitespace to make logs cleaner
    sql = re.sub(r"\s+", " ", sql)
    logging.info(f"SQL: {sql} Args: {args}")

    db = get_db()
    if args is not None:
        return db.execute(sql, args)
    else:
        return db.execute(sql)

def close_db(e=None):
    """
    Closes the database connection at the end of the request.
    This function is registered with the Flask app teardown context.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()
        logging.info("Database connection closed")

def init_app(app):
    """Registers the close_db function with the Flask app."""
    app.teardown_appcontext(close_db)

# =======================================================
# COMPATIBILITY LAYER
# =======================================================
def connect():
    """
    Mock function to satisfy the 'db.connect()' call in server.py.
    The actual connection is lazy-loaded via get_db() when needed.
    """
    logging.info("Connected to database disney.db (Simulated for server.py)")