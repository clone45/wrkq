import json
import sqlite3
import pymongo
from datetime import datetime
from pathlib import Path

def create_sqlite_schema(conn):
    """Create the SQLite database schema"""
    cursor = conn.cursor()
    
    # Create tables with proper schema
    cursor.executescript('''
        -- Schema creation SQL from above
        CREATE TABLE jobs (
            id INTEGER PRIMARY KEY,
            job_id TEXT UNIQUE,
            original_id TEXT,
            title TEXT,
            company TEXT,
            blurb TEXT,
            location TEXT,
            salary TEXT,
            site_name TEXT,
            details_link TEXT,
            posting_date TEXT,
            job_description TEXT,
            review_status TEXT,
            rating_rationale TEXT,
            rating_tldr TEXT,
            star_rating TEXT,
            hidden INTEGER DEFAULT 0,
            company_id INTEGER,
            slug TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
        
        CREATE TABLE companies (
            id INTEGER PRIMARY KEY,
            original_id TEXT,
            name TEXT,
            job_count INTEGER DEFAULT 0
        );
        
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY,
            original_id TEXT,
            job_id INTEGER,
            company_id INTEGER,
            application_date TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        );
        
        CREATE TABLE history (
            id INTEGER PRIMARY KEY,
            company_id INTEGER,
            action TEXT,
            application_id INTEGER,
            job_id INTEGER,
            timestamp TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (application_id) REFERENCES applications(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
    ''')
    
    conn.commit()

def migrate_companies(mongo_db, sqlite_conn):
    """Migrate companies data from MongoDB to SQLite"""
    print("Migrating companies...")
    cursor = sqlite_conn.cursor()
    
    # Get all companies from MongoDB
    companies = list(mongo_db.companies.find({}))
    
    # Create a mapping of MongoDB _ids to SQLite ids for later reference
    company_id_map = {}
    
    for company in companies:
        # Extract the basic company info
        mongo_id = str(company['_id'])
        name = company.get('name', '')
        job_count = company.get('job_count', 0)
        
        # Insert into SQLite
        cursor.execute(
            'INSERT INTO companies (original_id, name, job_count) VALUES (?, ?, ?)',
            (mongo_id, name, job_count)
        )
        
        # Store the mapping
        company_id_map[mongo_id] = cursor.lastrowid
    
    sqlite_conn.commit()
    print(f"Migrated {len(companies)} companies")
    return company_id_map

