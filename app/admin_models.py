# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" User and Administrator Models module.

This module defines two models, used for seperating both the "user" and 
"admin" authentication and audit logs into their own databases for additional security.
"""

from datetime import datetime
from flask_login import UserMixin
from app import db

class AdminUser(UserMixin, db.Model): # (Anthropic, 2025)
    __tablename__ = 'admin_users'
    __bind_key__ = 'admin'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)  # Added email field.
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Intentionally overrides UserMixin.is_active property to persist in the database.
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # type: ignore[assignment]
    role = db.Column(db.String(20), default='admin', nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    account_locked_until = db.Column(db.DateTime)
    
    def __repr__(self): # (Anthropic, 2025)
        return f'<AdminUser {self.username}>'
    
    def is_account_locked(self): # (Anthropic, 2025)
        if self.account_locked_until:
            if datetime.utcnow() < self.account_locked_until:
                return True
            else:
                # Lock expired, reset
                self.account_locked_until = None
                self.failed_login_attempts = 0
                db.session.commit()
        return False
    
        """ Check if the admin account is currently locked.

        Returns:
            True if locked, False otherwise.
        """

    def increment_failed_login(self): # (Anthropic, 2025)
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            # Lock account for 15 minutes
            from datetime import timedelta
            self.account_locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.session.commit()
        
        """ Increment failed login attempts and lock if threshold is exceeded.

        Returns:
            Updates failed_login_attempts and may set account_locked_until.
        """

    def reset_failed_login(self): # (Anthropic, 2025)
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()
        
        """ Reset failed login attempts when successfully logged in.

        Returns:
            Resets failed_login_attempts and account_locked_until.
        """

# Administrator audit log model,for tracking admin operations stored in admin.db.
class AdminAuditLog(db.Model): # (Anthropic, 2025)
    __tablename__ = 'admin_audit_logs'
    __bind_key__ = 'admin'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False, index=True)
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    details = db.Column(db.Text)
    
    def __repr__(self): # (Anthropic, 2025)
        return f'<AdminAuditLog {self.action} by Admin {self.admin_id} at {self.timestamp}>'

