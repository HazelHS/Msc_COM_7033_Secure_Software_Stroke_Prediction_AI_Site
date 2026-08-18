# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" This is the Flask-WTF Forms module.

Used to sanitise user input and use "Cross-Site Request Forgery" (CSRF) protection. 
CSRF is when a different malicious website tricks a user's browser, into submitting unwanted actions. 
These attacks can be carried out using insecure session cookies to make requests without the user's consent. 
Flask-WTF generates tokens to validate that only session cookies generated from this site can be accepted).
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, FloatField, SelectField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
from app.models import User
from app.security import validate_password_strength
import bleach

# User registration form with emails are used as username.
class RegistrationForm(FlaskForm): # (Anthropic, 2025)
    email = StringField('Email (This will be your username)',
                       validators=[
                           DataRequired(message="Email is required."),
                           Email(message="Invalid email address.")
                       ])
    
    patient_id = IntegerField('Patient ID',
                             validators=[
                                 DataRequired(message="Patient ID is required.")
                             ])
    
    password = PasswordField('Password',
                            validators=[
                                DataRequired(message="Password is required."),
                                Length(min=12, message="Password must be at least 12 characters.")
                            ])
    
    confirm_password = PasswordField('Confirm Password',
                                    validators=[
                                        DataRequired(message="Please confirm your password."),
                                        EqualTo('password', message="Passwords must match.")
                                    ])
    
    def validate_email(self, email): # (Anthropic, 2025)
        # Sanitize the input.
        clean_email = bleach.clean(email.data, tags=[], strip=True).lower()
        user = User.query.filter_by(email=clean_email).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')
        
        # Use email will be used as username.
        user_by_username = User.query.filter_by(username=clean_email).first()
        if user_by_username:
            raise ValidationError('Email already registered. Please use a different one.')
        email.data = clean_email
        
        """ Check if the email already exists and sanitize it.

        Args:
            email: WTForms field.

        Raises:
            ValidationError: If email is already registered.
        """

    def validate_patient_id(self, patient_id): # (Anthropic, 2025) 
        if patient_id.data:
            from app.models import User
            if User.patient_id_exists(patient_id.data):
                raise ValidationError('This Patient ID is already registered.')
            
        """ Validate that the patient_id is not already registered.

        Args:
            patient_id: WTForms field.

        Raises:
            ValidationError: If patient_id is already registered.
        """

    def validate_password(self, password): # (Anthropic, 2025)
        is_valid, error_message = validate_password_strength(password.data)
        if not is_valid:
            raise ValidationError(error_message or "Password does not meet security requirements.")
        
        """ Validate password strength.

        Args:
            password: WTForms field.

        Raises:
            ValidationError: If password does not meet requirements.
        """

# The user login form.
class LoginForm(FlaskForm): # (Anthropic, 2025)  
    username = StringField('Username',
                          validators=[
                              DataRequired(message="Username is required."),
                              Length(min=3, max=80)
                          ])
    
    password = PasswordField('Password',
                            validators=[
                                DataRequired(message="Password is required.")
                            ])
    
    remember_me = BooleanField('Remember Me')
    
    def validate_username(self, username): # (Anthropic, 2025)
        username.data = bleach.clean(username.data, tags=[], strip=True)
        
        """ Sanitize the username input.

        Args:
            username: WTForms field.
        """

