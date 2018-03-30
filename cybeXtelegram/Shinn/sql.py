# sql.py - Create a SQLite3 table and populate it with data
import sqlite3

# create a new database if the database doesn't already exist
with sqlite3.connect("cybex-telegram-users.db") as connection:
    c = connection.cursor()
    c.execute("""CREATE TABLE users
    (update_id INT, chat TEXT)""")

    # inserting example data to the table
    c.execute("""INSERT INTO users 
    VALUES(2439118, 
    "{'id': 547143881, 'type': 'private', 'first_name': 'Shinno', 'last_name': 'T'}")""")