def migrate_jobs(mongo_db, sqlite_conn, company_id_map):
    """Migrate jobs data from MongoDB to SQLite"""
    print("Migrating jobs...")
    cursor = sqlite_conn.cursor()
    
    # Get all jobs from MongoDB
    jobs = list(mongo_db.jobs.find({}))
    
    # Create a mapping of MongoDB _ids to SQLite ids for later reference
    job_id_map = {}
    
    # Track stats for reporting
    total_jobs = len(jobs)
    skipped_jobs = 0
    migrated_jobs = 0
    
    for job in jobs:
        # Extract job data
        mongo_id = str(job['_id'])
        job_id = job.get('job_id', '')
        
        # Check if job_id already exists in the database
        cursor.execute('SELECT id FROM jobs WHERE job_id = ?', (job_id,))
        existing_job = cursor.fetchone()
        
        if existing_job:
            # Job already exists, skip it
            skipped_jobs += 1
            # Store the mapping anyway so references don't break
            job_id_map[mongo_id] = existing_job[0]
            continue
        
        # Extract remaining job data
        title = job.get('title', '')
        company = job.get('company', '')
        blurb = job.get('blurb', '')
        location = job.get('location', '')
        salary = job.get('salary', '')
        site_name = job.get('site_name', '')
        details_link = job.get('details_link', '')
        posting_date = job.get('posting_date', '')
        job_description = job.get('job_description', '')
        review_status = job.get('review_status', '')
        rating_rationale = job.get('rating_rationale', '')
        rating_tldr = job.get('rating_tldr', '')
        star_rating = job.get('star_rating', '')
        hidden = 1 if job.get('hidden', False) else 0
        slug = job.get('slug', '')
        
        # Handle company reference
        company_id = None
        if 'company_id' in job and job['company_id']:
            mongo_company_id = str(job['company_id'])
            company_id = company_id_map.get(mongo_company_id)
        
        try:
            # Insert into SQLite
            cursor.execute('''
                INSERT INTO jobs (
                    original_id, job_id, title, company, blurb, location, salary, 
                    site_name, details_link, posting_date, job_description, 
                    review_status, rating_rationale, rating_tldr, star_rating, 
                    hidden, company_id, slug
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mongo_id, job_id, title, company, blurb, location, salary,
                site_name, details_link, posting_date, job_description,
                review_status, rating_rationale, rating_tldr, star_rating,
                hidden, company_id, slug
            ))
            
            # Store the mapping
            job_id_map[mongo_id] = cursor.lastrowid
            migrated_jobs += 1
            
        except sqlite3.IntegrityError as e:
            # This is a fallback in case the earlier check missed something
            print(f"Could not insert job {job_id} ({mongo_id}): {e}")
            skipped_jobs += 1
            
            # Try to get the ID of the existing job for mapping
            cursor.execute('SELECT id FROM jobs WHERE job_id = ?', (job_id,))
            existing_id = cursor.fetchone()
            if existing_id:
                job_id_map[mongo_id] = existing_id[0]
    
    sqlite_conn.commit()
    print(f"Jobs migration: {migrated_jobs} migrated, {skipped_jobs} skipped, {total_jobs} total")
    return job_id_map

def migrate_applications(mongo_db, sqlite_conn, company_id_map, job_id_map):
    """Migrate applications data from MongoDB to SQLite"""
    print("Migrating applications...")
    cursor = sqlite_conn.cursor()
    
    # Get all applications from MongoDB
    applications = list(mongo_db.applications.find({}))
    
    # Create a mapping of MongoDB _ids to SQLite ids for later reference
    application_id_map = {}
    
    for app in applications:
        # Extract application data
        mongo_id = str(app['_id'])
        
        # Get references
        job_id = None
        if 'job_id' in app and app['job_id']:
            mongo_job_id = str(app['job_id'])
            job_id = job_id_map.get(mongo_job_id)
        
        company_id = None
        if 'company_id' in app and app['company_id']:
            mongo_company_id = str(app['company_id'])
            company_id = company_id_map.get(mongo_company_id)
        
        # Format the application date
        application_date = None
        if 'application_date' in app and app['application_date']:
            application_date = app['application_date'].isoformat() if hasattr(app['application_date'], 'isoformat') else str(app['application_date'])
        
        # Insert into SQLite
        cursor.execute(
            'INSERT INTO applications (original_id, job_id, company_id, application_date) VALUES (?, ?, ?, ?)',
            (mongo_id, job_id, company_id, application_date)
        )
        
        # Store the mapping
        application_id_map[mongo_id] = cursor.lastrowid
    
    sqlite_conn.commit()
    print(f"Migrated {len(applications)} applications")
    return application_id_map

def migrate_history(mongo_db, sqlite_conn, company_id_map, job_id_map, application_id_map):
    """Migrate history data from company history arrays"""
    print("Migrating history records...")
    cursor = sqlite_conn.cursor()
    
    # Get all companies with history
    companies = list(mongo_db.companies.find({"history": {"$exists": True, "$ne": []}}))
    
    history_count = 0
    
    for company in companies:
        company_mongo_id = str(company['_id'])
        company_id = company_id_map.get(company_mongo_id)
        
        if not company_id or 'history' not in company:
            continue
        
        for history_entry in company.get('history', []):
            action = history_entry.get('action', '')
            
            # Get references
            application_id = None
            if 'application_id' in history_entry and history_entry['application_id']:
                mongo_app_id = str(history_entry['application_id'])
                application_id = application_id_map.get(mongo_app_id)
            
            job_id = None
            if 'job_id' in history_entry and history_entry['job_id']:
                mongo_job_id = str(history_entry['job_id'])
                job_id = job_id_map.get(mongo_job_id)
            
            # Format the timestamp
            timestamp = None
            if 'timestamp' in history_entry and history_entry['timestamp']:
                timestamp = history_entry['timestamp'].isoformat() if hasattr(history_entry['timestamp'], 'isoformat') else str(history_entry['timestamp'])
            
            # Insert into SQLite
            cursor.execute(
                'INSERT INTO history (company_id, action, application_id, job_id, timestamp) VALUES (?, ?, ?, ?, ?)',
                (company_id, action, application_id, job_id, timestamp)
            )
            
            history_count += 1
    
    sqlite_conn.commit()
    print(f"Migrated {history_count} history records")

def main():
    # MongoDB connection
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
    mongo_db = mongo_client["jobs_database"]
    
    # SQLite connection
    db_path = Path("../job_tracker/db/data/sqlite.db")
    if db_path.exists():
        print(f"Warning: {db_path} already exists. It will be overwritten.")
    
    sqlite_conn = sqlite3.connect(db_path)
    
    try:
        # Create the SQLite schema
        create_sqlite_schema(sqlite_conn)
        
        # Migrate data in the correct order to maintain referential integrity
        company_id_map = migrate_companies(mongo_db, sqlite_conn)
        job_id_map = migrate_jobs(mongo_db, sqlite_conn, company_id_map)
        application_id_map = migrate_applications(mongo_db, sqlite_conn, company_id_map, job_id_map)
        migrate_history(mongo_db, sqlite_conn, company_id_map, job_id_map, application_id_map)
        
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        sqlite_conn.rollback()
    finally:
        sqlite_conn.close()
        mongo_client.close()

if __name__ == "__main__":
    main()