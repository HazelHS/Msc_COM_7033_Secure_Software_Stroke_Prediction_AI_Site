# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" This is the Authentication module.

Handles user registration, login, and logout. With support for both authentication of "admin" and "users".
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app import db, bcrypt, limiter, mongo_db
from app.models import User
from app.admin_models import AdminUser
from app.forms import RegistrationForm, LoginForm
from app.security import log_audit, sanitize_input, generate_search_hash, generate_2fa_code, send_2fa_code, store_2fa_code, verify_2fa_code

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")  # Rate limit registration to prevent abuse

# User registration endpoint, creates new user account with email as username, and will validate that the patient_id inputted at creation exists in the MongoDB database, and is not already registered.
def register(): # (Anthropic, 2025)
    if current_user.is_authenticated:
        # Redirect based on user type.
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return redirect(url_for('crud.dashboard'))
        else:
            return redirect(url_for('crud.user_dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit(): # (Anthropic, 2025)
        email = form.email.data  # Emails are used as usernames.
        patient_id = form.patient_id.data
        
        # Validate that patient_id exists in the MongoDB database.
        if mongo_db is None:
            flash('Database connection error, contact site administrator.', 'danger')
            return render_template('auth/register.html', form=form)
        
        try:
            collection = mongo_db.patient_records
            
            # Search for the patient by ID using HMAC hashes.
            search_hash = generate_search_hash(str(patient_id), 'id')
            patient_record = collection.find_one({'id_search': search_hash})
            
            # If no record are found, reject registration.
            if not patient_record:
                flash('Patient ID not found in our records. Please verify your ID and try again.', 'danger')
                return render_template('auth/register.html', form=form)
            
        except Exception as e:
            flash('Error validating Patient ID. Please try again.', 'danger')
            return render_template('auth/register.html', form=form)
        
        # Hash the passwords with bcrypt.
        password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        
        # Create new user.
        user = User()
        user.username = email  # Email is used as username.
        user.email = email
        user.set_patient_id(form.patient_id.data)
        user.password_hash = password_hash
        user.role = 'user'
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log registration.
            log_audit(
                user_id=user.id,
                action='REGISTER',
                table_name='users',
                record_id=user.id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            flash('Registration successful, you can now log in with your email and password.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('auth/register.html', form=form)
    
    return render_template('auth/register.html', form=form)

    """ User registration endpoint.

    Returns:
        Rendered registration template or redirect.
    """

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per 5 minutes")  # Rate limit login attempts.

# User login endpoint, authenticates users from both admin.db and users.db databases.
def login(): # (Anthropic, 2025)
    if current_user.is_authenticated:
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            return redirect(url_for('crud.dashboard'))
        else:
            return redirect(url_for('crud.user_dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data
        
        # First, check if it's an admin user.
        admin = AdminUser.query.filter_by(username=username).first()
        
        if admin:
            # Administrator login.
            if admin.is_account_locked():
                flash('Account is locked due to multiple failed login attempts. Please try again in 15 minutes.', 'danger')
                return render_template('auth/login.html', form=form)
            
            if bcrypt.check_password_hash(admin.password_hash, password):
                if not admin.is_active:
                    flash('Your account has been deactivated. Please contact support.', 'danger')
                    return render_template('auth/login.html', form=form)
                
                # Check if admin has a email and enable "Two Factor Authentication" (2FA) if email is present.
                if admin.email:
                    # Generate and send 2FA code.
                    code = generate_2fa_code()
                    if send_2fa_code(admin.email, code):
                        # Store code in session.
                        store_2fa_code(session, code, admin.id)
                        session['pending_admin_id'] = admin.id
                        session['remember_me'] = remember
                        flash('A verification code has been sent to your email.', 'info')
                        return redirect(url_for('auth.admin_2fa'))
                    else:
                        flash('Failed to send verification code. Please try again.', 'danger')
                        return render_template('auth/login.html', form=form)
                
                # No email, proceed with normal login.
                admin.is_admin = True
                original_id = admin.id
                admin.id = f"admin_{admin.id}"
                login_user(admin, remember=remember)
                admin.id = original_id  # Reset for database operations.
                admin.reset_failed_login()
                
                flash(f'Welcome back {admin.username}.', 'success')
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('crud.dashboard'))
            
            else:
                admin.increment_failed_login()
                flash('Invalid username or password.', 'danger')
        
        else:
            # Check standard user database.
            user = User.query.filter_by(username=username).first()
            
            if user:
                if user.is_account_locked():
                    flash('Account is locked due to multiple failed login attempts. Please try again in 15 minutes.', 'danger')
                    return render_template('auth/login.html', form=form)
                
                if bcrypt.check_password_hash(user.password_hash, password):
                    if not user.is_active:
                        flash('Your account has been deactivated. Please contact support.', 'danger')
                        return render_template('auth/login.html', form=form)
                    
                    # Successful user login, uses prefixed ID.
                    user.is_admin = False
                    original_id = user.id
                    user.id = f"user_{user.id}"
                    login_user(user, remember=remember)
                    user.id = original_id  # Reset for database operations.
                    user.reset_failed_login()
                    
                    # Log successful login.
                    log_audit(
                        user_id=original_id,
                        action='LOGIN',
                        table_name='users',
                        record_id=original_id,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent')
                    )
                    
                    flash(f'Welcome back, {user.username}.', 'success')
                    
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('crud.user_dashboard'))
                
                else:
                    user.increment_failed_login()
                    
                    # Log failed login attempts.
                    log_audit(
                        user_id=user.id,
                        action='FAILED_LOGIN',
                        table_name='users',
                        record_id=user.id,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get('User-Agent'),
                        details='Invalid password'
                    )
                    
                    flash('Invalid username or password.', 'danger')
            else:
                flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html', form=form)

    """ User login endpoint, authenticates users from both admin and user databases.

    Returns:
        Rendered login template or redirect.
    """

@auth_bp.route('/admin-2fa', methods=['GET', 'POST'])
@limiter.limit("10 per 5 minutes")

# Admin 2FA verification page.
def admin_2fa(): # (Anthropic, 2025)
    from app.forms import TwoFactorForm
    
    # Check if there's a pending admin login.
    pending_admin_id = session.get('pending_admin_id')
    if not pending_admin_id:
        flash('No pending authentication. Please log in.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = TwoFactorForm()
    
    if form.validate_on_submit():
        entered_code = form.code.data
        
        # Verify the code.
        is_valid, message = verify_2fa_code(session, entered_code, pending_admin_id)
        
        if is_valid:
            # Complete admin login.
            admin = AdminUser.query.get(pending_admin_id)
            if admin and admin.is_active:
                admin.is_admin = True
                original_id = admin.id
                admin.id = f"admin_{admin.id}"
                remember = session.get('remember_me', False)
                login_user(admin, remember=remember)
                admin.id = original_id
                admin.reset_failed_login()
                
                # Clear session data.
                session.pop('pending_admin_id', None)
                session.pop('remember_me', None)
                
                flash(f'Welcome back {admin.username}.', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('crud.dashboard'))
            else:
                flash('Admin account not found or inactive.', 'danger')
                return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
    
    return render_template('auth/admin_2fa.html', form=form)

    """ Admin 2FA verification page.

    Returns:
        Rendered 2FA verification template or redirect.
    """

@auth_bp.route('/logout')
@login_required
def logout(): # (Anthropic, 2025)
    if current_user.is_authenticated:
        # Extract actual user's ID for logging.
        if hasattr(current_user, 'is_admin') and current_user.is_admin:
            user_id_str = str(current_user.id)
            if user_id_str.startswith('admin_'):
                user_id = int(user_id_str.split('_')[1])
            else:
                user_id = current_user.id
        else:
            user_id_str = str(current_user.id)
            if user_id_str.startswith('user_'):
                user_id = int(user_id_str.split('_')[1])
            else:
                user_id = current_user.id
        
        # Log the logout.
        log_audit(
            user_id=user_id,
            action='LOGOUT',
            table_name='users',
            record_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        logout_user()
        flash('You have been logged out successfully.', 'info')
    
    return redirect(url_for('auth.login'))

    """ User logout endpoint, destroys user's session.

    Returns:
        Redirect to login page.
    """

@auth_bp.route('/userpage', methods=['GET'])
@limiter.limit("20 per hour")

def userpage(): # (Anthropic, 2025)
    from flask_login import login_required
    from app.forms import ChangePasswordForm, ChangeEmailForm, DeleteAccountForm
    
    if not current_user.is_authenticated:
        flash('Please log in to access your account page.', 'info')
        return redirect(url_for('auth.login'))
    
    change_password_form = ChangePasswordForm()
    change_email_form = ChangeEmailForm()
    delete_account_form = DeleteAccountForm()
    
    return render_template('auth/userpage.html',
                         change_password_form=change_password_form,
                         change_email_form=change_email_form,
                         delete_account_form=delete_account_form)
    
    """ User account management page, allows users to change password, email, or delete account.

    Returns:
        Rendered user account management template.
    """

@auth_bp.route('/change-password', methods=['POST'])
@limiter.limit("5 per hour")

# Change user password endpoint.
def change_password(): # (Anthropic, 2025)
    from flask_login import login_required
    from app.forms import ChangePasswordForm
    
    if not current_user.is_authenticated:
        flash('Please log in to change your password.', 'info')
        return redirect(url_for('auth.login'))
    
    form = ChangePasswordForm()
    
    # Remove current_user from session to prevent id field conflict during commit.
    if current_user in db.session:
        db.session.expunge(current_user)
    
    # Use no_autoflush to prevent SQLAlchemy from trying to update current_user's modified id field.
    with db.session.no_autoflush:
        if form.validate_on_submit():
            # Verify current password.
            is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
            
            if is_admin:
                # Get actual admin user from database.
                user_id_str = str(current_user.id)
                if user_id_str.startswith('admin_'):
                    admin_id = int(user_id_str.split('_')[1])
                else:
                    try:
                        admin_id = int(user_id_str)
                    except (ValueError, TypeError):
                        flash('Invalid user session.', 'danger')
                        return redirect(url_for('auth.login'))
                
                admin = AdminUser.query.get(admin_id)
                
                if not admin or not bcrypt.check_password_hash(admin.password_hash, form.current_password.data):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('auth.userpage'))
                
                # Update password.
                admin.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
                db.session.commit()
                
            else:
                # Get actual user from database.
                user_id_str = str(current_user.id)
                if user_id_str.startswith('user_'):
                    user_id = int(user_id_str.split('_')[1])
                else:
                    try:
                        user_id = int(user_id_str)
                    except (ValueError, TypeError):
                        flash('Invalid user session.', 'danger')
                        return redirect(url_for('auth.login'))
                
                user = User.query.get(user_id)
                
                if not user or not bcrypt.check_password_hash(user.password_hash, form.current_password.data):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('auth.userpage'))
                
                # Update password.
                user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
                db.session.commit()
                
                # Log password change.
                log_audit(
                    user_id=user_id,
                    action='PASSWORD_CHANGE',
                    table_name='users',
                    record_id=user_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
            
            flash('Your password has been changed successfully!', 'success')
            return redirect(url_for('auth.userpage'))
    
    # Form validation failed.
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    
    return redirect(url_for('auth.userpage'))

    """ Change user password endpoint.

    Returns:
        Redirect to user account page.
    """

@auth_bp.route('/change-email', methods=['POST'])
@limiter.limit("5 per hour")

# Change user email/username endpoint, however admin users cannot change their email, as "admin" is not an email. This was chosen for simplicity, rather than adding an additional email field for admin users only.
def change_email(): # (Anthropic, 2025)
    from flask_login import login_required
    from app.forms import ChangeEmailForm
    
    if not current_user.is_authenticated:
        flash('Please log in to change your email.', 'info')
        return redirect(url_for('auth.login'))
    
    # Check if user is admin.
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    
    if is_admin:
        flash('Admin accounts cannot change their email address.', 'danger')
        return redirect(url_for('auth.userpage'))
    
    form = ChangeEmailForm()
    
    # Remove current_user from session to prevent id field conflict during commit.
    if current_user in db.session:
        db.session.expunge(current_user)
    
    # Use no_autoflush to prevent SQLAlchemy from trying to update current_user's modified id field, this wraps the entire validation and processing.
    with db.session.no_autoflush:
        if form.validate_on_submit():
            # Get actual user ID (extract integer from prefixed string).
            user_id_str = str(current_user.id)
            if user_id_str.startswith('user_'):
                user_id = int(user_id_str.split('_')[1])
            else:
                try:
                    user_id = int(user_id_str)
                except (ValueError, TypeError):
                    flash('Invalid user session.', 'danger')
                    return redirect(url_for('auth.login'))
            
            user = User.query.get(user_id)
            
            if not user or not bcrypt.check_password_hash(user.password_hash, form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.userpage'))
            
            # Store old email for logging.
            old_email = user.email
            
            # Update email and username (email is used as username).
            user.email = form.new_email.data
            user.username = form.new_email.data
            
            # Commit outside will happen after the no_autoflush block.
            db.session.commit()
            
            # Log email change.
            log_audit(
                user_id=user_id,
                action='EMAIL_CHANGE',
                table_name='users',
                record_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details=f'Email changed from {old_email} to {form.new_email.data}'
            )
            
            flash('Your email has been changed successfully! Please use your new email to log in next time.', 'success')
            return redirect(url_for('auth.userpage'))
    
    # Form validation failed.
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    
    return redirect(url_for('auth.userpage'))

    """ Change user email/username endpoint.

    Returns:
        Redirect to user account page.
    """

@auth_bp.route('/delete-account', methods=['POST'])
@limiter.limit("3 per hour")

# Delete user account endpoint, deletes associated patient data from the MongoDB database. The administrator however cannot delete their account, similar to email change. Without a valid admin account there would be no way to recover admin privileges without additional functionality.
def delete_account(): # (Anthropic, 2025)
    from flask_login import login_required
    from app.forms import DeleteAccountForm
    
    if not current_user.is_authenticated:
        flash('Please log in to delete your account.', 'info')
        return redirect(url_for('auth.login'))
    
    # Check if user is admin.
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    
    if is_admin:
        flash('Admin accounts cannot be deleted.', 'danger')
        return redirect(url_for('auth.userpage'))
    
    form = DeleteAccountForm()
    
    # Remove current_user from session to prevent id field conflict during commit.
    if current_user in db.session:
        db.session.expunge(current_user)

    # Use no_autoflush to prevent SQLAlchemy from trying to update current_user's modified id field.
    with db.session.no_autoflush:
        if form.validate_on_submit():
            # Get actual user from database.
            user_id_str = str(current_user.id)
            if user_id_str.startswith('user_'):
                user_id = int(user_id_str.split('_')[1])
            else:
                try:
                    user_id = int(user_id_str)
                except (ValueError, TypeError):
                    flash('Invalid user session.', 'danger')
                    return redirect(url_for('auth.login'))
            
            user = User.query.get(user_id)
            
            if not user or not bcrypt.check_password_hash(user.password_hash, form.confirm_password.data):
                flash('Password is incorrect.', 'danger')
                return redirect(url_for('auth.userpage'))
            
            # Verify the confirmation text.
            if not form.confirm_text.data or form.confirm_text.data.upper() != 'DELETE':
                flash('You must type "DELETE" to confirm account deletion.', 'danger')
                return redirect(url_for('auth.userpage'))
            
            # Store patient_id for logging before deletion.
            patient_id = user.patient_id
            
            # Delete associated patient data from MongoDB.
            if mongo_db is not None and patient_id:
                try:
                    collection = mongo_db.patient_records
                    search_hash = generate_search_hash(str(patient_id), 'id')
                    result = collection.delete_one({'id_search': search_hash})
                    
                    if result.deleted_count > 0:
                        flash(f'Your patient record (ID: {patient_id}) has been permanently deleted as requested.', 'info')
                except Exception as e:
                    flash('Error deleting patient data. Please contact administrator.', 'warning')
            
            # Log account deletion.
            log_audit(
                user_id=user_id,
                action='DELETE_ACCOUNT',
                table_name='users',
                record_id=user_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details=f'Account deleted with patient_id: {patient_id}'
            )
            
            # Delete user account.
            db.session.delete(user)
            db.session.commit()
            
            # Log out user.
            logout_user()
            
            flash('Your account and all associated data have been permanently deleted. Thank you for using our service.', 'success')
            return redirect(url_for('index'))
    
    # Form validation failed.
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    
    return redirect(url_for('auth.userpage'))

    """ Delete user account endpoint.

    Returns:
        Redirect to user account page or index after deletion.
    """

@auth_bp.route('/admin/change-email', methods=['POST'])
@limiter.limit("5 per hour")

# Change admin email endpoint.
def admin_change_email(): # (Anthropic, 2025)
    from flask_login import login_required
    from app.forms import AdminEmailForm
    
    if not current_user.is_authenticated:
        flash('Please log in to change your email.', 'info')
        return redirect(url_for('auth.login'))
    
    # Check if user is admin.
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    
    if not is_admin:
        flash('Only admin users can access this feature.', 'danger')
        return redirect(url_for('auth.userpage'))
    
    form = AdminEmailForm()
    
    # Remove current_user from session to prevent id field conflict during commit.
    if current_user in db.session:
        db.session.expunge(current_user)
    
    with db.session.no_autoflush:
        if form.validate_on_submit():
            # Get actual admin ID.
            user_id_str = str(current_user.id)
            if user_id_str.startswith('admin_'):
                admin_id = int(user_id_str.split('_')[1])
            else:
                try:
                    admin_id = int(user_id_str)
                except (ValueError, TypeError):
                    flash('Invalid user session.', 'danger')
                    return redirect(url_for('auth.login'))
            
            admin = AdminUser.query.get(admin_id)
            
            if not admin or not bcrypt.check_password_hash(admin.password_hash, form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.userpage'))
            
            # Store old email for logging.
            old_email = admin.email or "None"
            
            # Update email.
            admin.email = form.new_email.data
            
            db.session.commit()
            
            flash(f'Your email has been {"updated" if old_email != "None" else "added"} successfully! 2FA will be enabled on your next login.', 'success')
            return redirect(url_for('auth.userpage'))
    
    # Form validation failed.
    for field, errors in form.errors.items():
        for error in errors:
            flash(error, 'danger')
    
    return redirect(url_for('auth.userpage'))

    """ Change admin email endpoint.

    Returns:
        Redirect to user account page.
    """

