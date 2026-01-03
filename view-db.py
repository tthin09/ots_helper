import sqlite3
import json
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_path():
    """Get database path based on environment."""
    if os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER'):
        return "/app/data/articles.db"
    else:
        return "data/articles.db"

def view_database():
    """Display database schema and first 5 entries."""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    print("=" * 80)
    print(f"DATABASE: {db_path}")
    print("=" * 80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute("PRAGMA table_info(articles)")
    columns = cursor.fetchall()
    
    print("\n📋 TABLE SCHEMA: articles")
    print("-" * 80)
    print(f"{'Column':<20} {'Type':<15} {'NotNull':<10} {'Default':<15} {'PK':<5}")
    print("-" * 80)
    
    for col in columns:
        col_id, name, col_type, not_null, default, pk = col
        print(f"{name:<20} {col_type:<15} {bool(not_null)!s:<10} {str(default):<15} {bool(pk)!s:<5}")
    
    # Get total count
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_count = cursor.fetchone()[0]
    
    print("\n" + "=" * 80)
    print(f"TOTAL ENTRIES: {total_count}")
    print("=" * 80)
    
    # Get first 5 entries
    cursor.execute("""
        SELECT id, updated_at, hash, last_checked, uploaded, attached 
        FROM articles 
        LIMIT 5
    """)
    
    entries = cursor.fetchall()
    
    if not entries:
        print("\n❌ No entries found in database")
        conn.close()
        return
    
    print("\n📊 FIRST 5 ENTRIES:")
    print("=" * 80)
    
    for idx, entry in enumerate(entries, 1):
        article_id, updated_at, content_hash, last_checked, uploaded, attached = entry
        
        print(f"\n[{idx}] Article ID: {article_id}")
        print(f"    Updated At:    {updated_at}")
        print(f"    Last Checked:  {last_checked}")
        print(f"    Content Hash:  {content_hash[:40]}..." if content_hash else "    Content Hash:  None")
        print(f"    Uploaded:      {'✓ Yes' if uploaded else '✗ No'}")
        print(f"    Attached:      {'✓ Yes' if attached else '✗ No'}")
        print("-" * 80)
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) FROM articles WHERE uploaded = 1")
    uploaded_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM articles WHERE attached = 1")
    attached_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM articles WHERE uploaded = 1 AND attached = 0")
    pending_attachment_count = cursor.fetchone()[0]
    
    print("\n📈 STATISTICS:")
    print("=" * 80)
    print(f"Total Articles:           {total_count}")
    print(f"Uploaded to OpenAI:       {uploaded_count} ({uploaded_count/total_count*100:.1f}%)" if total_count > 0 else "Uploaded to OpenAI:       0")
    print(f"Attached to Vector Store: {attached_count} ({attached_count/total_count*100:.1f}%)" if total_count > 0 else "Attached to Vector Store: 0")
    print(f"Pending Attachment:       {pending_attachment_count}")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    view_database()