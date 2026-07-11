import sqlite3
import csv

conn = sqlite3.connect("daddybot_memory.db")
cursor = conn.cursor()

with open("wifey_master.csv", "r", encoding="utf-8") as file:
    reader = csv.reader(file)

    next(reader) #Skip header row

    #loop through rows, assigning values to variables, and inserting into the database, strips extra spaces, and handles empty values for author and series
    for row in reader:
        title = row[0].strip()
        author = row[1].strip() if row[1].strip() else None
        series = row[2].strip() if row[2].strip() else None

        try:
            cursor.execute("""
                           INSERT INTO read_books (user_name, book_title, author, series)
                           VALUES (?, ?, ?, ?)
                           """, ("KittyKat", title.lower(), author, series))


        except sqlite3.IntegrityError:
            pass

conn.commit()
conn.close()

print(f"Migration complete! Welcome in Mrs. KittyKat!")