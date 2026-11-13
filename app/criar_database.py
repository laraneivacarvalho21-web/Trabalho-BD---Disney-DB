import sqlite3
import pandas as pd
import os

"""
ETL Script (Extract, Transform, Load)
-------------------------------------
1. Reads raw data from 'disney_plus_titles.xlsx'.
2. Creates a normalized Relational Schema (3NF).
3. Transforms data (splitting multivalued columns like 'cast' and 'director').
4. Populates the SQLite database 'disney.db'.
"""

# Define database file name
db_file = 'disney.db'

# Remove existing database to ensure a fresh start
if os.path.exists(db_file):
    os.remove(db_file)

# Connect to SQLite
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# ============================================
# 1. TABLE CREATION (DDL)
# ============================================

# Main Entity: CONTENT
cursor.execute('''
    CREATE TABLE Content (
        show_id TEXT PRIMARY KEY UNIQUE,
        type TEXT NOT NULL,
        title TEXT NOT NULL UNIQUE,
        release_year INTEGER NOT NULL,
        rating TEXT NOT NULL,
        duration INTEGER NOT NULL,
        date_added TEXT NOT NULL ,
        description TEXT UNIQUE
    )
''')

# Entity: PARTICIPANT (Actors and Directors)
# 'UNIQUE' ensures we don't duplicate people
cursor.execute('''
    CREATE TABLE Participant (
        participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
''')

# Entity: COUNTRY
cursor.execute('''
    CREATE TABLE Country (
        country_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
''')

# Entity: GENRE (Categories)
cursor.execute('''
    CREATE TABLE Genre (
        genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
''')

# Relationship: DIRECTS (N:M between Participant and Content)
cursor.execute('''
    CREATE TABLE Directs (
        show_id TEXT,
        participant_id INTEGER,
        PRIMARY KEY (show_id, participant_id),
        FOREIGN KEY (show_id) REFERENCES Content(show_id),
        FOREIGN KEY (participant_id) REFERENCES Participant(participant_id)
    )
''')

# Relationship: ACTS_IN (N:M between Participant and Content)
cursor.execute('''
    CREATE TABLE Acts_In (
        show_id TEXT,
        participant_id INTEGER,
        PRIMARY KEY (show_id, participant_id),
        FOREIGN KEY (show_id) REFERENCES Content(show_id),
        FOREIGN KEY (participant_id) REFERENCES Participant(participant_id)
    )
''')

# Relationship: PRODUCED_IN (N:M between Country and Content)
cursor.execute('''
    CREATE TABLE Produced_In (
        show_id TEXT,
        country_id INTEGER,
        PRIMARY KEY (show_id, country_id),
        FOREIGN KEY (show_id) REFERENCES Content(show_id),
        FOREIGN KEY (country_id) REFERENCES Country(country_id)
    )
''')

# Relationship: BELONGS_TO (N:M between Genre and Content)
cursor.execute('''
    CREATE TABLE Belongs_To (
        show_id TEXT,
        genre_id INTEGER,
        PRIMARY KEY (show_id, genre_id),
        FOREIGN KEY (show_id) REFERENCES Content(show_id),
        FOREIGN KEY (genre_id) REFERENCES Genre(genre_id)
    )
''')

# ============================================
# 2. DATA TRANSFORMATION & LOADING
# ============================================

# Load Excel file into a Pandas DataFrame
df = pd.read_excel('given_database_material/DisneyPlus.xlsx')
df['date_added'] = df['date_added'].astype(str)

def split_and_clean(value):
    """Helper function to split comma-separated strings into lists."""
    if pd.isna(value) or value == '':
        return []
    return [item.strip() for item in str(value).split(',')]

print("Populating database... This may take a moment.")

for _, row in df.iterrows():
    # LOGIC: Extract the first number from the strinG
    try:
        raw_duration = str(row['duration'])
        # Split by space and take the first part, then convert to int
        clean_duration = int(raw_duration.split(' ')[0])
    except (ValueError, IndexError):
        # Handle cases where duration might be missing or empty
        clean_duration = None

    # 2.1 Insert into Main Content Table
    cursor.execute('''
        INSERT INTO Content (show_id, type, title, release_year, rating, duration, date_added, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (row['show_id'], row['type'], row['title'], row['release_year'], 
          row['rating'], clean_duration, row['date_added'], row['description']))

    # 2.2 Handle Directors (N:M Normalization)
    directors = split_and_clean(row['director'])
    for director in directors:
        # Insert Director if not exists
        cursor.execute('INSERT OR IGNORE INTO Participant (name) VALUES (?)', (director,))
        # Get ID
        cursor.execute('SELECT participant_id FROM Participant WHERE name = ?', (director,))
        participant_id = cursor.fetchone()[0]
        # Link in Junction Table
        cursor.execute('INSERT OR IGNORE INTO Directs (show_id, participant_id) VALUES (?, ?)', 
                       (row['show_id'], participant_id))

    # 2.3 Handle Cast/Actors (N:M Normalization)
    actors = split_and_clean(row['cast'])
    for actor in actors:
        cursor.execute('INSERT OR IGNORE INTO Participant (name) VALUES (?)', (actor,))
        cursor.execute('SELECT participant_id FROM Participant WHERE name = ?', (actor,))
        participant_id = cursor.fetchone()[0]
        cursor.execute('INSERT OR IGNORE INTO Acts_In (show_id, participant_id) VALUES (?, ?)', 
                       (row['show_id'], participant_id))

    # 2.4 Handle Countries (N:M Normalization)
    countries = split_and_clean(row['country'])
    for country in countries:
        # Remove trailing commas usually found in this specific dataset
        country = country.strip(',') 
        if country:
            cursor.execute('INSERT OR IGNORE INTO Country (name) VALUES (?)', (country,))
            cursor.execute('SELECT country_id FROM Country WHERE name = ?', (country,))
            country_id = cursor.fetchone()[0]
            cursor.execute('INSERT OR IGNORE INTO Produced_In (show_id, country_id) VALUES (?, ?)', 
                           (row['show_id'], country_id))

    # 2.5 Handle Genres (listed as 'listed_in' in source)
    genres = split_and_clean(row['listed_in'])
    for genre in genres:
        cursor.execute('INSERT OR IGNORE INTO Genre (name) VALUES (?)', (genre,))
        cursor.execute('SELECT genre_id FROM Genre WHERE name = ?', (genre,))
        genre_id = cursor.fetchone()[0]
        cursor.execute('INSERT OR IGNORE INTO Belongs_To (show_id, genre_id) VALUES (?, ?)', 
                       (row['show_id'], genre_id))

# Commit changes and close
conn.commit()
conn.close()
print("Database 'disney.db' created and populated successfully!")