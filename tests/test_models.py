# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Unit tests module for the database models, user and AuditLog.

Tests the model fields, relationships, and constraints.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from tests.test_utils import create_user, create_audit_log

# Test that User model is defined.
def test_user_model_exists(): # (Anthropic, 2025)
    from app.models import User
    assert User is not None
    
    """ Test that the User model is defined in app.models.

    Asserts:
        That the User class is not None.
    """

# Test that AuditLog model is defined.
def test_audit_log_model_exists(): # (Anthropic, 2025)
    from app.models import AuditLog
    assert AuditLog is not None
    
    """ Test that the AuditLog model is defined in app.models.

    Asserts:
        That the AuditLog class is not None.
    """

@pytest.mark.parametrize("field", [
    'id', 'username', 'email', 'password_hash',
    'created_at', 'last_login', 'is_active', 'role',
    'failed_login_attempts', 'account_locked_until'
])
def test_user_model_fields(init_database, field): # (Anthropic, 2025)
    from app.models import User
    user = User()
    assert hasattr(user, field), f"Missing field: {field}"
    
    """ Test that User model has all required fields.

    Args:
        init_database: Pytest fixture for database setup.
        field: Name of the field to check.

    Asserts:
        That the User model has the specified field.
    """

@pytest.mark.parametrize("field", [
    'id', 'user_id', 'action', 'table_name', 'record_id',
    'ip_address', 'user_agent', 'timestamp', 'details'
])
def test_audit_log_model_fields(init_database, field): # (Anthropic, 2025)
    from app.models import AuditLog
    log = AuditLog()
    assert hasattr(log, field), f"Missing field: {field}"
    
    """ Test that AuditLog model has all required fields.

    Args:
        init_database: Pytest fixture for database setup.
        field: Name of the field to check.

    Asserts:
        That the AuditLog model has the specified field.
    """

def test_create_user(init_database, bcrypt_instance): # (Anthropic, 2025)
    from app import db
    user = create_user(
        'testuser123',
        'test123@example.com',
        bcrypt_instance.generate_password_hash('TestPass123!').decode('utf-8')
    )
    
    assert user.id is not None
    assert user.username == 'testuser123'
    assert user.email == 'test123@example.com'
    assert user.is_active == True
    assert user.role == 'user'
    assert user.failed_login_attempts == 0
    
    """ Test creating a user and verifying default field values.

    Args:
        init_database: Pytest fixture for database setup.
        bcrypt_instance: Bcrypt instance for password hashing.

    Asserts:
        That the created user has correct field values and defaults.
    """

def test_user_repr(test_user): # (Anthropic, 2025)
    assert 'testuser' in repr(test_user)
    
    """ Test the string representation of the User model.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That the username appears in the string representation.
    """

def test_user_account_not_locked_initially(test_user): # (Anthropic, 2025)
    assert test_user.is_account_locked() == False
    
    """ Test that a new user account is not locked by default.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That the account is not locked initially.
    """

def test_user_increment_failed_login(test_user): # (Anthropic, 2025)
    initial_attempts = test_user.failed_login_attempts
    test_user.increment_failed_login()
    assert test_user.failed_login_attempts == initial_attempts + 1
    
    """ Test incrementing failed login attempts for a user.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That failed_login_attempts increments by 1.
    """

def test_user_account_locks_after_5_failures(init_database, bcrypt_instance): # (Anthropic, 2025)
    from app import db
    user = create_user(
        'locktest',
        'locktest@example.com',
        bcrypt_instance.generate_password_hash('TestPass123!').decode('utf-8')
    )
    
    for i in range(5):
        user.increment_failed_login()
    
    assert user.is_account_locked() == True
    assert user.account_locked_until is not None
    
    """ Test that a user account locks after 5 failed login attempts.

    Args:
        init_database: Pytest fixture for database setup.
        bcrypt_instance: Bcrypt instance for password hashing.

    Asserts:
        That the account is locked and account_locked_until is set after 5 failures.
    """

