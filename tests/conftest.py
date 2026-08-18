# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Pytest configuration and fixtures for records app.

This module sets up the testing environment, including application context.
"""

import pytest
import os
import sys
from cryptography.fernet import Fernet

# Add parent directory to path.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables before importing app, (Anthropic, 2025).
os.environ['FLASK_ENV'] = 'testing'
os.environ['TESTING'] = 'True'

# Generate test encryption key if not provided,  (Anthropic, 2025).
if 'ENCRYPTION_KEY' not in os.environ:
    test_key = Fernet.generate_key().decode()
    os.environ['ENCRYPTION_KEY'] = test_key

if 'SECRET_KEY' not in os.environ:
    os.environ['SECRET_KEY'] = 'test_secret_key_for_testing_only'

# Set test MongoDB URI to use the test database, (Anthropic, 2025).
if 'MONGODB_URI' not in os.environ:
    os.environ['MONGODB_URI'] = 'mongodb+srv://leedstrinityhazelltu_db_user:OtEtnVn5lGBzDbYb@secureappdb.wgoupdf.mongodb.net/?appName=SecureAppDB'

from app import create_app, db
from app.models import User

@pytest.fixture(scope='session')
def app(): # (Anthropic, 2025)
    app = create_app('testing')
    
    # Additional test configuration with separate in-memory DBs for each bind.
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_BINDS': {
            'admin': 'sqlite:///:memory:'  # Separate in-memory DB for admin.
        },
        'MONGODB_URI': os.environ.get('MONGODB_URI', 'mongodb+srv://leedstrinityhazelltu_db_user:OtEtnVn5lGBzDbYb@secureappdb.wgoupdf.mongodb.net/?appName=SecureAppDB'),
    })
    return app

    """ Create application for testing session which is shared across all tests.

    Returns:
        Flask app instance configured for testing.
    """

@pytest.fixture(scope='session')
def _db(app): # (Anthropic, 2025)
    with app.app_context():
        # Import models to ensure they're registered
        from app.admin_models import AdminUser, AdminAuditLog
        from app.models import User, AuditLog
        
        # Create all tables for both binds
        db.create_all()
        yield db
        db.drop_all()
        
    """ Session-wide test database.

    Args:
        app: Flask application fixture.

    Yields:
        SQLAlchemy db instance with all tables created.
    """

@pytest.fixture(scope='session')
def mongodb_available(app): # (Anthropic, 2025)
    with app.app_context():
        try:
            from app import mongo_db
            if mongo_db is None:
                return False
            # Test connection
            mongo_db.client.server_info()
            return True
        except Exception:
            return False
        
    """ Check if MongoDB is available, used for conditional skipping.

    Args:
        app: Flask application fixture.

    Returns:
        True if MongoDB is available, False otherwise.
    """

@pytest.fixture(scope='session')
def _mongodb(app, mongodb_available): # (Anthropic, 2025)
    if not mongodb_available:
        pytest.skip("MongoDB not available - Please check cloud atlas connection settings.")
    
    with app.app_context():
        from app import mongo_db
        yield mongo_db
        # Clean up test database at end of session.
        try:
            mongo_db.client.drop_database('SecureAppDB')
        except Exception:
            pass
        
    """ Session-wide MongoDB connection, only if available.

    Args:
        app: Flask application fixture.
        mongodb_available: Boolean indicating MongoDB availability.

    Yields:
        MongoDB client instance for testing.
    """

@pytest.fixture(scope='function')
def init_database(app, _db): # (Anthropic, 2025)
    with app.app_context():
        yield _db
        # Rollback and clean all tables
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
        
    """ Function-scoped database cleans up after each test, use this in tests that need SQLAlchemy DB.

    Args:
        app: Flask application fixture.
        _db: SQLAlchemy db fixture.

    Yields:
        Cleaned SQLAlchemy db instance for each test.
    """

@pytest.fixture(scope='function')
def init_mongodb(app, _mongodb): # (Anthropic, 2025)
    with app.app_context():
        yield _mongodb
        # Clean up all collections
        try:
            for collection_name in _mongodb.list_collection_names():
                _mongodb[collection_name].delete_many({})
        except Exception:
            # If cleanup fails, it's not critical
            pass
        
    """ Function-scoped MongoDB - cleans up after each test. Use this in tests that need MongoDB.

    Args:
        app: Flask application fixture.
        _mongodb: MongoDB client fixture.

    Yields:
        Cleaned MongoDB client instance for each test.
    """

@pytest.fixture(scope='function')
def client(app): # (Anthropic, 2025)
    return app.test_client()
    """ Create test client.

    Args:
        app: Flask application fixture.

    Returns:
        Flask test client.
    """

@pytest.fixture(scope='function')
def app_context(app): # (Anthropic, 2025)
    with app.app_context():
        yield app
        
    """ Create application context.

    Args:
        app: Flask application fixture.

    Yields:
        Application context for the duration of the test.
    """

@pytest.fixture(scope='function')
def bcrypt_instance(app): # (Anthropic, 2025)
    from flask_bcrypt import Bcrypt
    return Bcrypt(app)

    """ Get bcrypt instance.

    Args:
        app: Flask application fixture.

    Returns:
        Flask-Bcrypt instance.
    """

@pytest.fixture(scope='function')
def test_user(init_database, bcrypt_instance): # (Anthropic, 2025)
    user = User()
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.password_hash = bcrypt_instance.generate_password_hash('SecurePass123!@#').decode('utf-8')
    user.role = 'user'
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user

    """ Create a test user, reusable across tests.

    Args:
        init_database: Clean database fixture.
        bcrypt_instance: Flask-Bcrypt instance.

    Returns:
        User instance.
    """

@pytest.fixture(scope='function')
def admin_user(init_database, bcrypt_instance): # (Anthropic, 2025)
    from app.admin_models import AdminUser
    admin = AdminUser()
    admin.username = 'testadmin'
    admin.password_hash = bcrypt_instance.generate_password_hash('TestAdmin123!').decode('utf-8')
    admin.role = 'admin'
    admin.is_active = True
    db.session.add(admin)
    db.session.commit()
    db.session.refresh(admin)
    return admin

    """ Create an admin user for testing.

    Args:
        init_database: Clean database fixture.
        bcrypt_instance: Flask-Bcrypt instance.

    Returns:
        AdminUser instance.
    """

@pytest.fixture(scope='function')
def standard_user(init_database, bcrypt_instance): # (Anthropic, 2025)
    user = User()
    user.username = 'testuser@example.com'
    user.email = 'testuser@example.com'
    user.password_hash = bcrypt_instance.generate_password_hash('TestUser123!').decode('utf-8')
    user.set_patient_id(12345)
    user.role = 'user'
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user

    """ Create a standard user with patient ID.

    Args:
        init_database: Clean database fixture.
        bcrypt_instance: Flask-Bcrypt instance.

    Returns:
        User instance with patient ID.
    """

@pytest.fixture(scope='function')
def authenticated_client(client, test_user): # (Anthropic, 2025)
    with client:
        with client.session_transaction() as session:
            session['_user_id'] = str(test_user.id)
            session['_fresh'] = True
        yield client
        
    """ Create an authenticated test client.

    Args:
        client: Flask test client fixture.
        test_user: User instance.

    Yields:
        Authenticated Flask test client.
    """

@pytest.fixture(scope='function')
def sample_patient_data(): # (Anthropic, 2025)
    return {
        'id': 1,
        'gender': 'Male',
        'age': 45.0,
        'hypertension': 0,
        'heart_disease': 1,
        'ever_married': 'Yes',
        'work_type': 'Private',
        'residence_type': 'Urban',
        'avg_glucose_level': 120.5,
        'bmi': '28.5',
        'smoking_status': 'never smoked',
        'stroke': 0
    }
    
    """ Provide sample patient data for testing.

    Returns:
        Dictionary of sample patient data.
    """

@pytest.fixture(scope='function')
def mock_patient_record(app, init_mongodb, sample_patient_data): # (Anthropic, 2025)
    from app.security import encrypt_patient_record
    
    with app.app_context():
        collection = init_mongodb.patient_records
        patient_data = {**sample_patient_data, 'id': 12345}
        encrypted_data = encrypt_patient_record(patient_data)
        result = collection.insert_one(encrypted_data)
        
        yield result.inserted_id
        
    """ Create a mock patient record in MongoDB for testing. 
        Requires MongoDB to be running.

    Args:
        app: Flask application fixture.
        init_mongodb: Clean MongoDB fixture.
        sample_patient_data: Dictionary of patient data.

    Yields:
        Inserted record ID.
    """

