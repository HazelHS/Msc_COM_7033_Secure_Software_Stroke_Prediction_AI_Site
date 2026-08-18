# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" SVM Model Integration Helper for CRUD Operations.

Provides functions to load the trained SVM model, preprocess patient data,
and generate real-time stroke risk predictions for the admin dashboard.
"""

import os
import pickle
import numpy as np
import warnings
import hmac
import hashlib
from flask import current_app

# Suppress sklearn feature name warnings
warnings.filterwarnings('ignore', message='X does not have valid feature names')

# Global cache for loaded model
_cached_svm_model = None
_model_metadata = None

def load_svm_model(): # (Anthropic, 2025)
    global _cached_svm_model, _model_metadata
    
    # Return cached model if available.
    if _cached_svm_model is not None:
        return _cached_svm_model, _model_metadata
    
    model_path = 'svm_stroke_model.pkl'
    
    if not os.path.exists(model_path):
        current_app.logger.warning(f"SVM model not found at {model_path}")
        return None, None
    
    try: # Enforce HMAC signature verification for model integrity to prevent loading tampered models from executing untrusted code.
        sig_path = f"{model_path}.sig"
        if not os.path.exists(sig_path):
            current_app.logger.error(f"SVM model signature missing: {sig_path}; refusing to load unsigned model")
            return None, None

        with open(model_path, 'rb') as f:
            data_bytes = f.read()
        with open(sig_path, 'r') as sf:
            expected_sig = sf.read().strip()

        secret = os.environ.get('SECRET_KEY', '')
        calc_sig = hmac.new(secret.encode('utf-8'), data_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc_sig, expected_sig):
            current_app.logger.error("SVM model signature mismatch; refusing to load model")
            return None, None

        # Signature verified; unpickle the byte payload.
        model_data = pickle.loads(data_bytes)  # nosec: B301
        
        _cached_svm_model = model_data.get('model')
        _model_metadata = {
            'best_params': model_data.get('best_params', {}),
            'accuracy': model_data.get('metrics', {}).get('after_balancing', {}).get('accuracy', 0),
            'precision': model_data.get('metrics', {}).get('after_balancing', {}).get('precision', 0),
            'recall': model_data.get('metrics', {}).get('after_balancing', {}).get('recall', 0),
            'f1_score': model_data.get('metrics', {}).get('after_balancing', {}).get('f1_score', 0)
        }
        
        current_app.logger.info(f"SVM model loaded successfully. Accuracy: {_model_metadata['accuracy']*100:.2f}%")
        return _cached_svm_model, _model_metadata
        
    except Exception as e:
        current_app.logger.error(f"Error loading SVM model: {e}")
        return None, None
    
    """ Load the trained SVM model from pickle file.
    
    Attempts to load a cached model first for performance. If not cached,
    loads from disk and extracts accuracy metrics from the training results.
    
    Returns:
        tuple: A tuple containing:
            - model (sklearn.svm.SVC or None): The trained SVM classifier,
              or None if model file not found.
            - metadata (dict or None): Dictionary with keys 'best_params',
              'accuracy', 'precision', 'recall', 'f1_score', or None if
              model file not found.
    
    Raises:
        No exceptions raised; errors are logged and (None, None) returned.
    """

def preprocess_patient_for_prediction(patient_record): # (Anthropic, 2025)
    try:
        # Extract features in correct order
        features = {}
        
        # Gender encoding: Male=1, Female=0, Other=2
        gender_map = {'Male': 1, 'Female': 0, 'Other': 2}
        features['gender'] = gender_map.get(patient_record.get('gender', 'Other'), 2)
        
        # Age (will be normalized)
        features['age'] = float(patient_record.get('age', 0))
        
        # Hypertension (0 or 1)
        features['hypertension'] = int(patient_record.get('hypertension', 0))
        
        # Heart disease (0 or 1)
        features['heart_disease'] = int(patient_record.get('heart_disease', 0))
        
        # Ever married: Yes=1, No=0
        married_map = {'Yes': 1, 'No': 0}
        features['ever_married'] = married_map.get(patient_record.get('ever_married', 'No'), 0)
        
        # Work type encoding (simplified mapping)
        work_type_map = {
            'Private': 0,
            'Self-employed': 1,
            'Govt_job': 2,
            'children': 3,
            'Never_worked': 4
        }
        features['work_type'] = work_type_map.get(patient_record.get('work_type', 'Private'), 0)
        
        # Residence type: Urban=1, Rural=0
        residence_map = {'Urban': 1, 'Rural': 0}
        features['Residence_type'] = residence_map.get(patient_record.get('Residence_type', 'Urban'), 1)
        
        # Avg glucose level (will be normalized)
        features['avg_glucose_level'] = float(patient_record.get('avg_glucose_level', 0))
        
        # BMI (will be normalized, handle 'N/A')
        bmi_value = patient_record.get('bmi', '28.0')
        if bmi_value == 'N/A' or bmi_value is None:
            features['bmi'] = 28.0  # Median value
        else:
            features['bmi'] = float(bmi_value)
        
        # Smoking status encoding
        smoking_map = {
            'never smoked': 0,
            'formerly smoked': 1,
            'smokes': 2,
            'Unknown': 3
        }
        features['smoking_status'] = smoking_map.get(patient_record.get('smoking_status', 'Unknown'), 3)
        
        # Create feature array in correct order
        feature_order = ['gender', 'age', 'hypertension', 'heart_disease', 'ever_married',
                        'work_type', 'Residence_type', 'avg_glucose_level', 'bmi', 'smoking_status']
        
        feature_array = np.array([features[key] for key in feature_order]).reshape(1, -1)
        
        # Normalize numeric features (age, avg_glucose_level, bmi)
        # Using approximate normalization based on training data statistics
        # Age: mean~42, std~22
        # Glucose: mean~104, std~43
        # BMI: mean~28.6, std~7.6
        
        normalized = feature_array.copy()
        normalized[0, 1] = (feature_array[0, 1] - 42.0) / 22.5  # age
        normalized[0, 7] = (feature_array[0, 7] - 104.5) / 43.1  # avg_glucose_level
        normalized[0, 8] = (feature_array[0, 8] - 28.6) / 7.6   # bmi
        
        return normalized
        
    except Exception as e:
        current_app.logger.error(f"Error preprocessing patient data: {e}")
        return None
    
    """ Preprocess a single patient record for SVM prediction.
    
    Transforms raw patient data into the normalized feature vector expected
    by the trained SVM model. Follows the same preprocessing pipeline used
    during model training (DataProcessing.py):
    - Encodes categorical features (gender, marital status, work type, etc.)
    - Normalizes continuous numeric features (age, glucose, BMI) using
      z-score normalization with training set statistics
    
    Args:
        patient_record (dict): Dictionary containing patient data with keys:
            'gender', 'age', 'hypertension', 'heart_disease', 'ever_married',
            'work_type', 'Residence_type', 'avg_glucose_level', 'bmi',
            'smoking_status'. Missing values will be substituted with defaults.
    
    Returns:
        numpy.ndarray: A 1x10 normalized feature array ready for model.predict(),
            or None if preprocessing fails. Features are ordered as: [gender, age,
            hypertension, heart_disease, ever_married, work_type, Residence_type,
            avg_glucose_level, bmi, smoking_status].
    
    Raises:
        No exceptions raised; errors are logged and None returned.
    """

def predict_stroke_risk(patient_record): # (Anthropic, 2025)
    model, metadata = load_svm_model()
    
    if model is None:
        return {
            'prediction': 'N/A',
            'risk_level': 'unknown',
            'confidence': 0,
            'error': 'Model not available'
        }
    
    try:
        # Preprocess the patient data
        features = preprocess_patient_for_prediction(patient_record)
        
        if features is None:
            return {
                'prediction': 'Error',
                'risk_level': 'unknown',
                'confidence': 0,
                'error': 'Preprocessing failed'
            }
        
        # Make prediction
        prediction = model.predict(features)[0]
        
        # Get probability if available
        try:
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(features)[0]
                confidence = float(probabilities[1])  # Probability of stroke
            elif hasattr(model, 'decision_function'):
                decision = model.decision_function(features)[0]
                # Convert decision function to probability-like score
                confidence = float(1 / (1 + np.exp(-decision)))
            else:
                confidence = 0.5
        except:
            confidence = 0.5
        
        # Determine risk level based on prediction and confidence
        if prediction == 1:
            if confidence > 0.8:
                risk_level = 'high'
            elif confidence > 0.6:
                risk_level = 'elevated'
            else:
                risk_level = 'moderate'
        else:
            if confidence < 0.2:
                risk_level = 'low'
            elif confidence < 0.4:
                risk_level = 'minimal'
            else:
                risk_level = 'low-moderate'
        
        return {
            'prediction': int(prediction),
            'risk_level': risk_level,
            'confidence': round(confidence * 100, 2),
            'error': None
        }
        
    except Exception as e:
        current_app.logger.error(f"Error predicting stroke risk: {e}")
        return {
            'prediction': 'Error',
            'risk_level': 'unknown',
            'confidence': 0,
            'error': str(e)
        }
    """ Predict stroke risk for a single patient record.
    
    Generates a binary stroke prediction (0=low risk, 1=high risk) with
    confidence score and risk level classification. Uses the trained SVM
    model's decision function or probability estimates if available.
    
    Args:
        patient_record (dict): Dictionary containing patient data. See
            preprocess_patient_for_prediction() for required keys.
    
    Returns:
        dict: Prediction results with keys:
            - prediction (int or str): 0 for low risk, 1 for high risk,
              'N/A' if model unavailable, 'Error' if preprocessing failed.
            - risk_level (str): One of 'high', 'elevated', 'moderate',
              'low-moderate', 'minimal', 'low', or 'unknown'.
            - confidence (float): Percentage confidence (0-100) in the
              prediction. For high-risk predictions, represents stroke
              probability. For low-risk, inverse is shown in UI.
            - error (str or None): Error message if prediction failed,
              None on success.
    
    Raises:
        No exceptions raised; errors are logged and returned in dict.
    """

def add_predictions_to_records(records, is_admin=False): # (Anthropic, 2025)
    if not is_admin:
        return records
    
    model, metadata = load_svm_model()
    
    if model is None:
        return records
    
    for record in records:
        prediction_result = predict_stroke_risk(record)
        record['ai_prediction'] = prediction_result
    
    return records

    """ Add AI predictions to a list of patient records.
    
    Batch processes patient records to add stroke risk predictions. Only
    executes for admin users to prevent unauthorized access to AI predictions.
    Modifies records in-place by adding an 'ai_prediction' key.
    
    Args:
        records (list): List of patient record dictionaries. Each record
            should contain patient data fields as defined in
            preprocess_patient_for_prediction().
        is_admin (bool): Whether the current user has admin privileges.
            Defaults to False. Predictions only generated if True.
    
    Returns:
        list: The same records list, with 'ai_prediction' field added to
            each record if is_admin=True and model available. Returns
            unmodified records if is_admin=False or model unavailable.
    
    Raises:
        No exceptions raised; records returned in original state on error.
    """

def get_model_metadata(): # (Anthropic, 2025)
    model, metadata = load_svm_model()
    return metadata

    """ Get metadata about the loaded SVM model.
    
    Retrieves performance metrics from the trained model without making
    predictions. Useful for displaying model accuracy on dashboards.
    
    Returns:
        dict or None: Model metadata dictionary with keys 'best_params',
            'accuracy', 'precision', 'recall', 'f1_score' if model loaded,
            None if model not available.
    
    Raises:
        No exceptions raised.
    """

def calculate_ai_risk_statistics(records): # (Anthropic, 2025)
    model, metadata = load_svm_model()
    
    if model is None:
        return None
    
    try:
        high_risk = 0
        moderate_risk = 0
        low_risk = 0
        
        for record in records:
            prediction = predict_stroke_risk(record)
            
            if prediction['prediction'] == 1:
                if prediction['confidence'] > 80:
                    high_risk += 1
                else:
                    moderate_risk += 1
            else:
                low_risk += 1
        
        total = len(records)
        
        return {
            'high_risk_count': high_risk,
            'moderate_risk_count': moderate_risk,
            'low_risk_count': low_risk,
            'high_risk_percentage': round((high_risk / total) * 100, 1) if total > 0 else 0,
            'moderate_risk_percentage': round((moderate_risk / total) * 100, 1) if total > 0 else 0,
            'low_risk_percentage': round((low_risk / total) * 100, 1) if total > 0 else 0
        }
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error calculating AI risk statistics: {e}")
        return None
    
    """ Calculate AI prediction statistics for all records.
    
    Aggregates stroke risk predictions across the entire patient database
    to generate dashboard statistics. Categorizes patients into high,
    moderate, and low risk groups based on model predictions.
    
    Args:
        records (list): List of patient record dictionaries to analyze.
    
    Returns:
        dict or None: Statistics dictionary with keys:
            - high_risk_count (int): Number of high-risk predictions
            - moderate_risk_count (int): Number of moderate-risk predictions
            - low_risk_count (int): Number of low-risk predictions
            - high_risk_percentage (float): Percentage of high-risk patients
            - moderate_risk_percentage (float): Percentage of moderate-risk
            - low_risk_percentage (float): Percentage of low-risk patients
            Returns None if model unavailable or calculation fails.
    
    Raises:
        No exceptions raised; errors logged and None returned.
    """
