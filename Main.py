# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.


""" This is the main application entry point.

it will initialize the Flask app, environment settings, initialize databases, 
create admin user, import CSV data, and start the server with HTTPS.
"""

import os
import sys
from app import create_app, db
from app.models import User, AuditLog
from cryptography.fernet import Fernet
from apscheduler.schedulers.background import BackgroundScheduler
import subprocess
from flask import request

# makes a secret key for Flask-WTF, used for SCRF tokens and secure session handling.
def generate_secret_key(): # (Anthropic, 2025)
    import secrets
    return secrets.token_hex(32)
    """Generate a random 32-byte hex string for use as a Flask secret key.

    Returns:
        str: A 64-character hexadecimal string suitable for SECRET_KEY.
    """

# encryption at rest for the mongoDB databse for the records, using Fernet.
def generate_encryption_key(): # (Anthropic, 2025)
    return Fernet.generate_key().decode()
    """Generate a Fernet-compatible encryption key.

    Returns:
        str: A base64-encoded 32-byte key for Fernet encryption.
    """

# Find existing .env or create a new one with defaults if not found.
def check_environment(): # (Anthropic, 2025)
    env_file = '.env'
    
    if not os.path.exists(env_file):
        print("No .env file found, creating one with default settings...")
        # Everything from the "= f" onwards until the ' """ ' will be included in the .env config file.
        env_content = f"""# Flask Configuration
SECRET_KEY={generate_secret_key()}
FLASK_ENV=development
FLASK_DEBUG=False

# Database Configuration
SQLALCHEMY_DATABASE_URI=sqlite:///users.db
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=healthcare_db

# Encryption Key
ENCRYPTION_KEY={generate_encryption_key()}

# HMAC Key for Patient ID Hashing
PATIENT_ID_HMAC_KEY={generate_secret_key()}

# Security Settings
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=1800

# Rate Limiting
RATELIMIT_STORAGE_URL=memory://
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(".env file created")
        print()
    else: # Error checking.
        print(".env file found.")

# Validate encryption on startup intended as part of a "Fail-Secure" design. Even though there are unit tests for security, this runtime validation is for redundancy, incase of startup initiation without successful prior unit tests.
def validate_encryption_system(): # (Anthropic, 2025)
    print("Validating encryption...")
    
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    
    if not encryption_key:
        print("ENCRYPTION_KEY missing, check .env config")
        sys.exit(1)
    
    try:
        # Test Fernet encryption/decryption.
        cipher = Fernet(encryption_key.encode())
        test_data = b"test_encryption_validation"
        encrypted = cipher.encrypt(test_data)
        decrypted = cipher.decrypt(encrypted)
        
        if decrypted != test_data:
            raise ValueError("Decryption test failed - data mismatch")
        
        # Test HMAC hash generation ("keyed-hash message authentication code"), which is used for testing authenication generation on a test string "test:value". Success indacates HMAC's reliably for later use in security.py.
        import hmac
        import hashlib
        test_hash = hmac.new(
            encryption_key.encode(),
            b"test:value",
            hashlib.sha256
        ).hexdigest()
        
        if not test_hash or len(test_hash) != 64:
            raise ValueError("HMAC hash generation failed")
        
        print("Encryption system validated successfully")
        print(f"Fernet cipher: Operational")
        print(f"HMAC hashing: Operational")
        return True
        
    except Exception as e:
        print(f"Encryption system validation failed: {e}")
        sys.exit(1)

# Ensure that the records database is reachable on startup.
def check_mongodb(): # (Anthropic, 2025)
    try:
        from pymongo import MongoClient
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000)
        client.server_info()
        print("MongoDB connection successful")
        return True
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print()
        return False
    
    """Check if MongoDB is reachable at the default URI.

    Returns:
        bool: True if MongoDB connection is successful, False otherwise.
    """

def create_admin_user(app): # (Anthropic, 2025)
    from app.admin_models import AdminUser
    from app import bcrypt, db
    
    # Create an admin user on startup if existing admin is not found.
    with app.app_context():
        try:
            # Check if admin already exists
            admin = AdminUser.query.filter_by(username='admin').first()
            
            if not admin:
                # Generate a strong random password for the admin.
                import secrets
                import string
                
                # Generate strong password: 16 chars with upper, lower, digits, and special chars.
                alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
                admin_password = ''.join(secrets.choice(alphabet) for i in range(16))
                
                # Ensure password meets requirements.
                admin_password = 'Admin' + admin_password + '123!'
                
                # Create admin user.
                admin = AdminUser()
                admin.username = 'admin'
                admin.email = None  # No email by default, if admin adds one manually it will automatiicaly enable "Two Factor Authentication" (2FA).
                admin.password_hash = bcrypt.generate_password_hash(admin_password).decode('utf-8')
                admin.role = 'admin'
                admin.is_active = True  # type: ignore[assignment]
                
                db.session.add(admin)
                db.session.commit()
                
                print("\n" + "="*70)
                print("Admin user created.")
                print("="*70)
                print(f"Username: admin")
                print(f"Password: {admin_password}")
                print(f"Email: Not set (add via Account Settings to enable 2FA)")
                print("="*70)
                print("="*70 + "\n")
                
                # Save the generated admin credentials to an insecure file, for development use only.
                with open('Admin_Login.txt', 'w') as f:
                    f.write("="*70 + "\n")
                    f.write("="*70 + "\n")
                    f.write(f"Username: admin\n")
                    f.write(f"Password: {admin_password}\n")
                    f.write(f"Email: Not set (add via Account Settings to enable 2FA)\n")
                    f.write("="*70 + "\n")
                
                print("Admin login details saved to: Admin_Login.txt")
            else:
                print("Admin user already exists")
        
        except Exception as e:
            print(f"Admin user creation error: {e}")
            sys.exit(1)
            
    """Create an admin user if one does not already exist.

    Args:
        app: The Flask application instance.

    Raises:
        SystemExit: If user creation fails.
    """

def import_csv_data(app): # (Anthropic, 2025)
    from pymongo import MongoClient
    from app.security import encrypt_patient_record, EncryptionError
    import csv
    import os
    
    with app.app_context():
        try:
            # Check if MongoDB is connected.
            mongo_uri = app.config.get('MONGODB_URI', 'mongodb+srv://leedstrinityhazelltu_db_user:OtEtnVn5lGBzDbYb@secureappdb.wgoupdf.mongodb.net/?appName=SecureAppDB')
            mongo_db_name = app.config.get('MONGODB_DB', 'SecureAppDB')
            
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
            db = client[mongo_db_name]
            collection = db.patient_records
            
            # Check if database is empty.
            if collection.count_documents({}) > 0:
                print(f"Patient records already imported ({collection.count_documents({})} records)")
                return
            
            csv_file = 'healthcare-dataset-stroke-data.csv'
            
            # Error checking.
            if not os.path.exists(csv_file):
                print(f"CSV file not found: {csv_file}")
                print("Skipping CSV import.")
                return
            
            print("Importing CSV record data to MongoDB...")
            
            # Open the CSV file, read, process then write to the database.
            with open(csv_file, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                records = []
                encryption_errors = 0
                
                for row in csv_reader:
                    try:
                        # Ensure data is typed correctly and missing values are handled.
                        record = {
                            'id': int(row['id']) if row.get('id') else None,
                            'gender': row['gender'],
                            'age': float(row['age']) if row['age'] else 0,
                            'hypertension': int(row['hypertension']) if row['hypertension'] else 0,
                            'heart_disease': int(row['heart_disease']) if row['heart_disease'] else 0,
                            'ever_married': row['ever_married'],
                            'work_type': row['work_type'],
                            'Residence_type': row['Residence_type'],
                            'avg_glucose_level': float(row['avg_glucose_level']) if row['avg_glucose_level'] else 0,
                            'bmi': row['bmi'],
                            'smoking_status': row['smoking_status'],
                            'stroke': int(row['stroke']) if row['stroke'] else 0
                        }
                        
                        # Encrypt sensitive fields before storage, fpr encryption at rest.
                        encrypted_record = encrypt_patient_record(record)
                        records.append(encrypted_record)
                        
                    except EncryptionError as e:
                        encryption_errors += 1
                        print(f"Encryption failed for row: {e}")
                        continue
                
                # Bulk insert
                if records:
                    collection.insert_many(records)
                    print(f"Successfully imported {len(records)} patient records!")
                    if encryption_errors > 0:
                        print(f"Warning: {encryption_errors} records skipped due to encryption errors")
                else:
                    print("No records could be imported. Check encryption configuration.")
        
        except Exception as e:
            print(f"CSV import error: {e}")
            print("Continuing without CSV data. Import manually if needed.")
            
    """ Imports and encrypts the "healthcare-dataset-stroke-data.CSV" into MongoDB on startup if mongoDB database is empty.

    Args:
        app: The Flask application instance.

    Raises:
        EncryptionError: If encryption of a record fails.
    """

def initialize_database(app): # (Anthropic, 2025)
    with app.app_context():
        try:
            # Import admin models to ensure they're registered with SQLAlchemy.
            from app.admin_models import AdminUser, AdminAuditLog
            
            # Initialize both databases (users.db and admin.db via binds) and use create_all with checkfirst to avoid errors if tables exist.
            db.create_all()
            print("Databases (users.db and admin.db) initialized successfully.")
            
            # Check user counts.
            user_count = User.query.count()
            print(f"Standard user count: {user_count}")
            
            # Create admin user if needed.
            create_admin_user(app)
            
            # Import CSV data if needed.
            import_csv_data(app)
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            sys.exit(1)
            
    """Initialize SQLAlchemy databases and create required tables.

    Args:
        app: The Flask application instance.

    Side Effects:
        Creates tables, prints user counts, creates admin user,
        and imports CSV data if needed.

    Raises:
        SystemExit: If initialization fails.
    """

# Schedule periodic backups using APScheduler.
def run_backup_script(): # (OpenAI, 2025)
    subprocess.run(["python", "backup_archive.py"])
            
# Main execution function.
def main(): # (Anthropic, 2025)
    # Check environment setup.
    print("Checking environment configuration...")
    check_environment()
    
    # Validate encryption.
    validate_encryption_system()
    
    # Check MongoDB connection status.
    print("Checking MongoDB connection...")
    mongodb_available = check_mongodb()
    
    # Create Flask application.
    print("Starting Flask application...")
    app = create_app('development')
    
    # Initialize database.
    initialize_database(app)
    
    # Minimal centralized mitigation for passive header (findings from ZAP/DAST).
    def _set_security_headers(response):
        # Remove server fingerprinting header (Werkzeug sets Server by default).
        response.headers.pop('Server', None)
        # Content Security Policy: allow local content and the CDNs used by the app.
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net data:; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
        response.headers.setdefault('Content-Security-Policy', csp)

        # Clickjacking protection for older browsers.
        response.headers.setdefault('X-Frame-Options', 'DENY')

        # Prevent MIME sniffing by browsers.
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')

        # Conservative referrer policy.
        response.headers.setdefault('Referrer-Policy', 'no-referrer-when-downgrade')

        # Minimal permissions policy.
        response.headers.setdefault('Permissions-Policy', 'geolocation=()')

        # Enable HSTS only in production environments.
        if app.config.get('ENV') == 'production':
            response.headers.setdefault(
                'Strict-Transport-Security', 'max-age=31536000; includeSubDomains'
            )

        # Avoid caching for dynamic (non-static) responses.
        try:
            if not request.path.startswith('/static'):
                response.headers.setdefault('Cache-Control', 'no-cache, no-store, must-revalidate')
                response.headers.setdefault('Pragma', 'no-cache')
                response.headers.setdefault('Expires', '0')
        except Exception:
            # Be conservative if request path is unavailable.
            response.headers.setdefault('Cache-Control', 'no-cache, no-store, must-revalidate')

        return response
    
        """ Recommended security change from ZAP report, headers to be set on an HTTP response.

        This helper applies a set of HTTP headers intended to reduce passive risks such as 
        CSP, clickjacking, MIME sniffing, referrer policy, permissions and cache-control. 
        The CSP is intentionally permissive for development (includes common CDNs and allows inline scripts/styles). 

        Args:
            response: A Flask response object to modify.

        Returns:
            The same Flask response object with additional security headers set.
        """

    app.after_request(_set_security_headers)
    
    # Schedule backup every 24 hours, and only start the scheduler in the actual server process to avoid duplicate threads, when the Werkzeug reloader spawns child processes on debug startup.
    scheduler = None
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not os.environ.get('FLASK_ENV') == 'development':
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_backup_script, 'interval', hours=24)
        scheduler.start()
        print("Background scheduler started (main process).")
    else:
        print("Skipping scheduler start in reloader process.")
 
    # Print startup information, with the localhost URL.
    print("\n" + "="*70)
    print("Application ready")
    print("="*70)
    print(f"Homepage: https://127.0.0.1:5000/")
    print("="*70)
    print()
    
    # display error if no MongoDB connection can be made.
    if not mongodb_available:
        print("MongoDB not found, no access to patient records")
        print()
    
    print("Press CTRL+C to stop the server")
    print()
    
    # Run the application.
    try:
        print("\n" + "="*70)
        print("HTTPS Enabled, using self-signed certificate")
        print("="*70 + "\n")
        
        # Disable the reloader to avoid duplicated processes/threads on Windows.
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True,
            use_reloader=False,
            ssl_context='adhoc'  # Auto-generates self-signed certificate.
        )
    except KeyboardInterrupt:
        print("\n\nServer stopped")
        if scheduler is not None:
            scheduler.shutdown()
        
    """
    Enable HTTPS with self-signed certificate, in production SSL certificates are 
    normally purchased or generated by a trusted Certificate Authority, such as DigiCert or GlobalSign. 
    For developement however, self-signed certificates suffice for demonstrating and testing that the 
    implementation works as intended. Unlike HTTP, HTTPS sends data over an encrypted connection, 
    designed to prevent eavesdropping or "packet sniffing" and tampering such as "man in the middle" attacks.

    Raises:
        Prints status messages.
        Exits on failure.
    """

if __name__ == '__main__':
    main()

