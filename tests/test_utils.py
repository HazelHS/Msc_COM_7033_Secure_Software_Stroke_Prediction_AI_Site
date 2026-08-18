# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Shared test utilities module and helper functions.

Provides functions for use in the other test modules.
"""

from app import db
from app.models import User

def create_user(username, email, password_hash, role='user', patient_id=None): # (Anthropic, 2025)
    user = User()
    user.username = username
    user.email = email
    user.password_hash = password_hash
    user.role = role
    if patient_id:
        user.patient_id = patient_id
    db.session.add(user)
    db.session.commit()
    db.session.refresh(user)
    return user

    """ Creates a user in the database.

    Args:
        username: The username for the user.
        email: The email address for the user.
        password_hash: The hashed password.
        role: The user's role (default 'user').
        patient_id: Optional patient ID.

    Returns:
        User: The created User object.
    """

def create_audit_log(user_id, action, table_name, record_id='123', ip='127.0.0.1'): # (Anthropic, 2025)
    from app.models import AuditLog
    log = AuditLog()
    log.user_id = user_id
    log.action = action
    log.table_name = table_name
    log.record_id = record_id
    log.ip_address = ip
    log.user_agent = 'Mozilla/5.0'
    log.details = f'Test {action} log'
    db.session.add(log)
    db.session.commit()
    db.session.refresh(log)
    return log

    """ Creates an audit log entry.

    Args:
        user_id: The ID of the user performing the action.
        action: The action performed.
        table_name: The name of the table affected.
        record_id: The record ID (default '123').
        ip: The IP address (default '127.0.0.1').

    Returns:
        AuditLog: The created AuditLog object.
    """

def assert_encrypted_data(encrypted, original, encrypted_fields): # (Anthropic, 2025)
    for field in encrypted_fields:
        # Should fail if field doesn't exist in original.
        assert field in original, f"Field {field} missing from original data"
        assert field in encrypted, f"Field {field} missing from encrypted data"
        assert encrypted[field] != str(original[field]), f"Field {field} should be encrypted"
        assert isinstance(encrypted[field], str), f"Encrypted {field} should be string"
        
    """ Verifies encrypted data differs from original.

    Args:
        encrypted: The encrypted data dictionary.
        original: The original data dictionary.
        encrypted_fields: List of fields expected to be encrypted.

    Raises:
        AssertionError: If any field is not encrypted as expected.
    """

def assert_search_hashes_exist(encrypted_data, searchable_fields): # (Anthropic, 2025)
    for field in searchable_fields:
        assert field in encrypted_data, f"Searchable field {field} missing from encrypted data"
        search_field = f"{field}_search"
        assert search_field in encrypted_data, f"Search hash {search_field} missing"
        assert encrypted_data[search_field] is not None, f"Search hash {search_field} is None"
        assert len(encrypted_data[search_field]) == 64, f"Search hash {search_field} has wrong length"
        
    """ Verifies search hashes were generated.

    Args:
        encrypted_data: The encrypted data dictionary.
        searchable_fields: List of fields expected to have search hashes.

    Raises:
        AssertionError: If any search hash is missing or invalid.
    """