# Form for creating and updating the patient records.
class PatientRecordForm(FlaskForm): # (Anthropic, 2025)   
    patient_id = IntegerField('Patient ID (Optional)',
                             validators=[
                                 Optional(),
                                 NumberRange(min=1, max=999999999, message="Patient ID must be between 1 and 999999999.")
                             ],
                             render_kw={"placeholder": "Auto-generated if not provided"})
    
    gender = SelectField('Gender',
                        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
                        validators=[DataRequired(message="Gender is required.")])
    
    age = FloatField('Age',
                    validators=[
                        DataRequired(message="Age is required."),
                        NumberRange(min=0, max=120, message="Age must be between 0 and 120.")
                    ])
    
    hypertension = SelectField('Hypertension',
                              choices=[('0', 'No'), ('1', 'Yes')],
                              validators=[DataRequired()])
    
    heart_disease = SelectField('Heart Disease',
                               choices=[('0', 'No'), ('1', 'Yes')],
                               validators=[DataRequired()])
    
    ever_married = SelectField('Ever Married',
                              choices=[('Yes', 'Yes'), ('No', 'No')],
                              validators=[DataRequired()])
    
    work_type = SelectField('Work Type',
                           choices=[
                               ('Private', 'Private'),
                               ('Self-employed', 'Self-employed'),
                               ('Govt_job', 'Government Job'),
                               ('children', 'Children'),
                               ('Never_worked', 'Never Worked')
                           ],
                           validators=[DataRequired()])
    
    residence_type = SelectField('Residence Type',
                                choices=[('Urban', 'Urban'), ('Rural', 'Rural')],
                                validators=[DataRequired()])
    
    avg_glucose_level = FloatField('Average Glucose Level',
                                  validators=[
                                      DataRequired(message="Glucose level is required."),
                                      NumberRange(min=0, max=500, message="Glucose level must be between 0 and 500.")
                                  ])
    
    bmi = StringField('BMI',
                     validators=[Optional()])
    
    smoking_status = SelectField('Smoking Status',
                                choices=[
                                    ('never smoked', 'Never Smoked'),
                                    ('formerly smoked', 'Formerly Smoked'),
                                    ('smokes', 'Smokes'),
                                    ('Unknown', 'Unknown')
                                ],
                                validators=[DataRequired()])
    
    stroke = SelectField('Stroke',
                        choices=[('0', 'No'), ('1', 'Yes')],
                        validators=[DataRequired()])
    
    # Validate the BMI field to allow 'N/A' or a valid as a float within a range from 10 to 100.
    def validate_bmi(self, bmi): # (Anthropic, 2025)
        if bmi.data and bmi.data.strip() and bmi.data != 'N/A':
            try:
                bmi_value = float(bmi.data)
                if bmi_value < 10 or bmi_value > 100:
                    raise ValidationError("BMI must be between 10 and 100.")
            except ValueError:
                raise ValidationError("BMI must be a valid number or 'N/A'.")
            
        """ Validate the BMI field to allow 'N/A' or a valid float.

        Args:
            bmi: WTForms field.

        Raises:
            ValidationError: If BMI is not valid.
        """

    def validate_patient_id(self, patient_id): # (Anthropic, 2025)
        if patient_id.data is not None:
            # Ensure it's a positive integer
            if patient_id.data < 1:
                raise ValidationError("Patient ID must be a positive number.")
            
        """ Validate that patient_id is a positive integer.

        Args:
            patient_id: WTForms field.

        Raises:
            ValidationError: If patient_id is not positive.
        """

# Form for searching patient records, includes both unencrypted and encrypted with searches using HMAC fields.
class SearchForm(FlaskForm): # (Anthropic, 2025)
    search_field = SelectField('Search By',
                              choices=[
                                  ('', 'All Records'),
                                  # Unencrypted fields, direct search.
                                  ('id', 'Patient ID'),
                                  ('gender', 'Gender'),
                                  ('age', 'Age'),
                                  ('ever_married', 'Ever Married (0=No, 1=Yes)'),
                                  ('work_type', 'Work Type'),
                                  ('Residence_type', 'Residence Type'),
                                  # Encrypted but searchable fields using HMAC hash search.
                                  ('stroke', 'Stroke (0=No, 1=Yes)'),
                                  ('hypertension', 'Hypertension (0=No, 1=Yes)'),
                                  ('heart_disease', 'Heart Disease (0=No, 1=Yes)'),
                                  ('smoking_status', 'Smoking Status')
                              ])
    
    search_value = StringField('Search Value')

# Form for changing user passwords.
class ChangePasswordForm(FlaskForm): # (Anthropic, 2025)   
    current_password = PasswordField('Current Password',
                                    validators=[
                                        DataRequired(message="Current password is required.")
                                    ])
    
    new_password = PasswordField('New Password',
                                validators=[
                                    DataRequired(message="New password is required."),
                                    Length(min=12, message="Password must be at least 12 characters.")
                                ])
    
    confirm_new_password = PasswordField('Confirm New Password',
                                        validators=[
                                            DataRequired(message="Please confirm your new password."),
                                            EqualTo('new_password', message="Passwords must match.")
                                        ])
    
    def validate_new_password(self, new_password): # (Anthropic, 2025)
        is_valid, error_message = validate_password_strength(new_password.data)
        if not is_valid:
            raise ValidationError(error_message or "Password does not meet security requirements.")
        
        """ Validate new password strength.

        Args:
            new_password: WTForms field.

        Raises:
            ValidationError: If password does not meet requirements.
        """

