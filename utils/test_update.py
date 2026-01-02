import sqlite3
import os

# Connect to database
db_path = "articles.db"  # or "/app/data/articles.db" in Docker
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all articles
cursor.execute("SELECT id, updated_at FROM articles LIMIT 10")
articles = cursor.fetchall()

print("Available articles:")
for idx, (article_id, updated_at) in enumerate(articles, 1):
    print(f"{idx}. ID: {article_id}, Updated: {updated_at}")

# Pick one to modify
article_id = articles[0][0]  # First article

# Change its hash to force an update
cursor.execute("""
    UPDATE articles 
    SET hash = 'fake_hash_to_force_update',
        updated_at = datetime('now', '-1 day')
    WHERE id = ?
""", (article_id,))

conn.commit()
conn.close()

print(f"\nModified article {article_id} - it will be detected as 'updated' on next run")
print("Run: python main.py")