# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" CRUD Operations blueprint module.

Handles create, read, update, and delete operations for healthcare data. 
Uses the mongoDB database for patient records storage.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app import mongo_db, limiter
from app.forms import PatientRecordForm, SearchForm
from app.security import (log_audit, sanitize_input, validate_patient_data, 
                          encrypt_patient_record, decrypt_patient_record, 
                          decrypt_patient_records_batch, generate_search_hash,
                          decrypt_field, EncryptionError, DecryptionError,
                          SEARCHABLE_ENCRYPTED_FIELDS)
from app.SVMcrudHelper import add_predictions_to_records, get_model_metadata, calculate_ai_risk_statistics
from bson.objectid import ObjectId
from bson.errors import InvalidId
import csv
import os

crud_bp = Blueprint('crud', __name__)

def get_patient_collection(): # (Anthropic, 2025)
    if mongo_db is None:
        return None
    return mongo_db.patient_records

    """ Get MongoDB database patient records collection.

    Returns:
        MongoDB collection object or None if not connected.
    """

@crud_bp.route('/dashboard')
@login_required

# Main dashboard displaying patient records, which is only accessible to admin users. Users are redirected to their patient record view.
def dashboard(): # (Anthropic, 2025)
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        return redirect(url_for('crud.user_dashboard'))
    
    collection = get_patient_collection()
    
    if collection is None:
        flash('MongoDB database is not connected. Please ensure MongoDB is running before accessing patient records.', 'danger')
        flash('To start MongoDB: cd mongodb_portable && .\\start_mongodb.ps1', 'info')
        return render_template('crud/dashboard.html', records=[], total=0, page=1, per_page=20, stats={})
    
    # Pagination parameters.
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Search functionality.
    search_field = request.args.get('search_field', '')
    search_value = request.args.get('search_value', '')
    
    # Build query.
    query = {}
    if search_field and search_value:
        search_value = sanitize_input(search_value)
        
        # Handle "ever_married" field, and convert 0/1 to Yes/No and make it case-insensitive.
        if search_field == 'ever_married' and search_value:
            # Accept 0/1 or Yes/No.
            search_value_lower = search_value.strip().lower()
            if search_value_lower in ['0', 'no']:
                query[search_field] = 'No'
            elif search_value_lower in ['1', 'yes']:
                query[search_field] = 'Yes'
            else:
                flash('Ever Married must be 0 (No) or 1 (Yes).', 'warning')
        
        # Unencrypted string fields, case-insensitive search.
        elif search_field in ['gender', 'work_type', 'Residence_type']:
            query[search_field] = {'$regex': f'^{search_value}$', '$options': 'i'}

        # Patient ID search using HMAC hash, a deterministic encryption method for searches. This means that IDs are not stored in plaintext, which doesn't sacrifice security; however, it is less secure than full encryption.
        elif search_field in ['age', 'id'] and search_value:
            try:
                search_hash = generate_search_hash(str(search_value), 'id')
                query['id_search'] = search_hash
            except EncryptionError as e:
                flash(f'Search unavailable: {str(e)}', 'danger')
            except ValueError:
                flash('Invalid Patient ID value.', 'warning')
        
        # Unencrypted numeric fields.
        elif search_field == 'age' and search_value:
            try:
                query[search_field] = float(search_value)
            except ValueError:
                flash('Invalid age value.', 'warning')
                
        # Encrypted searchable fields using HMAC hash.
        elif search_field in SEARCHABLE_ENCRYPTED_FIELDS:
            try:
                search_hash = generate_search_hash(search_value, search_field)
                search_hash_field = f"{search_field}_search"
                query[search_hash_field] = search_hash
            except EncryptionError as e:
                flash(f'Search unavailable: {str(e)}', 'danger')
            except ValueError:
                flash('Invalid search value for numeric field.', 'warning')
    
    # Get total count.
    total = collection.count_documents(query)
    
    # Get paginated records.
    skip = (page - 1) * per_page
    records = list(collection.find(query).skip(skip).limit(per_page))
    
    # Decrypt sensitive fields.
    records = decrypt_patient_records_batch(records)
    
    # Add AI predictions for admin users
    is_admin = hasattr(current_user, 'is_admin') and current_user.is_admin
    records = add_predictions_to_records(records, is_admin=is_admin)
    
    # Convert ObjectId to string for template.
    for record in records:
        record['_id'] = str(record['_id'])
    
    # Calculate pagination.
    total_pages = (total + per_page - 1) // per_page
    
    # Calculate statistics for visualizations.
    stats = calculate_dashboard_stats(collection)
    
    # Log dashboard access.
    log_audit(
        user_id=current_user.id,
        action='READ',
        table_name='patient_records',
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        details=f'Dashboard access, page {page}'
    )
    
    # Get model metadata for dashboard
    model_metadata = get_model_metadata()
    
    search_form = SearchForm()
    
    return render_template('crud/dashboard.html', 
                         records=records, 
                         total=total,
                         page=page,
                         per_page=per_page,
                         total_pages=total_pages,
                         search_form=search_form,
                         search_field=search_field,
                         search_value=search_value,
                         stats=stats,
                         model_metadata=model_metadata)
    
    """ Main dashboard displaying patient records for admin users.

    Returns:
        Rendered dashboard template with records and statistics.
    """

