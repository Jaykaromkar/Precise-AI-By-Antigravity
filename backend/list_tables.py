import sqlite3
try:
    conn = sqlite3.connect('rag_database_v3.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in rag_database_v3.db:")
    for table in tables:
        print(f"- {table[0]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