def test_user_reset_failed_login(test_user): # (Anthropic, 2025)
    test_user.failed_login_attempts = 3
    test_user.reset_failed_login()
    
    assert test_user.failed_login_attempts == 0
    assert test_user.account_locked_until is None
    
    """ Test resetting failed login attempts for a user.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That failed_login_attempts is reset to 0 and account_locked_until is None.
    """

def test_user_relationships(test_user): # (Anthropic, 2025)
    assert hasattr(test_user, 'audit_logs')
    
    """ Test that the User model has an audit_logs relationship.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That the audit_logs relationship exists.
    """

def test_create_audit_log(init_database, test_user): # (Anthropic, 2025)
    from app import db
    log = create_audit_log(test_user.id, 'CREATE', 'patient_records')
    assert log.id is not None
    assert log.user_id == test_user.id
    assert log.action == 'CREATE'
    assert log.table_name == 'patient_records'
    assert log.timestamp is not None
    
    """ Test creating an audit log entry.

    Args:
        init_database: Pytest fixture for database setup.
        test_user: Pytest fixture for a test user.

    Asserts:
        That the audit log entry is created with correct fields.
    """

def test_audit_log_repr(init_database, test_user): # (Anthropic, 2025)
    log = create_audit_log(test_user.id, 'READ', 'users')
    repr_str = repr(log)
    assert 'READ' in repr_str
    assert str(test_user.id) in repr_str
    
    """ Test the string representation of the AuditLog model.

    Args:
        init_database: Pytest fixture for database setup.
        test_user: Pytest fixture for a test user.

    Asserts:
        That the action and user_id appear in the string representation.
    """

def test_user_password_not_stored_as_plaintext(test_user): # (Anthropic, 2025)
    assert test_user.password_hash != 'SecurePass123!@#'
    assert test_user.password_hash.startswith('$2b$')
    
    """ Test that the user's password is hashed and not stored as plaintext.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That the password_hash is not the plaintext password and uses bcrypt.
    """

@pytest.mark.parametrize("unique_field", ['username', 'email'])
def test_user_unique_constraints(init_database, bcrypt_instance, unique_field): # (Anthropic, 2025)
    from app import db
    user1 = create_user(
        'uniqueuser',
        'unique@example.com',
        bcrypt_instance.generate_password_hash('Pass123!').decode('utf-8')
    )
    
    from app.models import User
    user2 = User()
    user2.username = 'uniqueuser' if unique_field == 'username' else 'user2'
    user2.email = 'unique@example.com' if unique_field == 'email' else 'user2@example.com'
    user2.password_hash = bcrypt_instance.generate_password_hash('Pass123!').decode('utf-8')
    db.session.add(user2)
    
    with pytest.raises(IntegrityError):
        db.session.commit()
    
    db.session.rollback()
    
    """ Test that usernames and emails must be unique in the User model.

    Args:
        init_database: Pytest fixture for database setup.
        bcrypt_instance: Bcrypt instance for password hashing.
        unique_field: Field to test for uniqueness ('username' or 'email').

    Asserts:
        That committing a duplicate username or email raises IntegrityError.
    """

def test_user_default_values(init_database, bcrypt_instance): # (Anthropic, 2025)
    user = create_user(
        'defaultuser',
        'default@example.com',
        bcrypt_instance.generate_password_hash('Pass123!').decode('utf-8')
    )
    
    assert user.is_active == True
    assert user.role == 'user'
    assert user.failed_login_attempts == 0
    assert user.account_locked_until is None
    assert user.created_at is not None
    
    """ Test that a new user has correct default values.

    Args:
        init_database: Pytest fixture for database setup.
        bcrypt_instance: Bcrypt instance for password hashing.

    Asserts:
        That default values for user fields are set correctly.
    """

def test_audit_log_default_timestamp(init_database, test_user): # (Anthropic, 2025)
    log = create_audit_log(test_user.id, 'TEST', 'test_table')
    assert log.timestamp is not None
    assert (datetime.utcnow() - log.timestamp).seconds < 60
    
    """ Test that AuditLog entries have automatic timestamps.

    Args:
        init_database: Pytest fixture for database setup.
        test_user: Pytest fixture for a test user.

    Asserts:
        That the timestamp is set and is recent.
    """