def calculate_dashboard_stats(collection): # (Anthropic, 2025)
    try:
        # Get all records for analysis.
        all_records = list(collection.find({}))
        decrypted_records = decrypt_patient_records_batch(all_records)
        
        total_records = len(decrypted_records)
        
        if total_records == 0:
            return {}
        
        # Initialize counters.
        stroke_count = 0
        hypertension_count = 0
        heart_disease_count = 0
        gender_counts = {'Male': 0, 'Female': 0, 'Other': 0}
        smoking_counts = {'never smoked': 0, 'formerly smoked': 0, 'smokes': 0, 'Unknown': 0}
        age_groups = {'0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81+': 0}
        work_type_counts = {}
        
        for record in decrypted_records:
            # Stroke count.
            if record.get('stroke') == 1:
                stroke_count += 1
            
            # Hypertension count.
            if record.get('hypertension') == 1:
                hypertension_count += 1
            
            # Heart disease count.
            if record.get('heart_disease') == 1:
                heart_disease_count += 1
            
            # Gender distribution.
            gender = record.get('gender', 'Other')
            if gender in gender_counts:
                gender_counts[gender] += 1
            
            # Smoking status distribution.
            smoking = record.get('smoking_status', 'Unknown')
            if smoking in smoking_counts:
                smoking_counts[smoking] += 1
            
            # Age groups.
            age = record.get('age', 0)
            if age <= 20:
                age_groups['0-20'] += 1
            elif age <= 40:
                age_groups['21-40'] += 1
            elif age <= 60:
                age_groups['41-60'] += 1
            elif age <= 80:
                age_groups['61-80'] += 1
            else:
                age_groups['81+'] += 1
            
            # Work type distribution.
            work_type = record.get('work_type', 'Unknown')
            work_type_counts[work_type] = work_type_counts.get(work_type, 0) + 1
        
        # Calculate percentages.
        stroke_percentage = (stroke_count / total_records) * 100
        hypertension_percentage = (hypertension_count / total_records) * 100
        heart_disease_percentage = (heart_disease_count / total_records) * 100
        
        # Calculate AI prediction statistics
        ai_predictions = calculate_ai_risk_statistics(decrypted_records)
        
        return {
            'total_records': total_records,
            'stroke_count': stroke_count,
            'stroke_percentage': round(stroke_percentage, 1),
            'no_stroke_count': total_records - stroke_count,
            'no_stroke_percentage': round(100 - stroke_percentage, 1),
            'hypertension_count': hypertension_count,
            'hypertension_percentage': round(hypertension_percentage, 1),
            'heart_disease_count': heart_disease_count,
            'heart_disease_percentage': round(heart_disease_percentage, 1),
            'gender_counts': gender_counts,
            'smoking_counts': smoking_counts,
            'age_groups': age_groups,
            'work_type_counts': work_type_counts,
            'ai_predictions': ai_predictions
        }
    except Exception as e:
        current_app.logger.error(f"Error calculating dashboard stats: {e}")
        return {}
    
    """ Calculate aggregated statistics for dashboard visualizations.

    Args:
        collection: MongoDB collection of patient records.

    Returns:
        Dictionary of aggregated statistics.
    """

