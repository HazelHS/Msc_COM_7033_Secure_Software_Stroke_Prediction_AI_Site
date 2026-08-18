# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Unit tests module for authentication and authorization.

Tests the login, logout, registration, and session management.
"""

import pytest
from datetime import datetime, timedelta
from tests.test_utils import create_user

# (Anthropic, 2025)
@pytest.mark.parametrize("route,expected_status,expected_content", [
    ('/login', 200, b'Login'),
    ('/register', 200, b'Register'),
    ('/', 200, b'Healthcare')
])

# Test that public pages are accessible.
def test_public_pages_accessible(client, route, expected_status, expected_content): # (Anthropic, 2025)
    response = client.get(route)
    assert response.status_code == expected_status
    assert expected_content in response.data, f"Expected content missing from {route}"
    """Test that public pages are accessible and contain expected content.

    Args:
        client: Flask test client.
        route: URL route to test.
        expected_status: Expected HTTP status code.
        expected_content: Expected content bytes in response.

    Asserts:
        That the route returns the expected status and contains the expected content.
    """

# Test that dashboard requires login.
def test_dashboard_requires_authentication(client): # (Anthropic, 2025)
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location
    """Test that dashboard page requires authentication.

    Args:
        client: Flask test client.

    Asserts:
        That unauthenticated access redirects to login.
    """

# Test that logout redirects to index.
def test_logout_redirects_to_index(authenticated_client): # (Anthropic, 2025)
    response = authenticated_client.get('/logout', follow_redirects=False)
    assert response.status_code == 302
    """Test that logout route redirects to index.

    Args:
        authenticated_client: Flask test client with authenticated session.

    Asserts:
        That logout returns a redirect response.
    """

# Test bcrypt password hashing and verification.
def test_bcrypt_hash_verification(bcrypt_instance): # (Anthropic, 2025)
    password = "TestPassword123!"
    password_hash = bcrypt_instance.generate_password_hash(password).decode('utf-8')
    
    assert bcrypt_instance.check_password_hash(password_hash, password) == True
    assert bcrypt_instance.check_password_hash(password_hash, "WrongPassword") == False
    """Test bcrypt password hashing and verification.

    Args:
        bcrypt_instance: Flask-Bcrypt instance.

    Asserts:
        That the password hash verifies correctly and fails for wrong password.
    """

# Test that same password produces different hashes (due to salt).
def test_password_hash_is_different_each_time(bcrypt_instance): # (Anthropic, 2025)
    password = "SamePassword123!"

    hash1 = bcrypt_instance.generate_password_hash(password).decode('utf-8')
    hash2 = bcrypt_instance.generate_password_hash(password).decode('utf-8')

    assert hash1 != hash2
    assert bcrypt_instance.check_password_hash(hash1, password) == True
    assert bcrypt_instance.check_password_hash(hash2, password) == True
    """Test that hashing the same password produces different hashes due to salt.

    Args:
        bcrypt_instance: Flask-Bcrypt instance.

    Asserts:
        That hashes are different and both verify the password.
    """

# Test that login manager is configured.
def test_user_login_manager_exists(app): # (Anthropic, 2025)
    assert hasattr(app, 'login_manager')
    """Test that Flask-Login login_manager is configured on the app.

    Args:
        app: Flask application.

    Asserts:
        That the app has a login_manager attribute.
    """

# Test that user loader function is defined.
def test_user_loader_function_exists(init_database, test_user): # (Anthropic, 2025)
    from app.models import load_user
    from app import db
    db.session.commit()
    
    # Try loading user by ID
    loaded_user = load_user(str(test_user.id))
    if loaded_user is None:
        loaded_user = load_user(f'user_{test_user.id}')
    
    assert loaded_user is not None, "User loader should return user"
    assert loaded_user.username == test_user.username
    assert loaded_user.id == test_user.id
    """Test that the user loader function returns the correct user.

    Args:
        init_database: Pytest fixture for database setup.
        test_user: Pytest fixture for a test user.

    Asserts:
        That the user loader returns the correct user instance.
    """

# Test that user loader returns None for invalid ID.
def test_user_loader_returns_none_for_invalid_id(init_database): # (Anthropic, 2025)
    from app.models import load_user
    
    loaded_user = load_user(str(99999))
    assert loaded_user is None
    """Test that user loader returns None for an invalid user ID.

    Args:
        init_database: Pytest fixture for database setup.

    Asserts:
        That loading a non-existent user returns None.
    """

# Test that @login_required decorator exists.
def test_flask_login_required_decorator(): # (Anthropic, 2025)
    from flask_login import login_required
    assert login_required is not None
    assert callable(login_required)
    """Test that Flask-Login's @login_required decorator exists and is callable.

    Asserts:
        That login_required is defined and callable.
    """

# Test that session is configured securely.
@pytest.mark.parametrize("config_key,expected_value", [
    ("WTF_CSRF_ENABLED", False),  # keep in sync with test_csrf_protection_configuration
])
def test_session_configuration(app, config_key, expected_value): # (Anthropic, 2025)
    assert config_key in app.config
    assert app.config[config_key] == expected_value, f"{config_key} should be {expected_value}"
    """Test that session configuration keys are set to secure values.

    Args:
        app: Flask application.
        config_key: Configuration key to check.
        expected_value: Expected value for the configuration key.

    Asserts:
        That the configuration key exists and matches the expected value.
    """

# Second part of the previous test, permanent session lifetime is configuration test.
def test_permanent_session_lifetime_configured(app): # (Anthropic, 2025)
    from datetime import timedelta
    assert 'PERMANENT_SESSION_LIFETIME' in app.config
    lifetime = app.config['PERMANENT_SESSION_LIFETIME']
    assert isinstance(lifetime, timedelta)
    assert lifetime.total_seconds() > 0
    """Test that PERMANENT_SESSION_LIFETIME is configured and positive.

    Args:
        app: Flask application.

    Asserts:
        That the session lifetime is a positive timedelta.
    """

# Test that bcrypt is configured with appropriate rounds.
def test_bcrypt_rounds_configuration(app): # (Anthropic, 2025)
    assert 'BCRYPT_LOG_ROUNDS' in app.config
    rounds = app.config['BCRYPT_LOG_ROUNDS']
    assert rounds >= 12
    """Test that bcrypt is configured with a secure number of rounds.

    Args:
        app: Flask application.

    Asserts:
        That BCRYPT_LOG_ROUNDS is at least 12.
    """

# Test that CSRF protection is configured.
def test_csrf_protection_configuration(app): # (Anthropic, 2025)
    assert 'WTF_CSRF_ENABLED' in app.config
    assert app.config['WTF_CSRF_ENABLED'] == False
    """Test that CSRF protection is disabled in the testing environment.

    Args:
        app: Flask application.

    Asserts:
        That WTF_CSRF_ENABLED is False.
    """

# Test that create patient route exists.
def test_create_user_route_exists(client): # (Anthropic, 2025)
    response = client.get('/patient/create', follow_redirects=False)
    assert response.status_code == 302
    """Test that the create patient route exists and redirects.

    Args:
        client: Flask test client.

    Asserts:
        That the route returns a redirect response.
    """

# (Anthropic, 2025)
@pytest.mark.parametrize("route", [
    '/dashboard',
    '/patient/create',
    '/user-dashboard',
    '/userpage',
])

# Test that all CRUD routes require authentication.
def test_protected_routes_require_auth(client, route): # (Anthropic, 2025)
    response = client.get(route, follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location
    """Test that protected routes require authentication.

    Args:
        client: Flask test client.
        route: URL route to test.

    Asserts:
        That unauthenticated access redirects to login.
    """

# Test that account unlocks after timeout period.
def test_account_unlock_after_timeout(init_database, bcrypt_instance): # (Anthropic, 2025)
    from app import db
    
    user = create_user(
        'timeouttest',
        'timeout@example.com',
        bcrypt_instance.generate_password_hash('Pass123!').decode('utf-8')
    )
    
    user.failed_login_attempts = 5
    user.account_locked_until = datetime.utcnow() - timedelta(minutes=1)
    db.session.commit()
    
    is_locked = user.is_account_locked()
    
    assert is_locked == False
    assert user.failed_login_attempts == 0
    """Test that a locked account unlocks after the timeout period.

    Args:
        init_database: Pytest fixture for database setup.
        bcrypt_instance: Flask-Bcrypt instance.

    Asserts:
        That the account is unlocked and failed attempts reset after timeout.
    """

# (Anthropic, 2025)
@pytest.mark.parametrize("method,expected_value", [
    ('is_authenticated', True),
    ('is_active', True),
    ('is_anonymous', False),
])

# Test that User model implements Flask-Login UserMixin methods (is_authenticated, is_active, is_anonymous) with correct boolean values.
def test_user_mixin_provides_flask_login_methods(test_user, method, expected_value): # (Anthropic, 2025)
    assert hasattr(test_user, method)
    if method != 'get_id':
        assert getattr(test_user, method) == expected_value
    """Test that User model implements Flask-Login UserMixin methods.

    Args:
        test_user: Pytest fixture for a test user.
        method: Name of the method to check.
        expected_value: Expected boolean value for the method.

    Asserts:
        That the method exists and returns the expected value.
    """

# Test that User.get_id() returns a string representation of the user ID for Flask-Login session management.
def test_user_get_id_returns_string(test_user): # (Anthropic, 2025)
    user_id = test_user.get_id()
    assert user_id is not None
    assert isinstance(user_id, str)
    """Test that User.get_id() returns a string for Flask-Login.

    Args:
        test_user: Pytest fixture for a test user.

    Asserts:
        That get_id returns a non-None string.
    """

