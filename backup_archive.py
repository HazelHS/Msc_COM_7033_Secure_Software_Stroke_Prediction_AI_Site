# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artifact. Mostly for syntax, logic and error checking with ChatGPT and Clude Sonnet 4.5 used as the models.

""" Backup and archiving module for the databases.

This module provides functionality to backup the SQLite and MongoDB databases 
for both the users and administrators (including audit logs) as well as the main patient records DB.
"""

import os
import datetime
import subprocess
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Paths
BACKUP_DIR = "db_backups"
os.makedirs(BACKUP_DIR, exist_ok=True)

# Backup SQLite databases (users.db, admin.db)
def backup_sqlite(db_filename): # (OpenAI, 2025)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.basename(db_filename)
    backup_file = os.path.join(BACKUP_DIR, f"{base_name}_{timestamp}.bak")
    if os.path.exists(db_filename):
        with open(db_filename, "rb") as src, open(backup_file, "wb") as dst:
            dst.write(src.read())
        print(f"Backed up {db_filename} to {backup_file}")
    else:
        print(f"SQLite file not found: {db_filename}")
    """Back up a SQLite database file to the backup directory with a timestamp.

    Args:
        db_filename: Path to the SQLite database file.
    """

# Backup MongoDB patient records, requires mongodump to be installed (can be found at: https://www.mongodb.com/docs/database-tools/mongodump/).
def backup_mongodb(): # (OpenAI, 2025)
    mongo_uri = os.getenv("MONGODB_URI")
    mongo_db = os.getenv("MONGODB_DB")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"{mongo_db}_{timestamp}.archive")
    # Use mongodump (must be installed and in PATH)
    cmd = [
        r"C:\Program Files\MongoDB\database_tools\bin\mongodump.exe",
        f"--uri={mongo_uri}",
        f"--archive={backup_file}"
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"Backed up MongoDB to {backup_file}")
    except Exception as e:
        print(f"MongoDB backup failed: {e}")
        
    """Back up the MongoDB database using mongodump.

    Raises:
        Exception: If mongodump fails.
    """

if __name__ == "__main__": # (OpenAI, 2025)
    backup_sqlite(os.path.join("instance", "users.db"))
    backup_sqlite(os.path.join("instance", "admin.db"))
    backup_mongodb()