@crud_bp.route('/user-dashboard')
@login_required

def user_dashboard(): # (Anthropic, 2025)
    # Check if user is not admin.
    if hasattr(current_user, 'is_admin') and current_user.is_admin:
        return redirect(url_for('crud.dashboard'))
    
    # Get user's patient_id.
    user_id_str = str(current_user.id)
    if user_id_str.startswith('user_'):
        user_id = int(user_id_str.split('_')[1])
    else:
        user_id = current_user.id
    
    from app.models import User
    user = User.query.get(user_id)
    
    if not user or not user.patient_id:
        flash('No patient record associated with your account.', 'warning')
        return render_template('crud/user_dashboard.html', record=None)
    
    collection = get_patient_collection()

    # Error checking for the mongoDB database, with directions for troubleshooting.
    if collection is None:
        flash('MongoDB database is not connected. Please ensure MongoDB is running to view patient records.', 'danger')
        flash('To start MongoDB: cd mongodb_portable && .\\start_mongodb.ps1', 'info')
        return render_template('crud/user_dashboard.html', record=None)
    
    try:
        # Find patient record by patient_id using search hash.
        from app.security import generate_search_hash
        search_hash = generate_search_hash(str(user.patient_id), 'id')
        record = collection.find_one({'id_search': search_hash})
        
        if not record:
            flash('Your patient record could not be found.', 'warning')
            return render_template('crud/user_dashboard.html', record=None)
        
        # Decrypt sensitive fields.
        record = decrypt_patient_record(record)
        
        # Convert ObjectId to string.
        record['_id'] = str(record['_id'])
        
        # Log dashboard access.
        log_audit(
            user_id=user_id,
            action='READ',
            table_name='patient_records',
            record_id=str(record.get('id')),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            details=f'User dashboard access for patient_id {user.patient_id}'
        )
        
        return render_template('crud/user_dashboard.html', record=record)
        
    except Exception as e:
        current_app.logger.error(f"Error loading user dashboard: {e}")
        flash('Error loading your patient record.', 'danger')
        return render_template('crud/user_dashboard.html', record=None)
    
    """ User dashboard for users, displays only their own patient records.

    Returns:
        Rendered user dashboard template with user's record.
    """

