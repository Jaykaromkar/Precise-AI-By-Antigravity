import sqlite3

def check_db():
    conn = sqlite3.connect('local.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, document_id, status, progress_message, length(report_json) FROM document_reports ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    print("Recent Reports:")
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    check_db()
