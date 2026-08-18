# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" This is the Database Models module.

using SQLAlchemy for user authentication and audit logging.
"""

from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager
import hmac
import hashlib
import os
from cryptography.fernet import Fernet

# Initialize HMAC key for deterministic hashing (duplicate checking)
PATIENT_ID_HMAC_KEY = os.environ.get('PATIENT_ID_HMAC_KEY', 'default-dev-key-change-in-production').encode()

# Initialize Fernet encryption for reversible encryption (data retrieval)
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key()
elif isinstance(ENCRYPTION_KEY, str):
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

def hash_patient_id(patient_id): # (Anthropic, 2025)
    if patient_id is None:
        return None
    return hmac.new(PATIENT_ID_HMAC_KEY, str(patient_id).encode(), hashlib.sha256).hexdigest()

    """ Create deterministic hash of patient_id using HMAC for duplicate checking.

    Args:
        patient_id: Patient ID value.

    Returns:
        Hex digest string of the HMAC hash, or None if patient_id is None.
    """

# User model for authentication, stores the user credentials and account information, users are linked to patient records via their patient_id's.
class User(UserMixin, db.Model): # (Anthropic, 2025)
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    patient_id_hash = db.Column(db.String(64), unique=True, nullable=True, index=True)  # HMAC hash for duplicate checking.
    _patient_id_encrypted = db.Column('patient_id_encrypted', db.String(256), nullable=True)  # Fernet encrypted for retrieval.
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    # Intentionally overrides UserMixin.is_active property to persist in database.
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # type: ignore[assignment]
    role = db.Column(db.String(20), default='user', nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    account_locked_until = db.Column(db.DateTime)
    
    # Relationships.
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def patient_id(self): # (Anthropic, 2025)
        if self._patient_id_encrypted:
            try:
                decrypted = cipher_suite.decrypt(self._patient_id_encrypted.encode())
                return int(decrypted.decode())
            except Exception:
                return None
        return None
    
        """ Decrypt and return the patient_id.

        Returns:
            Decrypted patient_id as int, or None if not available.
        """

    def set_patient_id(self, patient_id): # (Anthropic, 2025)
        if patient_id is not None:
            # Store hash for duplicate checking.
            self.patient_id_hash = hash_patient_id(patient_id)
            # Store encrypted value for retrieval.
            encrypted = cipher_suite.encrypt(str(patient_id).encode())
            self._patient_id_encrypted = encrypted.decode()
        else:
            self.patient_id_hash = None
            self._patient_id_encrypted = None
            
        """ Hash and encrypt the patient_id for storage.

        Args:
            patient_id: Patient ID value to store.
        """

    @staticmethod
    def query_by_patient_id(patient_id): # (Anthropic, 2025)
        patient_hash = hash_patient_id(patient_id)
        return User.query.filter_by(patient_id_hash=patient_hash).first()
    
        """ Query user by patient_id (using hash comparison).

        Args:
            patient_id: Patient ID value.

        Returns:
            User instance or None.
        """

    @staticmethod
    def patient_id_exists(patient_id): # (Anthropic, 2025)
        patient_hash = hash_patient_id(patient_id)
        return User.query.filter_by(patient_id_hash=patient_hash).first() is not None
    
        """ Check if a patient_id is already registered.

        Args:
            patient_id: Patient ID value.

        Returns:
            True if exists, False otherwise.
        """

    def __repr__(self): # (Anthropic, 2025)
        return f'<User {self.username}>'

    # Check if the account is currently locked.
    def is_account_locked(self): # (Anthropic, 2025)
        if self.account_locked_until:
            if datetime.utcnow() < self.account_locked_until:
                return True
            else:
                # Lock expired, reset.
                self.account_locked_until = None
                self.failed_login_attempts = 0
                db.session.commit()
        return False
    
        """ Check if the account is currently locked.

        Returns:
            True if locked, False otherwise.
        """

    def increment_failed_login(self): # (Anthropic, 2025)
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Lock the account for 15 minutes.
            from datetime import timedelta
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        
        """ Increment failed login attempts and lock if threshold exceeded.

        Returns:
            Updates failed_login_attempts and may set account_locked_until.
        """

    def reset_failed_login(self): # (Anthropic, 2025)
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()
        
        """ Reset failed login attempts on successfully logging in.

        Side Effects:
            Resets failed_login_attempts and account_locked_until.
        """

# Audit log model, for tracking all the CRUD operations and providing accountability with security monitoring.
class AuditLog(db.Model): # (Anthropic, 2025)
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)  # Create, Read, Update, Delete, Login, and Logout.
    table_name = db.Column(db.String(50), nullable=False)  # users, patient_records.
    record_id = db.Column(db.String(100))  # ID of affected record.
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6.
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    details = db.Column(db.Text)  # Additional context, JSON serialized.
    
    def __repr__(self): # (Anthropic, 2025)
        return f'<AuditLog {self.action} by User {self.user_id} at {self.timestamp}>'

@login_manager.user_loader
def load_user(user_id): # (Anthropic, 2025)
        if user_id.startswith('admin_'):
            # Loads from thte admin database.
            from app.admin_models import AdminUser
            admin_id = int(user_id.split('_')[1])
            admin = AdminUser.query.get(admin_id)
            if admin:
                # Adds a prefix to id's for session management.
                admin.id = user_id
                admin.is_admin = True
            return admin
        
        elif user_id.startswith('user_'):
            # Loads from the user database.
            std_user_id = int(user_id.split('_')[1])
            user = User.query.get(std_user_id)
            if user:
                user.id = user_id
                user.is_admin = False
            return user
        
        """ Flask-Login user loader for both admin and user databases.

        Args:
            user_id: User ID string, prefixed with 'admin_' or 'user_'.

        Returns:
            User or AdminUser instance, or None if not found.
        """

