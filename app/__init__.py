# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Flask Application Factory modeule. 

Initializes and configures the Flask application with security extensions and 
supports both SQLite databases for "users.db" (standard users) and the "admin.db" for the administrator.
"""

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from pymongo import MongoClient
from config import config
import os

# (Anthropic, 2025), Initialize extensions.
db = SQLAlchemy() 
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["5000 per day", "1000 per hour"],  # Increased global limits, set this to 500, 100 for default restrictions, was increased for manual testing.
    storage_uri="memory://"
)

# MongoDB client, initialized in create_app.
mongo_client = None
mongo_db = None

def create_app(config_name=None): # (Anthropic, 2025)
    app = Flask(__name__)
    
    # Loads the configurations.
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Configure database binds for both database's setup.
    app.config['SQLALCHEMY_BINDS'] = {
        'admin': app.config.get('ADMIN_DATABASE_URI', 'sqlite:///admin.db')
    }
    
    # Initialize extensions with app.
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    
    # Configure Flask-Login.
    login_manager.login_view = 'auth.login'  # type: ignore[assignment]
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    # Initialize Flask-Talisman (Security Headers, for HTTPS).
    if not app.config['DEBUG']:
        Talisman(
            app,
            force_https=app.config['TALISMAN_FORCE_HTTPS'],
            strict_transport_security=app.config['TALISMAN_STRICT_TRANSPORT_SECURITY'],
            strict_transport_security_max_age=app.config['TALISMAN_STRICT_TRANSPORT_SECURITY_MAX_AGE'],
            content_security_policy=app.config['TALISMAN_CONTENT_SECURITY_POLICY'],
            content_security_policy_nonce_in=['script-src']
        )
    
    # Initialize MongoDB.
    global mongo_client, mongo_db
    try:
        mongo_client = MongoClient(
            app.config['MONGODB_URI'],
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        mongo_db = mongo_client[app.config['MONGODB_DB']]
        # Test connection.
        mongo_client.server_info()
        app.logger.info("MongoDB connection successful")
        
    except Exception as e:
        app.logger.error(f"MongoDB connection failed: {e}")
        app.logger.warning("Running without MongoDB support")
        mongo_db = None
    
    # Register blueprints.
    from app.auth import auth_bp
    from app.crud import crud_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(crud_bp)
    
    # Only create tables if not in testing mode.
    if not app.config.get('TESTING', False):
        with app.app_context():
            from app.admin_models import AdminUser, AdminAuditLog
            db.create_all()
    
    # Error handlers.
    @app.errorhandler(404)
    def not_found_error(error): # (Anthropic, 2025)
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error): # (Anthropic, 2025)
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(429)
    def ratelimit_handler(e): # (Anthropic, 2025)
        return render_template('errors/429.html', error=e.description), 429
    
    # Context processor for the MongoDB status, makes a MongoDB connection status available to all HTML templates.
    @app.context_processor
    def inject_mongodb_status(): # (Anthropic, 2025)
        return {'mongodb_connected': mongo_db is not None}
    
    # Index route.
    @app.route('/')
    def index(): # (Anthropic, 2025)
        return render_template('index.html')
    
    return app

    """ Flask application factory.

    Args:
        config_name: Name of the configuration to use.

    Returns:
        Configured Flask app instance.
    """

