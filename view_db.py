import sqlite3
import os
from pathlib import Path

def get_db_path():
    """Get database path based on environment."""
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER'):
        return "/app/data/articles.db"
    else:
        return "data/articles.db"

def view_database(limit=5):
    """View first entries from the database."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    print(f"📊 Viewing database: {db_path}\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"Tables found: {[table[0] for table in tables]}\n")
        
        # Get column names
        cursor.execute("PRAGMA table_info(articles)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"Columns: {', '.join(column_names)}\n")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_count = cursor.fetchone()[0]
        print(f"Total entries: {total_count}\n")
        
        # Get first N entries
        cursor.execute(f"SELECT * FROM articles LIMIT {limit}")
        rows = cursor.fetchall()
        
        print(f"{'='*100}")
        print(f"First {limit} entries:")
        print(f"{'='*100}\n")
        
        for idx, row in enumerate(rows, 1):
            print(f"Entry #{idx}:")
            print("-" * 100)
            for col_name, value in zip(column_names, row):
                # Truncate long values for readability
                display_value = str(value)
                if len(display_value) > 100:
                    display_value = display_value[:97] + "..."
                print(f"  {col_name:15} : {display_value}")
            print()
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # View first 5 entries (change this number if needed)
    view_database(limit=5)
