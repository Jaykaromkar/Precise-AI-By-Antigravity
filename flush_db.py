import sqlite3
import os

try:
    conn = sqlite3.connect('backend/niramaya.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_messages WHERE content LIKE '%bg-blue%';")
    conn.commit()
    print('Rows deleted:', cur.rowcount)
except Exception as e:
    print('Error:', e)
