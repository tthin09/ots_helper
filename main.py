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
from google.cloud import storage
from google.cloud.storage import transfer_manager
from google.cloud import discoveryengine_v1beta as discoveryengine

# Load environment variables from .env file
load_dotenv()

def setup_logging():
    """Setup logging to both file and console."""
    # Determine log path based on environment
    logs_dir = get_logs_path()
    
    # Create logs directory if it doesn't exist
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Generate log filename with datetime
    log_filename = datetime.now().strftime("%Y%m%d_%H%M%S.log")
    log_file = os.path.join(logs_dir, log_filename)
    
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
        return "/app/articles"
    else:
        return "articles"

def get_json_metadata_path():
    """Get JSON metadata path based on environment."""
    if is_running_in_docker():
        return "/app/data/articles_metadata.json"
    else:
        return "articles_metadata.json"

def get_logs_path():
    """Get logs directory path based on environment."""
    if is_running_in_docker():
        return "/app/logs"
    else:
        return "logs"

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
                last_checked TEXT NOT NULL,
                uploaded INTEGER DEFAULT 0,
                blob_names TEXT,
                attached INTEGER DEFAULT 0,
                article_link TEXT
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_updated_at ON articles(updated_at)
        ''')
        
        # Migrate existing rows to add new columns if they don't exist
        cursor.execute("PRAGMA table_info(articles)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'uploaded' not in columns:
            cursor.execute('ALTER TABLE articles ADD COLUMN uploaded INTEGER DEFAULT 0')
        if 'file_ids' not in columns and 'blob_names' not in columns:
            cursor.execute('ALTER TABLE articles ADD COLUMN blob_names TEXT')
        # Migrate from old file_ids column to blob_names if needed
        if 'file_ids' in columns and 'blob_names' not in columns:
            cursor.execute('ALTER TABLE articles RENAME COLUMN file_ids TO blob_names')
        if 'attached' not in columns:
            cursor.execute('ALTER TABLE articles ADD COLUMN attached INTEGER DEFAULT 0')
        if 'article_link' not in columns:
            cursor.execute('ALTER TABLE articles ADD COLUMN article_link TEXT')
        
        conn.commit()
        conn.close()
    
    def get_article(self, article_id):
        """Retrieve single article metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, updated_at, hash, uploaded, blob_names, attached FROM articles WHERE id = ?',
            (str(article_id),)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'updated_at': result[1],
                'hash': result[2],
                'uploaded': bool(result[3]),
                'blob_names': result[4],
                'attached': bool(result[5])
            }
        return None
    
    def upsert_article(self, article_id, updated_at, content_hash, article_link=None):
        """Insert or update article metadata."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO articles (id, updated_at, hash, last_checked, uploaded, blob_names, attached, article_link)
            VALUES (?, ?, ?, ?, 0, NULL, 0, ?)
        ''', (str(article_id), updated_at, content_hash, datetime.now().isoformat(), article_link))
        
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
    
    def mark_as_uploaded(self, article_id, blob_names):
        """Mark article as uploaded with blob name(s)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert list/string to JSON string for storage
        if isinstance(blob_names, list):
            blob_names_str = json.dumps(blob_names)
        else:
            blob_names_str = blob_names
        
        cursor.execute('''
            UPDATE articles 
            SET uploaded = 1, blob_names = ?
            WHERE id = ?
        ''', (blob_names_str, str(article_id)))
        
        conn.commit()
        conn.close()
    
    def get_unuploaded_articles(self):
        """Get all articles that haven't been uploaded to GCS yet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM articles WHERE uploaded = 0 OR uploaded IS NULL
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in results]
    
    def get_unattached_articles(self):
        """Get all articles that haven't been uploaded to Vertex AI Data Store yet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, article_link FROM articles 
            WHERE (attached = 0 OR attached IS NULL)
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'article_id': row[0], 'article_link': row[1]} for row in results]
    
    def mark_as_attached(self, article_id):
        """Mark article as attached to Vertex AI Data Store."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE articles 
            SET attached = 1
            WHERE id = ?
        ''', (str(article_id),))
        
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
                INSERT OR REPLACE INTO articles (id, updated_at, hash, last_checked, uploaded, blob_names, attached)
                VALUES (?, ?, ?, ?, 0, NULL, 0)
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

    @staticmethod
    def sanitize_filename_static(title):
        """Static method to sanitize filename without instance."""
        clean_name = re.sub(r'[\\/*?:"<>|]', "", title)
        return clean_name.strip()

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

        # 4. Add Title Block and reference link
        article_link = self.article.get('html_url') or self.article.get('url')
        
        # Add reference link at the top if available
        reference_section = ""
        if article_link:
            reference_section = f"**Reference Article Link:** {article_link}\n\n---\n\n"
        
        # Insert periodic reference links throughout the article
        if article_link:
            lines = final_markdown.split('\n')
            total_lines = len(lines)
            
            if total_lines < 40:
                # Insert reference link in the middle for short articles
                middle_index = total_lines // 2
                reference_inline = f" (Source: {article_link})\n"
                lines.insert(middle_index, reference_inline)
            else:
                # Insert reference link every 20 lines for longer articles
                reference_inline = f" (Source: {article_link})\n"
                # Insert from bottom to top to maintain correct line indices
                insert_positions = list(range(20, total_lines, 20))
                insert_positions.reverse()
                for pos in insert_positions:
                    lines.insert(pos, reference_inline)
            
            final_markdown = '\n'.join(lines)
        
        full_content = f"# {title}\n\n{reference_section}{final_markdown}"
        
        # Add reference link at the end if available
        if article_link:
            full_content += f"\n\n---\n**Reference Article Link:** {article_link}"

        # 5. Save to file
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        filename = f"{self._sanitize_filename(title)}.md"
        file_path = os.path.join(output_folder, filename)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        # 6. Update database
        article_link = self.article.get('html_url') or self.article.get('url')
        self.db.upsert_article(
            article_meta['id'],
            article_meta['updated_at'],
            article_meta['hash'],
            article_link
        )

        logging.info(f"  Success! Saved to: {file_path}")
        return {'status': change_status, 'file_path': file_path, 'article_id': article_id, 'article_link': article_link}

class GCSUploader:
    """Handle uploading markdown files to Google Cloud Storage with batch processing."""
    
    def __init__(self, db=None):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.project_id = os.getenv("GCP_PROJECT_ID")
        
        if not self.bucket_name:
            logging.warning("GCS_BUCKET_NAME not set - GCS upload will be skipped")
            self.client = None
        elif not self.project_id:
            logging.warning("GCP_PROJECT_ID not set - GCS upload will be skipped")
            self.client = None
        else:
            try:
                self.client = storage.Client(project=self.project_id)
                self.bucket = self.client.bucket(self.bucket_name)
                logging.info(f"✓ GCS client initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize GCS client: {str(e)}")
                self.client = None
        
        self.db = db or ArticleDatabase()
    
    def upload_files(self, file_items):
        """Upload multiple markdown files to GCS in batches.
        
        Args:
            file_items: List of dicts with 'file_path', 'article_id', and optionally 'article_link' keys
        """
        results = {'successful': [], 'failed': []}
        total = len(file_items)
        
        if not self.client:
            logging.warning("GCS client not configured - skipping upload")
            return results
        
        logging.info(f"\n{'='*60}")
        logging.info(f"=== Uploading {total} files to GCS (Batch Mode) ===")        
        logging.info(f"Bucket: {self.bucket_name}")
        logging.info(f"{'='*60}")
        
        # Batch size for concurrent uploads
        BATCH_SIZE = 100
        batches = [file_items[i:i + BATCH_SIZE] for i in range(0, len(file_items), BATCH_SIZE)]
        
        for batch_num, batch in enumerate(batches, 1):
            logging.info(f"\n--- Processing Batch {batch_num}/{len(batches)} ({len(batch)} files) ---")
            
            # Prepare temporary directory for modified files
            temp_dir = "temp_upload"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            temp_files = []
            file_mapping = {}  # Map temp file to original item
            blob_name_mapping = {}  # Map temp file to blob name
            
            # Step 1: Read and prepare files with reference links
            for item in batch:
                file_path = item['file_path']
                article_id = item['article_id']
                article_link = item.get('article_link')
                
                # Get the original filename without extension
                original_filename = os.path.basename(file_path)
                article_name = os.path.splitext(original_filename)[0]  # Remove .md extension
                
                # Read file content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Ensure reference links are present if article_link is available
                if article_link:
                    reference_marker = "**Reference Article Link:**"
                    
                    if reference_marker not in content:
                        lines = content.split('\n')
                        title_line = ""
                        title_index = -1
                        for i, line in enumerate(lines):
                            if line.startswith('# '):
                                title_line = line
                                title_index = i
                                break
                        
                        # Add reference at top after title
                        reference_top = f"\n**Reference Article Link:** {article_link}\n\n---\n"
                        if title_index >= 0:
                            lines.insert(title_index + 1, reference_top)
                        else:
                            lines.insert(0, reference_top.strip())
                        
                        # Insert periodic references throughout
                        total_lines = len(lines)
                        if total_lines < 40:
                            # Insert in middle for short articles
                            middle_index = total_lines // 2
                            reference_inline = f"\n(Source: {article_link})\n"
                            lines.insert(middle_index, reference_inline)
                        else:
                            # Insert every 20 lines for longer articles
                            reference_inline = f"\n(Source: {article_link})\n"
                            insert_positions = list(range(20, total_lines, 20))
                            insert_positions.reverse()
                            for pos in insert_positions:
                                lines.insert(pos, reference_inline)
                        
                        # Add reference at bottom
                        lines.append(f"\n---\n**Reference Article Link:** {article_link}")
                        
                        content = '\n'.join(lines)
                
                # Save to temp file with .txt extension using article name
                temp_filename = f"{article_name}.txt"
                temp_path = os.path.join(temp_dir, temp_filename)
                
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                temp_files.append(temp_filename)
                file_mapping[temp_filename] = item
                blob_name_mapping[temp_filename] = f"articles/{article_name}.txt"
            
            # Step 2: Use transfer manager for concurrent upload
            try:
                logging.info(f"Starting concurrent upload of {len(temp_files)} files...")
                
                upload_results = transfer_manager.upload_many_from_filenames(
                    self.bucket,
                    temp_files,
                    source_directory=temp_dir,
                    max_workers=8,
                    blob_name_prefix="articles/"
                )
                
                # Process results
                for temp_filename, result in zip(temp_files, upload_results):
                    item = file_mapping[temp_filename]
                    article_id = item['article_id']
                    blob_name = blob_name_mapping[temp_filename]
                    filename = os.path.basename(item['file_path'])
                    
                    if isinstance(result, Exception):
                        logging.error(f"  ✗ {filename}: {result}")
                        results['failed'].append({
                            'file_path': item['file_path'],
                            'article_id': article_id,
                            'filename': filename,
                            'error': str(result)
                        })
                    else:
                        logging.info(f"  ✓ {filename} -> {blob_name}")
                        
                        # Mark as uploaded and attached in database (auto-sync)
                        self.db.mark_as_uploaded(article_id, blob_name)
                        self.db.mark_as_attached(article_id)
                        
                        results['successful'].append({
                            'file_path': item['file_path'],
                            'article_id': article_id,
                            'blob_name': blob_name,
                            'gcs_uri': f"gs://{self.bucket_name}/{blob_name}",
                            'filename': filename,
                            'article_link': item.get('article_link')
                        })
                
            except Exception as e:
                logging.error(f"Batch upload failed: {str(e)}")
                # Fallback to sequential upload for this batch
                logging.info("Falling back to sequential upload...")
                
                for temp_filename in temp_files:
                    item = file_mapping[temp_filename]
                    try:
                        blob_name = blob_name_mapping[temp_filename]
                        blob = self.bucket.blob(blob_name)
                        temp_path = os.path.join(temp_dir, temp_filename)
                        
                        blob.upload_from_filename(temp_path, content_type='text/plain')
                        
                        article_id = item['article_id']
                        filename = os.path.basename(item['file_path'])
                        
                        logging.info(f"  ✓ {filename} -> {blob_name}")
                        
                        # Mark as uploaded and attached in database (auto-sync)
                        self.db.mark_as_uploaded(article_id, blob_name)
                        self.db.mark_as_attached(article_id)
                        
                        results['successful'].append({
                            'file_path': item['file_path'],
                            'article_id': article_id,
                            'blob_name': blob_name,
                            'gcs_uri': f"gs://{self.bucket_name}/{blob_name}",
                            'filename': filename,
                            'article_link': item.get('article_link')
                        })
                        
                    except Exception as upload_error:
                        logging.error(f"  ✗ {filename}: {upload_error}")
                        results['failed'].append({
                            'file_path': item['file_path'],
                            'article_id': item['article_id'],
                            'filename': filename,
                            'error': str(upload_error)
                        })
            
            finally:
                # Clean up temp files
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            
            logging.info(f"✓ Batch {batch_num} complete")
        
        logging.info(f"\n✓ GCS upload complete: {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results

class VertexAISync:
    """Handle syncing files from GCS bucket to Vertex AI Data Store."""
    
    def __init__(self, db=None):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.data_store_id = os.getenv("VERTEX_AI_DATA_STORE_ID")
        self.location = os.getenv("VERTEX_AI_LOCATION", "global")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        
        if not self.project_id:
            logging.warning("GCP_PROJECT_ID not set - Vertex AI sync will be skipped")
            self.client = None
        elif not self.data_store_id:
            logging.warning("VERTEX_AI_DATA_STORE_ID not set - Vertex AI sync will be skipped")
            self.client = None
        else:
            try:
                # Use regional endpoint based on location
                if self.location != "global":
                    client_options = {
                        "api_endpoint": f"{self.location}-discoveryengine.googleapis.com"
                    }
                    self.client = discoveryengine.DocumentServiceClient(
                        client_options=client_options
                    )
                    logging.info(f"✓ Using regional endpoint: {self.location}-discoveryengine.googleapis.com")
                else:
                    self.client = discoveryengine.DocumentServiceClient()
                    logging.info(f"✓ Using global endpoint")
                
                logging.info(f"✓ Vertex AI Data Store client initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Vertex AI client: {str(e)}")
                self.client = None
        
        self.db = db or ArticleDatabase()
    
    def import_documents_from_gcs(self, uploaded_files):
        """Import documents from GCS bucket to Vertex AI Data Store.
        
        Triggers a single import operation for the entire articles folder in the bucket.
        
        Args:
            uploaded_files: List of successfully uploaded files with blob_name and article_id
        """
        if not self.client:
            logging.warning("Vertex AI client not configured - skipping import")
            return {'successful': 0, 'failed': 0}
        
        if not uploaded_files:
            logging.info("No files to import to Vertex AI Data Store")
            return {'successful': 0, 'failed': 0}
        
        total = len(uploaded_files)
        logging.info(f"\n{'='*60}")
        logging.info(f"=== Triggering import of entire bucket folder to Vertex AI Data Store ===")
        logging.info(f"Project: {self.project_id}")
        logging.info(f"Data Store: {self.data_store_id}")
        logging.info(f"Location: {self.location}")
        logging.info(f"Bucket: {self.bucket_name}")
        logging.info(f"Files uploaded: {total}")
        logging.info(f"{'='*60}")
        
        # Construct the parent path
        parent = f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/dataStores/{self.data_store_id}/branches/default_branch"
        
        # Use wildcard to import all files from the articles folder
        gcs_uri_pattern = f"gs://{self.bucket_name}/articles/*"
        
        try:
            # Create import request for UNSTRUCTURED data (plain text files)
            # Configure GCS source with data schema for unstructured documents
            gcs_source = discoveryengine.GcsSource(
                input_uris=[gcs_uri_pattern],
                data_schema="content"  # Use "content" schema for unstructured text files
            )
            
            request = discoveryengine.ImportDocumentsRequest(
                parent=parent,
                gcs_source=gcs_source,
                reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
            )
            
            # Start the import operation
            logging.info(f"Starting import operation...")
            logging.info(f"  Pattern: {gcs_uri_pattern}")
            logging.info(f"  Data schema: content (unstructured text)")
            
            operation = self.client.import_documents(request=request)
            
            logging.info(f"✓ Import operation triggered successfully")
            logging.info(f"  Operation: {operation.operation.name}")
            logging.info(f"  Waiting for import to complete (this may take several minutes)...")
            
            # Wait for the operation to complete
            try:
                response = operation.result(timeout=1800)  # 30 minute timeout
                
                # Parse the response to get detailed import statistics
                error_samples = []
                if hasattr(response, 'error_samples') and response.error_samples:
                    error_samples = response.error_samples[:5]  # Get first 5 errors
                
                # Extract detailed metrics from response
                error_count = 0
                if hasattr(response, 'error_config') and response.error_config:
                    error_count = getattr(response.error_config, 'error_count', 0)
                
                # Get success count
                success_count = total - error_count
                
                # Try to extract detailed breakdown (added, updated, skipped)
                # These might be in different fields depending on the API version
                added_count = 0
                updated_count = 0
                skipped_count = 0
                
                # Check various possible field names
                if hasattr(response, 'success_count'):
                    success_count = response.success_count
                if hasattr(response, 'created_count'):
                    added_count = response.created_count
                if hasattr(response, 'updated_count'):
                    updated_count = response.updated_count
                if hasattr(response, 'skipped_count'):
                    skipped_count = response.skipped_count
                
                # If we don't have the breakdown, estimate from total
                if added_count == 0 and updated_count == 0 and skipped_count == 0:
                    # All successful documents are considered "added" if we don't have breakdown
                    added_count = success_count
                
                # Log detailed results
                if error_count > 0:
                    logging.warning(f"⚠ Import completed with errors")
                    logging.warning(f"  Successfully imported: {success_count}")
                    logging.warning(f"    - Added: {added_count}")
                    logging.warning(f"    - Updated: {updated_count}")
                    logging.warning(f"    - Skipped: {skipped_count}")
                    logging.warning(f"  Failed to import: {error_count}")
                    
                    if error_samples:
                        logging.warning(f"  Error samples:")
                        for error in error_samples:
                            logging.warning(f"    - {str(error)[:200]}")
                    
                    return {
                        'successful': success_count,
                        'failed': error_count,
                        'added': added_count,
                        'updated': updated_count,
                        'skipped': skipped_count
                    }
                else:
                    logging.info(f"✓ Import completed successfully")
                    logging.info(f"  Total documents processed: {total}")
                    logging.info(f"    - Added: {added_count}")
                    logging.info(f"    - Updated: {updated_count}")
                    logging.info(f"    - Skipped: {skipped_count}")
                    
                    return {
                        'successful': total,
                        'failed': 0,
                        'added': added_count,
                        'updated': updated_count,
                        'skipped': skipped_count
                    }
                    
            except Exception as wait_error:
                logging.error(f"Error while waiting for import to complete: {str(wait_error)}")
                logging.error(f"The operation may still be running in the background")
                logging.error(f"Check the Cloud Console for operation status: {operation.operation.name}")
                return {'successful': 0, 'failed': total}
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"Failed to trigger import operation: {error_msg}")
            return {'successful': 0, 'failed': total}

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
        logging.info(f"Added   articles: {len(changes['new'])}")
        logging.info(f"Updated articles: {len(changes['updated'])}")
        logging.info(f"Skipped articles: {len(changes['unchanged'])}")
        logging.info("-"*60)
        logging.info(f"Total articles processed: {len(changes['new']) + len(changes['updated']) + len(changes['unchanged'])}")
        logging.info(f"Pages crawled: {crawl_stats.get('pages_crawled', 0)}")
        logging.info(f"Crawl time: {format_duration(crawl_stats.get('total_time', 0))}")
        logging.info(f"Avg time per page: {crawl_stats.get('avg_time_per_page', 0):.2f}s")
        
        # Collect files for GCS upload: newly changed files
        files_for_gcs = changes['new'] + changes['updated']
        
        # Also check for files that exist locally but haven't been uploaded to GCS yet
        unuploaded_ids = db.get_unuploaded_articles()
        if unuploaded_ids:
            logging.info(f"\nFound {len(unuploaded_ids)} articles not yet uploaded to GCS")
            output_path = get_output_path()
            
            if os.path.exists(output_path):
                existing_files = {f for f in os.listdir(output_path) if f.endswith('.md')}
                
                for article_id in unuploaded_ids:
                    for filename in existing_files:
                        file_path = os.path.join(output_path, filename)
                        
                        already_queued = any(i['file_path'] == file_path for i in files_for_gcs)
                        if not already_queued:
                            files_for_gcs.append({
                                'file_path': file_path,
                                'article_id': article_id,
                                'status': 'existing'
                            })
                            break
        
        # Upload to GCS (will auto-sync to Vertex AI Data Store)
        if files_for_gcs:
            logging.info("\n" + "="*60)
            logging.info(f"Found {len(files_for_gcs)} files to upload to GCS")
            logging.info("="*60)
            
            gcs_upload_start = time.time()
            gcs_uploader = GCSUploader(db=db)
            gcs_results = gcs_uploader.upload_files(files_for_gcs)
            gcs_upload_time = time.time() - gcs_upload_start
            
            logging.info("\n" + "="*60)
            logging.info("=== GCS Upload Summary ===")
            logging.info("="*60)
            logging.info(f"Successful GCS uploads: {len(gcs_results['successful'])}")
            logging.info(f"Failed GCS uploads: {len(gcs_results['failed'])}")
            logging.info(f"GCS upload time: {format_duration(gcs_upload_time)}")
            logging.info("Note: Files will auto-sync to Vertex AI Data Store from GCS bucket")
            
            if gcs_results['successful']:
                logging.info("\nSuccessfully uploaded to GCS:")
                for item in gcs_results['successful']:
                    logging.info(f"  ✓ {item['filename']} -> {item['blob_name']}")
            
            if gcs_results['failed']:
                logging.warning("\nFailed GCS uploads:")
                for item in gcs_results['failed']:
                    logging.warning(f"  ✗ {item['filename']}: {item['error']}")
            
            # Sync uploaded files from GCS to Vertex AI Data Store
            if gcs_results['successful']:
                logging.info("\n" + "="*60)
                logging.info("=== Syncing files from GCS to Vertex AI Data Store ===")
                logging.info("="*60)
                
                sync_start = time.time()
                vertex_sync = VertexAISync(db=db)
                sync_results = vertex_sync.import_documents_from_gcs(gcs_results['successful'])
                sync_time = time.time() - sync_start
                
                logging.info("\n" + "="*60)
                logging.info("=== Vertex AI Sync Summary ===")
                logging.info("="*60)
                logging.info(f"Successfully synced: {sync_results['successful']}")
                logging.info(f"  - Added: {sync_results.get('added', 0)}")
                logging.info(f"  - Updated: {sync_results.get('updated', 0)}")
                logging.info(f"  - Skipped: {sync_results.get('skipped', 0)}")
                logging.info(f"Failed to sync: {sync_results['failed']}")
                logging.info(f"Sync time: {format_duration(sync_time)}")
                logging.info("="*60)
        else:
            logging.info("\n" + "="*60)
            logging.info("No files to upload to GCS")
            logging.info("="*60)
        
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