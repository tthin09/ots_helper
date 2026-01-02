import sqlite3
import os
from datetime import datetime

def is_running_in_docker():
    """Detect if code is running inside Docker container."""
    if os.getenv('DOCKER_CONTAINER'):
        return True
    if os.path.exists('/.dockerenv'):
        return True
    try:
        if os.getpid() == 1:
            return True
    except:
        pass
    return False

def get_db_path():
    """Get database path based on environment."""
    if is_running_in_docker():
        return "/app/data/articles.db"
    else:
        return "articles.db"

def view_database():
    """View database schema and first 5 entries."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        print("   Run main.py first to create the database.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*80)
    print("DATABASE INFORMATION")
    print("="*80)
    print(f"Database path: {db_path}")
    print(f"File size: {os.path.getsize(db_path) / 1024:.2f} KB")
    print()
    
    # Get table schema
    print("="*80)
    print("TABLE SCHEMA")
    print("="*80)
    cursor.execute("PRAGMA table_info(articles)")
    schema = cursor.fetchall()
    
    print(f"{'Column':<15} {'Type':<10} {'Not Null':<10} {'Primary Key':<12}")
    print("-"*80)
    for col in schema:
        col_name = col[1]
        col_type = col[2]
        not_null = "Yes" if col[3] else "No"
        pk = "Yes" if col[5] else "No"
        print(f"{col_name:<15} {col_type:<10} {not_null:<10} {pk:<12}")
    
    print()
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_count = cursor.fetchone()[0]
    
    print("="*80)
    print(f"TOTAL ARTICLES: {total_count}")
    print("="*80)
    print()
    
    # Get first 5 entries
    print("="*80)
    print("FIRST 5 ENTRIES")
    print("="*80)
    
    cursor.execute("""
        SELECT id, updated_at, hash, last_checked 
        FROM articles 
        ORDER BY last_checked DESC
        LIMIT 5
    """)
    
    entries = cursor.fetchall()
    
    if not entries:
        print("No entries found in database.")
    else:
        for idx, entry in enumerate(entries, 1):
            article_id, updated_at, content_hash, last_checked = entry
            
            print(f"\n[{idx}] Article ID: {article_id}")
            print(f"    Updated At:   {updated_at}")
            print(f"    Content Hash: {content_hash[:32]}... (truncated)")
            print(f"    Last Checked: {last_checked}")
            print("-"*80)
    
    # Get statistics
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    
    # Most recently updated
    cursor.execute("""
        SELECT id, updated_at 
        FROM articles 
        ORDER BY updated_at DESC 
        LIMIT 1
    """)
    most_recent = cursor.fetchone()
    if most_recent:
        print(f"Most recently updated: Article {most_recent[0]} at {most_recent[1]}")
    
    # Most recently checked
    cursor.execute("""
        SELECT id, last_checked 
        FROM articles 
        ORDER BY last_checked DESC 
        LIMIT 1
    """)
    most_checked = cursor.fetchone()
    if most_checked:
        print(f"Most recently checked: Article {most_checked[0]} at {most_checked[1]}")
    
    # Oldest article
    cursor.execute("""
        SELECT id, updated_at 
        FROM articles 
        ORDER BY updated_at ASC 
        LIMIT 1
    """)
    oldest = cursor.fetchone()
    if oldest:
        print(f"Oldest article: Article {oldest[0]} from {oldest[1]}")
    
    print("="*80)
    
    conn.close()

if __name__ == "__main__":
    view_database()