# Form for changing user email/username.
class ChangeEmailForm(FlaskForm): # (Anthropic, 2025)    
    new_email = StringField('New Email',
                           validators=[
                               DataRequired(message="New email is required."),
                               Email(message="Invalid email address.")
                           ])
    
    current_password = PasswordField('Current Password',
                                    validators=[
                                        DataRequired(message="Current password is required to change email.")
                                    ])
    
    # Check if new email is already in use.
    def validate_new_email(self, new_email): # (Anthropic, 2025)
        # Sanitize the input.
        clean_email = bleach.clean(new_email.data, tags=[], strip=True).lower()
        
        # Check if the email exists in the User table.
        user = User.query.filter_by(email=clean_email).first()
        if user:
            raise ValidationError('This email is already registered. Please use a different one.')
        
        # Check if the email exists as username in User table.
        user_by_username = User.query.filter_by(username=clean_email).first()
        if user_by_username:
            raise ValidationError('This email is already registered. Please use a different one.')
        new_email.data = clean_email
        
        """ Validate that new email is unique and sanitized.

        Args:
            new_email: WTForms field.

        Raises:
            ValidationError: If email is already registered.
        """

class DeleteAccountForm(FlaskForm): # (Anthropic, 2025)
    confirm_password = PasswordField('Enter your password to confirm deletion',
                                    validators=[
                                        DataRequired(message="Password is required to delete account.")
                                    ])
    
    confirm_text = StringField('Type "DELETE" to confirm',
                              validators=[
                                  DataRequired(message="Confirmation text is required.")
                              ])
    
    # Validate the confirmation text.
    def validate_confirm_text(self, confirm_text): # (Anthropic, 2025)
        if confirm_text.data.upper() != 'DELETE':
            raise ValidationError('You must type "DELETE" to confirm account deletion.')
        
        """ Form for deleting user account with confirmation.

        Args:
            confirm_text: WTForms field.

        Raises:
            ValidationError: If confirmation text is not 'DELETE'.
        """

# Form for admin users to add or change email.
class AdminEmailForm(FlaskForm): # (Anthropic, 2025)
    new_email = StringField('Email Address',
                           validators=[
                               DataRequired(message="Email is required."),
                               Email(message="Invalid email address.")
                           ])
    
    current_password = PasswordField('Current Password',
                                    validators=[
                                        DataRequired(message="Current password is required to change email.")
                                    ])
    
    # Check if new email is already in use.
    def validate_new_email(self, new_email): # (Anthropic, 2025)
        from app.admin_models import AdminUser
        # Sanitize the input.
        clean_email = bleach.clean(new_email.data, tags=[], strip=True).lower()
        
        # Check if the email exists in the AdminUser table.
        admin = AdminUser.query.filter_by(email=clean_email).first()
        if admin:
            raise ValidationError('This email is already registered. Please use a different one.')
        
        # Also check User table to avoid conflicts.
        user = User.query.filter_by(email=clean_email).first()
        if user:
            raise ValidationError('This email is already in use. Please use a different one.')
        
        new_email.data = clean_email
        
        """ Validate that new admin email is unique and sanitized.

        Args:
            new_email: WTForms field.

        Raises:
            ValidationError: If email is already registered.
        """

# Form for 2FA code verification.
class TwoFactorForm(FlaskForm): # (Anthropic, 2025)
    code = StringField('Verification Code',
                      validators=[
                          DataRequired(message="Verification code is required."),
                          Length(min=6, max=6, message="Code must be 6 digits.")
                      ])
    
    def validate_code(self, code): # (Anthropic, 2025)
        # Ensure only digits.
        if not code.data.isdigit():
            raise ValidationError("Code must contain only digits.")
        
        """ Validate that the 2FA code contains only digits.

        Args:
            code: WTForms field.

        Raises:
            ValidationError: If code contains non-digit characters.
        """

