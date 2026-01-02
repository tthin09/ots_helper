import json
import re
import os
from markdownify import markdownify as md
import requests
import hashlib
from datetime import datetime
from pathlib import Path
import sqlite3
import logging
import sys
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_logging():
    """Setup logging to both file and console."""
    # Determine log path based on environment
    if is_running_in_docker():
        log_file = "/app/data/crawler.log"
    else:
        log_file = "crawler.log"
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # File handler (with rotation to prevent huge files)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Console handler (so you still see output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    return logger

def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f} minutes ({seconds:.2f} seconds)"
    else:
        hours = seconds / 3600
        minutes = (seconds % 3600) / 60
        return f"{hours:.2f} hours ({minutes:.2f} minutes)"

def is_running_in_docker():
    """Detect if code is running inside Docker container."""
    # Check for Docker-specific environment variable (more reliable)
    if os.getenv('DOCKER_CONTAINER'):
        return True
    # Check for .dockerenv file (present in Docker containers)
    if os.path.exists('/.dockerenv'):
        return True
    # Check if running as PID 1 (typical in Docker)
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
        return "data/articles.db"

def get_output_path():
    """Get output path based on environment."""
    if is_running_in_docker():
        return "/app/output"
    else:
        return "output"

def get_json_metadata_path():
    """Get JSON metadata path based on environment."""
    if is_running_in_docker():
        return "/app/data/articles_metadata.json"
    else:
        return "articles_metadata.json"

