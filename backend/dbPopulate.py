import sqlite3
import csv

# Δημιουργία/Σύνδεση με τη βάση δεδομένων
# Αν το αρχείο movielens.db δεν υπάρχει, η SQLite θα το δημιουργήσει αυτόματα.
conn = sqlite3.connect('movielens.db')
cursor = conn.cursor()

# Δημιουργία του πίνακα movies
# Πρέπει να ακολουθεί τη δομή του αντίστοιχου CSV (movieId, title, genres)
cursor.execute('''
CREATE TABLE IF NOT EXISTS movies (
    movieId INTEGER PRIMARY KEY,
    title TEXT,
    genres TEXT
)
''')

# Διάβασμα του movies.csv και εισαγωγή των δεδομένων
print("Διαβάζω το movies.csv...")
with open('movies.csv', 'r', encoding='utf-8') as file:
    # Χρησιμοποιούμε το csv.reader για να διαβάσει σωστά το αρχείο
    csv_reader = csv.reader(file)
    
    # Προσπερνάμε την πρώτη γραμμή (επικεφαλίδες/headers)
    next(csv_reader)
    
    # Βάζουμε κάθε γραμμή του CSV μέσα στον πίνακα
    for row in csv_reader:
        cursor.execute('INSERT INTO movies (movieId, title, genres) VALUES (?, ?, ?)', (row[0], row[1], row[2]))

# --- ΠΙΝΑΚΑΣ RATINGS ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS ratings (
    userId INTEGER,
    movieId INTEGER,
    rating REAL,
    timestamp INTEGER,
    FOREIGN KEY(movieId) REFERENCES movies(movieId)
)
''')

print("Διαβάζω το ratings.csv...")
with open('ratings.csv', 'r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)
    for row in csv_reader:
        cursor.execute('INSERT INTO ratings (userId, movieId, rating, timestamp) VALUES (?, ?, ?, ?)', (row[0], row[1], row[2], row[3]))

# --- ΠΙΝΑΚΑΣ TAGS ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS tags (
    userId INTEGER,
    movieId INTEGER,
    tag TEXT,
    timestamp INTEGER,
    FOREIGN KEY(movieId) REFERENCES movies(movieId)
)
''')

print("Διαβάζω το tags.csv...")
with open('tags.csv', 'r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)
    for row in csv_reader:
        # Αφαιρέθηκε το περιττό κόμμα μετά την πρώτη παρένθεση
        cursor.execute('INSERT INTO tags (userId, movieId, tag, timestamp) VALUES (?, ?, ?, ?)', (row[0], row[1], row[2], row[3]))

# Αποθήκευση των αλλαγών και κλείσιμο
conn.commit()
conn.close()

print("Η βάση δημιουργήθηκε επιτυχώς!")