@crud_bp.route('/patient/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("20 per hour")

def create_patient(): # (Anthropic, 2025)
    form = PatientRecordForm()
    
    if form.validate_on_submit():
        collection = get_patient_collection()
        
        if collection is None:
            flash('MongoDB database is not connected. Cannot create patient records without database connection.', 'danger')
            flash('To start MongoDB: cd mongodb_portable && .\\start_mongodb.ps1', 'info')
            return render_template('crud/create.html', form=form)
        
        # Handles whether or not Patient ID should be auto-generated or specified.
        patient_id = form.patient_id.data
        
        if patient_id:
            # Check if specifiied ID is unique.
            try:
                # Generate search hash to check for existing ID.
                existing_hash = generate_search_hash(str(patient_id), 'id')
                existing_record = collection.find_one({'id_search': existing_hash})
                
                if existing_record:
                    flash(f'Patient ID {patient_id} is already in use. Please choose a different ID or leave blank to auto-generate.', 'danger')
                    return render_template('crud/create.html', form=form)
            except EncryptionError as e:
                flash(f'Security Error: {str(e)}. Cannot validate patient ID.', 'danger')
                return render_template('crud/create.html', form=form)
        else:
            # Auto-generate patient ID and find the highest existing ID and increment it.
            try:
                all_records = list(collection.find({}, {'id': 1, 'id_search': 1}))
                
                if all_records:
                    # Decrypt IDs to find the maximum.
                    max_id = 0
                    for record in all_records:
                        if 'id' in record:
                            try:
                                decrypted_id = decrypt_field(record['id'])
                                if decrypted_id is not None:
                                    numeric_id = int(decrypted_id)
                                    if numeric_id > max_id:
                                        max_id = numeric_id
                            except (DecryptionError, ValueError, TypeError):
                                continue
                    patient_id = max_id + 1
                else:
                    patient_id = 1
            except Exception as e:
                # Fallback to timestamp-based ID.
                from datetime import datetime
                patient_id = int(datetime.utcnow().timestamp())
                current_app.logger.warning(f"Using timestamp-based ID due to error: {e}")
        
        # Prepare the patient data.
        patient_data = {
            'id': patient_id,
            'gender': form.gender.data,
            'age': form.age.data,
            'hypertension': int(form.hypertension.data),
            'heart_disease': int(form.heart_disease.data),
            'ever_married': form.ever_married.data,
            'work_type': form.work_type.data,
            'Residence_type': form.residence_type.data,
            'avg_glucose_level': form.avg_glucose_level.data,
            'bmi': form.bmi.data if form.bmi.data else 'N/A',
            'smoking_status': form.smoking_status.data,
            'stroke': int(form.stroke.data)
        }
        
        # Validate the data.
        is_valid, errors = validate_patient_data(patient_data)
        if not is_valid:
            for field, error in errors.items():
                flash(f'{field}: {error}', 'danger')
            return render_template('crud/create.html', form=form)
        
        try:
            # Encrypt sensitive fields before storage.
            encrypted_data = encrypt_patient_record(patient_data)
            
            # Insert into MongoDB with encrypted sensitive fields
            result = collection.insert_one(encrypted_data)
            
            # Log creation.
            log_audit(
                user_id=current_user.id,
                action='CREATE',
                table_name='patient_records',
                record_id=str(result.inserted_id),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                details=f'Created patient record with ID: {patient_id}'
            )
            
            flash(f'Patient record created successfully! Patient ID: {patient_id}', 'success')
            return redirect(url_for('crud.dashboard'))
        
        except EncryptionError as e:
            # Refuse to store unencrypted data, as part of fail-secure design.
            flash(f'Security Error: {str(e)}. Record not saved.', 'danger')
            current_app.logger.error(f"Encryption failed during create: {e}")
            return render_template('crud/create.html', form=form)
            
        except Exception as e:
            flash('An error occurred while creating the record. Please try again.', 'danger')
            current_app.logger.error(f"Create patient error: {e}")
            return render_template('crud/create.html', form=form)
    
    return render_template('crud/create.html', form=form)

    """ Creation of new patient records, admin only privilege.

    Returns:
        Redirect or rendered template for patient creation.
    """


@crud_bp.route('/patient/<patient_id>')
@login_required

def view_patient(patient_id): # (Anthropic, 2025)
    collection = get_patient_collection()
    
    if collection is None:
        flash('MongoDB database is not connected. Cannot view patient records without database connection.', 'danger')
        flash('To start MongoDB: cd mongodb_portable && .\\start_mongodb.ps1', 'info')
        return redirect(url_for('crud.dashboard'))
    
    try:
        record = collection.find_one({'_id': ObjectId(patient_id)})
        
        if record is None:
            flash('Patient record not found.', 'warning')
            return redirect(url_for('crud.dashboard'))
        
        # Decrypt sensitive fields.
        record = decrypt_patient_record(record)
        
        # Convert ObjectId to string
        record['_id'] = str(record['_id'])
        
        # Log record viewing.
        log_audit(
            user_id=current_user.id,
            action='READ',
            table_name='patient_records',
            record_id=patient_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return render_template('crud/view.html', record=record)
        
    except InvalidId:
        flash('Invalid patient ID.', 'danger')
        return redirect(url_for('crud.dashboard'))
    
    """ View individual patient records.

    Args:
        patient_id: MongoDB ObjectId string.

    Returns:
        Rendered template for viewing a patient record or redirect.
    """

@crud_bp.route('/patient/<patient_id>/edit', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per hour")

def edit_patient(patient_id):
    collection = get_patient_collection()
    
    if collection is None:
        flash('MongoDB database is not connected. Cannot edit patient records without database connection.', 'danger')
        flash('To start MongoDB: cd mongodb_portable && .\\start_mongodb.ps1', 'info')
        return redirect(url_for('crud.dashboard'))
    
    try:
        record = collection.find_one({'_id': ObjectId(patient_id)})
        
        if record is None:
            flash('Patient record not found.', 'warning')
            return redirect(url_for('crud.dashboard'))
        
        # Decrypt record for form display.
        decrypted_record = decrypt_patient_record(record)
        
        form = PatientRecordForm()
        
        if form.validate_on_submit():
            # Update the patient data.
            updated_data = {
                'gender': form.gender.data,
                'age': form.age.data,
                'hypertension': int(form.hypertension.data),
                'heart_disease': int(form.heart_disease.data),
                'ever_married': form.ever_married.data,
                'work_type': form.work_type.data,
                'Residence_type': form.residence_type.data,
                'avg_glucose_level': form.avg_glucose_level.data,
                'bmi': form.bmi.data if form.bmi.data else 'N/A',
                'smoking_status': form.smoking_status.data,
                'stroke': int(form.stroke.data)
            }
            
            # Validate the data.
            is_valid, errors = validate_patient_data(updated_data)
            if not is_valid:
                for field, error in errors.items():
                    flash(f'{field}: {error}', 'danger')
                return render_template('crud/edit.html', form=form, patient_id=patient_id)
            
            try:
                # Encrypt sensitive fields before storage.
                encrypted_data = encrypt_patient_record(updated_data)
                
                collection.update_one(
                    {'_id': ObjectId(patient_id)},
                    {'$set': encrypted_data}
                )
                
                # Log the update.
                log_audit(
                    user_id=current_user.id,
                    action='UPDATE',
                    table_name='patient_records',
                    record_id=patient_id,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                flash('Patient record updated successfully!', 'success')
                return redirect(url_for('crud.view_patient', patient_id=patient_id))
            
            except EncryptionError as e:
                # Refuse to store the unencrypted data, as part of fail-secure design.
                flash(f'Security Error: {str(e)}. Record not updated.', 'danger')
                current_app.logger.error(f"Encryption failed during update: {e}")

            except Exception as e:
                flash('An error occurred while updating the record. Please try again.', 'danger')
                current_app.logger.error(f"Update patient error: {e}")
        
        elif request.method == 'GET':
            # Pre-populate the form with existing decrypted data.
            form.gender.data = decrypted_record.get('gender')
            form.age.data = decrypted_record.get('age')
            form.hypertension.data = str(decrypted_record.get('hypertension', 0))
            form.heart_disease.data = str(decrypted_record.get('heart_disease', 0))
            form.ever_married.data = decrypted_record.get('ever_married')
            form.work_type.data = decrypted_record.get('work_type')
            form.residence_type.data = decrypted_record.get('Residence_type')
            form.avg_glucose_level.data = decrypted_record.get('avg_glucose_level')
            form.bmi.data = decrypted_record.get('bmi')
            form.smoking_status.data = decrypted_record.get('smoking_status')
            form.stroke.data = str(decrypted_record.get('stroke', 0))
        
        return render_template('crud/edit.html', form=form, patient_id=patient_id, record=decrypted_record)
        
    except InvalidId:
        flash('Invalid patient ID.', 'danger')
        return redirect(url_for('crud.dashboard'))
    
    """ Edit existing patient records.

    Args:
        patient_id: MongoDB ObjectId string.

    Returns:
        Rendered template for editing a patient record or redirect.
    """

@crud_bp.route('/patient/<patient_id>/delete', methods=['POST'])
@login_required
@limiter.limit("10 per hour")

def delete_patient(patient_id): # (Anthropic, 2025)

    collection = get_patient_collection()
    
    if collection is None:
        flash('MongoDB database is not connected. Cannot delete patient records without database connection.', 'danger')
        flash('To start MongoDB: cd mongodb_portable && .\\start_mongodb.ps1', 'info')
        return redirect(url_for('crud.dashboard'))
    
    try:
        result = collection.delete_one({'_id': ObjectId(patient_id)})
        
        if result.deleted_count == 1:
            # Log deletion
            log_audit(
                user_id=current_user.id,
                action='DELETE',
                table_name='patient_records',
                record_id=patient_id,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
            
            flash('Patient record deleted successfully.', 'success')
        else:
            flash('Patient record not found.', 'warning')
        
    except InvalidId:
        flash('Invalid patient ID.', 'danger')
    except Exception as e:
        flash('An error occurred while deleting the record. Please try again.', 'danger')
    
    return redirect(url_for('crud.dashboard'))

    """ Deletion of patient records.

    Args:
        patient_id: MongoDB ObjectId string.

    Returns:
        Redirect to dashboard after deletion.
    """