class ArticleDatabase:
    """Manage article metadata using SQLite for scalability."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or get_db_path()
        self._init_db()
    
    def _init_db(self):
        """Initialize database with indexes for fast lookups."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                hash TEXT NOT NULL,
                last_checked TEXT NOT NULL
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_updated_at ON articles(updated_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def get_article(self, article_id):
        """Retrieve single article metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, updated_at, hash FROM articles WHERE id = ?',
            (str(article_id),)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'updated_at': result[1],
                'hash': result[2]
            }
        return None
    
    def upsert_article(self, article_id, updated_at, content_hash):
        """Insert or update article metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO articles (id, updated_at, hash, last_checked)
            VALUES (?, ?, ?, ?)
        ''', (str(article_id), updated_at, content_hash, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_all_ids(self):
        """Get all stored article IDs."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM articles')
        ids = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        return ids
    
    def delete_articles(self, article_ids):
        """Remove multiple articles from database."""
        if not article_ids:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(article_ids))
        cursor.execute(
            f'DELETE FROM articles WHERE id IN ({placeholders})',
            tuple(str(aid) for aid in article_ids)
        )
        
        conn.commit()
        conn.close()
    
    def migrate_from_json(self, json_file=None):
        """One-time migration from JSON to SQLite."""
        if json_file is None:
            json_file = get_json_metadata_path()
            
        if not os.path.exists(json_file):
            logging.info("No JSON file to migrate")
            return
        
        logging.info(f"Migrating from {json_file} to {self.db_path}...")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        migrated = 0
        for article_id, metadata in data.items():
            cursor.execute('''
                INSERT OR REPLACE INTO articles (id, updated_at, hash, last_checked)
                VALUES (?, ?, ?, ?)
            ''', (
                str(article_id),
                metadata.get('updated_at', ''),
                metadata.get('hash', ''),
                datetime.now().isoformat()
            ))
            migrated += 1
        
        conn.commit()
        conn.close()
        
        logging.info(f"Successfully migrated {migrated} articles to SQLite")
        
        # Optionally backup the JSON file
        backup_file = json_file + '.backup'
        os.rename(json_file, backup_file)
        logging.info(f"Original JSON backed up to {backup_file}")

class ArticleConverter:
    def __init__(self, json_data, db=None):
        self.data = json_data
        self.article = json_data.get('article', {}) if 'article' in json_data else json_data
        self.db = db or ArticleDatabase()

    def _sanitize_filename(self, title):
        """
        Removes illegal characters from the title to create a valid filename.
        """
        # Remove special characters but keep spaces, hyphens, and alphanumerics
        clean_name = re.sub(r'[\\/*?:"<>|]', "", title)
        # Replace spaces with underscores or keep them (optional)
        return clean_name.strip()

    def _clean_html_pre_conversion(self, html_content):
        """
        Perform any specific string manipulation on HTML before converting.
        Useful for removing Zendesk specific classes or empty divs.
        """
        if not html_content:
            return ""
        
        # Example: Remove empty paragraphs if any
        html_content = html_content.replace("<p>&nbsp;</p>", "")
        return html_content

    def _post_process_markdown(self, markdown_text):
        """
        Clean up the resulting markdown (remove excessive newlines, fix links).
        """
        # Reduce 3 or more newlines to 2
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        # Remove trailing whitespace on lines
        markdown_text = re.sub(r'[ \t]+$', '', markdown_text, flags=re.MULTILINE)
        
        return markdown_text.strip()

    def _get_content_hash(self, content):
        """Generate SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def detect_changes(self):
        """
        Detect if article has changed compared to previous version.
        Returns: 'new', 'updated', or 'unchanged'
        """
        article_id = str(self.article.get('id'))
        updated_at = self.article.get('updated_at')
        body_hash = self._get_content_hash(self.article.get('body', ''))
        
        stored = self.db.get_article(article_id)
        
        if not stored:
            return 'new', {'id': article_id, 'updated_at': updated_at, 'hash': body_hash}
        
        # Check if content or updated_at has changed
        if stored.get('hash') != body_hash or stored.get('updated_at') != updated_at:
            return 'updated', {'id': article_id, 'updated_at': updated_at, 'hash': body_hash}
        
        return 'unchanged', stored

    def convert(self, output_folder=None):
        """Main pipeline execution with change detection."""
        if output_folder is None:
            output_folder = get_output_path()
            
        # Detect changes
        change_status, article_meta = self.detect_changes()
        
        title = self.article.get('title', 'Untitled_Article')
        article_id = self.article.get('id')
        
        logging.info(f"Processing: {title} (ID: {article_id}) - Status: {change_status}")
        
        if change_status == 'unchanged':
            logging.info(f"  Skipped: No changes detected")
            return None
        
        html_body = self.article.get('body', '')
        
        # 1. Pre-clean HTML
        clean_html = self._clean_html_pre_conversion(html_body)

        # 2. Convert HTML to Markdown
        # heading_style="ATX" ensures headers use # instead of underlines
        # strip=['div', 'figure'] removes these wrapper tags but keeps their content
        markdown_content = md(
            clean_html, 
            heading_style="ATX", 
            strip=['div', 'figure', 'figcaption'],
            newline_style="BACKSLASH"
        )

        # 3. Post-process Markdown
        final_markdown = self._post_process_markdown(markdown_content)

        # 4. Add Title Block
        full_content = f"# {title}\n\n{final_markdown}"

        # 5. Save to file
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        filename = f"{self._sanitize_filename(title)}.md"
        file_path = os.path.join(output_folder, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        # 6. Update database
        self.db.upsert_article(
            article_meta['id'],
            article_meta['updated_at'],
            article_meta['hash']
        )

        logging.info(f"  Success! Saved to: {file_path}")
        return {'status': change_status, 'file_path': file_path, 'article_id': article_id}

class ArticleCrawler:
    """Handle crawling and detecting changes across all articles."""
    
    def __init__(self, db=None):
        self.db = db or ArticleDatabase()
        
    def crawl_all_articles(self):
        """Crawl all articles and return list of changes."""
        # FORCE use of environment variable - no fallback
        base_url = os.getenv("ZENDESK_API_URL")
        
        if not base_url:
            error_msg = "ERROR: ZENDESK_API_URL environment variable is not set!"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        logging.info(f"Using API URL from environment: {base_url}")
        
        # Start timing the crawl
        crawl_start = time.time()
        
        changes = {'new': [], 'updated': [], 'unchanged': [], 'deleted': []}
        current_article_ids = set()
        
        url = base_url
        page_count = 0
        total_articles_fetched = 0
        
        while url:
            page_count += 1
            page_start = time.time()
            
            logging.info(f"\nFetching page {page_count}...")
            
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    logging.error(f"Error fetching articles: {response.status_code}")
                    logging.error(f"Response: {response.text[:200]}")
                    break
                    
                data = response.json()
                articles = data.get("articles", [])
                total_articles_fetched += len(articles)
                
                page_fetch_time = time.time() - page_start
                logging.info(f"Fetched {len(articles)} articles in {page_fetch_time:.2f}s")
                
                process_start = time.time()
                logging.info(f"Processing {len(articles)} articles...")
                
                for article in articles:
                    current_article_ids.add(str(article.get('id')))
                    converter = ArticleConverter(article, db=self.db)
                    result = converter.convert()
                    
                    if result:
                        changes[result['status']].append(result)
                    else:
                        changes['unchanged'].append({'article_id': article.get('id')})
                
                process_time = time.time() - process_start
                page_total_time = time.time() - page_start
                logging.info(f"Page {page_count} processed in {process_time:.2f}s (total: {page_total_time:.2f}s)")
                
                url = data.get("next_page")
                
            except Exception as e:
                logging.error(f"Error during crawl: {str(e)}")
                break
        
        # SAFETY CHECK: Only check for deletions if we successfully fetched articles
        deletion_start = time.time()
        stored_ids = self.db.get_all_ids()
        deleted_ids = stored_ids - current_article_ids
        
        if total_articles_fetched == 0 and len(stored_ids) > 0:
            logging.warning("="*60)
            logging.warning("WARNING: API returned 0 articles but database has articles!")
            logging.warning("This might indicate an API error or wrong endpoint.")
            logging.warning("Skipping deletion check to prevent data loss.")
            logging.warning("="*60)
            deleted_ids = set()
        elif deleted_ids:
            logging.info(f"\nDetected {len(deleted_ids)} deleted articles")
            changes['deleted'] = list(deleted_ids)
            self.db.delete_articles(deleted_ids)
        
        deletion_time = time.time() - deletion_start
        logging.info(f"Deletion check completed in {deletion_time:.2f}s")
        
        # Calculate total crawl time
        total_crawl_time = time.time() - crawl_start
        changes['crawl_stats'] = {
            'total_time': total_crawl_time,
            'pages_crawled': page_count,
            'total_articles_fetched': total_articles_fetched,
            'avg_time_per_page': total_crawl_time / page_count if page_count > 0 else 0
        }
        
        return changes

# ==========================================
# USAGE
# ==========================================

if __name__ == "__main__":
    # Start total execution timer
    execution_start = time.time()
    
    # Setup logging first
    logger = setup_logging()
    
    logging.info("=== Starting Zendesk Article Crawler ===")
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Running in Docker: {is_running_in_docker()}")
    logging.info(f"Database: {get_db_path()}")
    logging.info(f"Output: {get_output_path()}")
    
    # Check if ZENDESK_API_URL is set
    api_url = os.getenv("ZENDESK_API_URL")
    if not api_url:
        logging.error("="*60)
        logging.error("ERROR: ZENDESK_API_URL environment variable is not set!")
        logging.error("Please set it in your .env file or docker-compose.yml")
        logging.error("="*60)
        sys.exit(1)
    
    logging.info(f"API URL: {api_url}")
    
    try:
        # Initialize database (will auto-create if doesn't exist)
        db_init_start = time.time()
        db = ArticleDatabase()
        db_init_time = time.time() - db_init_start
        logging.info(f"Database initialized in {db_init_time:.2f}s")
        
        # One-time migration from JSON to SQLite (if JSON file exists)
        json_path = get_json_metadata_path()
        if os.path.exists(json_path):
            migration_start = time.time()
            db.migrate_from_json()
            migration_time = time.time() - migration_start
            logging.info(f"Migration completed in {migration_time:.2f}s")
        
        # Use the crawler for daily sync
        crawler = ArticleCrawler(db=db)
        changes = crawler.crawl_all_articles()
        
        # Extract crawl stats
        crawl_stats = changes.pop('crawl_stats', {})
        
        logging.info("\n" + "="*60)
        logging.info("=== Crawl Summary ===")
        logging.info("="*60)
        logging.info(f"New articles: {len(changes['new'])}")
        logging.info(f"Updated articles: {len(changes['updated'])}")
        logging.info(f"Unchanged articles: {len(changes['unchanged'])}")
        logging.info(f"Deleted articles: {len(changes['deleted'])}")
        logging.info("-"*60)
        logging.info(f"Total articles processed: {len(changes['new']) + len(changes['updated']) + len(changes['unchanged'])}")
        logging.info(f"Pages crawled: {crawl_stats.get('pages_crawled', 0)}")
        logging.info(f"Crawl time: {format_duration(crawl_stats.get('total_time', 0))}")
        logging.info(f"Avg time per page: {crawl_stats.get('avg_time_per_page', 0):.2f}s")
        
        # Upload only changed files to cloud
        files_to_upload = changes['new'] + changes['updated']
        if files_to_upload:
            logging.info("\n" + "="*60)
            logging.info("Files to upload to cloud:")
            for item in files_to_upload:
                logging.info(f"  - {item['file_path']} ({item['status']})")
        
        # Calculate total execution time
        total_execution_time = time.time() - execution_start
        
        logging.info("\n" + "="*60)
        logging.info("=== Execution Complete ===")
        logging.info("="*60)
        logging.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Total execution time: {format_duration(total_execution_time)}")
        logging.info("="*60)
        
    except Exception as e:
        total_execution_time = time.time() - execution_start
        
        logging.error("\n" + "="*60)
        logging.error("=== Crawler Failed ===")
        logging.error("="*60)
        logging.error(f"Error: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        logging.error(f"Failed after: {format_duration(total_execution_time)}")
        logging.error("="*60)
        sys.exit(1)