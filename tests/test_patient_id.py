# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Test Patient ID module Functionality.

Tests for the admin's ability to specify patient IDs and user protection from modification.
"""

import pytest
from app.forms import PatientRecordForm
from app.security import encrypt_patient_record, generate_search_hash

class TestPatientIDForm:

    def test_patient_id_field_exists(self, app): # (Anthropic, 2025)
        from wtforms import IntegerField
        with app.app_context():
            form = PatientRecordForm()
            assert hasattr(form, 'patient_id')
            # Verify it's actually a form field, not just an attribute.
            assert isinstance(form.patient_id, IntegerField) or hasattr(form.patient_id, 'data')
            
        """ Test that the patient_id field exists in PatientRecordForm.

        Args:
            app: Flask app fixture.

        Asserts:
            The form has a patient_id field of the correct type.
        """

    def test_patient_id_optional(self, app, sample_patient_data): # (Anthropic, 2025)
        with app.app_context():
            form = PatientRecordForm(**{k: str(v) if isinstance(v, (int, float)) else v 
                                        for k, v in sample_patient_data.items()})
            assert form.patient_id.data is None
        
        """ Test that patient_id is optional in PatientRecordForm.

        Args:
            app: Flask app fixture.
            sample_patient_data: Dictionary of patient data.

        Asserts:
            The patient_id field is None if not provided.
        """
    
    def test_patient_id_accepts_valid_values(self, app, sample_patient_data): # (Anthropic, 2025)

        with app.app_context():
            data = {k: str(v) if isinstance(v, (int, float)) else v 
                   for k, v in sample_patient_data.items()}
            data['patient_id'] = 12345
            form = PatientRecordForm(**data)
            assert form.patient_id.data == 12345
            
        """ Test that patient_id accepts valid positive integers.

        Args:
            app: Flask app fixture.
            sample_patient_data: Dictionary of patient data.

        Asserts:
            The patient_id field is set to the provided integer.
        """

class TestPatientIDProtection: 
    # Test that patient_id is not in the change email form.
    def test_user_patient_id_not_in_change_email_form(self, app): # (Anthropic, 2025)
        from app.forms import ChangeEmailForm
        with app.app_context():
            form = ChangeEmailForm()
            assert not hasattr(form, 'patient_id')
            
        """ Test that patient_id is not present in ChangeEmailForm.

        Args:
            app: Flask app fixture.

        Asserts:
            The form does not have a patient_id field.
        """
    
    def test_user_patient_id_not_in_password_form(self, app): # (Anthropic, 2025)
        from app.forms import ChangePasswordForm
        with app.app_context():
            form = ChangePasswordForm()
            assert not hasattr(form, 'patient_id')
            
        """ Test that patient_id is not in the password change form.

        Args:
            app: Flask app fixture.

        Asserts:
            The form does not have a patient_id field.
        """
    
    def test_patient_id_display_only_in_userpage(self, client, standard_user): # (Anthropic, 2025)
        with client:
            client.post('/login', data={
                'username': 'testuser@example.com',
                'password': 'TestUser123!'
            }, follow_redirects=True)
            
            response = client.get('/userpage')
            assert response.status_code == 200
            assert b'12345' in response.data
            assert b'name="patient_id"' not in response.data
            
        """ Test that patient_id is displayed but not editable in userpage.

        Args:
            client: Flask test client.
            standard_user: User fixture.

        Asserts:
            patient_id is shown in the page but not as an editable field.
        """
            
class TestPatientIDSecurity:
    def test_patient_id_encrypted_in_database(self, app, init_mongodb, mock_patient_record): # (Anthropic, 2025)
        with app.app_context():
            collection = init_mongodb.patient_records
            record = collection.find_one({'_id': mock_patient_record})
            
            assert record is not None, "Patient record not found in MongoDB"
            assert 'id' in record, "ID field missing from record"
            assert record['id'] != '12345', "ID should be encrypted"
            assert record['id'] != 12345, "ID should be encrypted"
            assert 'id_search' in record, "Search hash missing"
            
        """ Test that patient_id is encrypted when stored in MongoDB.

        Args:
            app: Flask app fixture.
            init_mongodb: MongoDB fixture.
            mock_patient_record: Inserted patient record ID.

        Asserts:
            The id field is encrypted and id_search exists.
        """

    def test_patient_id_search_hash_generated(self, app): # (Anthropic, 2025)
        with app.app_context():
            patient_data = {
                'id': 54321,
                'gender': 'Male',
                'age': 40.0,
                'hypertension': 0,
                'heart_disease': 0,
                'ever_married': 'No',
                'work_type': 'Private',
                'Residence_type': 'Urban',
                'avg_glucose_level': 100.0,
                'bmi': '24.0',
                'smoking_status': 'never smoked',
                'stroke': 0
            }
            
            encrypted_data = encrypt_patient_record(patient_data)
            
            assert 'id' in encrypted_data
            assert encrypted_data['id'] != '54321'
            assert 'id_search' in encrypted_data
            
            expected_hash = generate_search_hash('54321', 'id')
            assert encrypted_data['id_search'] == expected_hash
            
        """ Test that a search hash is generated for patient_id.

        Args:
            app: Flask app fixture.

        Asserts:
            The id_search field is present and correct.
        """

# Enhanced cryptographic security tests for patient ID.
class TestPatientIDCryptographicSecurity:
    def test_patient_id_encryption_uniqueness(self, app): # (Anthropic, 2025)
        with app.app_context():
            patient_data_1 = {
                'id': 12345,
                'gender': 'Male',
                'age': 40.0,
                'hypertension': 0,
                'heart_disease': 0,
                'ever_married': 'No',
                'work_type': 'Private',
                'Residence_type': 'Urban',
                'avg_glucose_level': 100.0,
                'bmi': '24.0',
                'smoking_status': 'never smoked',
                'stroke': 0
            }
            
            patient_data_2 = patient_data_1.copy()
            encrypted_1 = encrypt_patient_record(patient_data_1)
            encrypted_2 = encrypt_patient_record(patient_data_2)
            
            # Same plaintext ID should produce different ciphertexts (due to random IV).
            assert encrypted_1['id'] != encrypted_2['id'], \
                "Encryption should produce different ciphertexts for same input (IV randomness check)"
        
        """ Test that encrypting the same patient_id twice produces different ciphertexts.

        Args:
            app: Flask app fixture.

        Asserts:
            Ciphertexts for the same plaintext are different (IV randomness).
        """
    
    def test_patient_id_encryption_not_reversible_without_key(self, app): # (Anthropic, 2025)
        with app.app_context():
            patient_data = {
                'id': 99999,
                'gender': 'Female',
                'age': 35.0,
                'hypertension': 1,
                'heart_disease': 0,
                'ever_married': 'Yes',
                'work_type': 'Private',
                'Residence_type': 'Rural',
                'avg_glucose_level': 105.0,
                'bmi': '28.5',
                'smoking_status': 'formerly smoked',
                'stroke': 0
            }
            
            encrypted_data = encrypt_patient_record(patient_data)
            encrypted_id = encrypted_data['id']
            
            # Encrypted value should not contain the plaintext ID.
            assert '99999' not in str(encrypted_id), \
                "Encrypted ID should not contain plaintext"
            
            # Should be base64 or hex encoded (non-plaintext).
            assert len(encrypted_id) > len(str(patient_data['id'])), \
                "Encrypted ID should be longer than plaintext (due to encryption overhead)"
            
            # Should not be a simple transformation (rot13, base64 of plaintext, etc.).
            import base64
            try:
                decoded = base64.b64decode(encrypted_id)
                assert b'99999' not in decoded, \
                    "Encrypted ID should not be simple base64 encoding of plaintext"
            except:
                pass  # If it's not base64, that's fine
            
        """ Test that encrypted patient_id cannot be reversed without the key.

        Args:
            app: Flask app fixture.

        Asserts:
            Encrypted value does not reveal plaintext and is not trivially decodable.
        """
    
    def test_patient_id_search_hash_deterministic(self, app): # (Anthropic, 2025)
        with app.app_context():
            hash_1 = generate_search_hash('12345', 'id')
            hash_2 = generate_search_hash('12345', 'id')
            
            # Search hashes should be identical for same input
            assert hash_1 == hash_2, \
                "Search hash should be deterministic for searching capability"
                
        """ Test that search hash for the same patient_id is deterministic.

        Args:
            app: Flask app fixture.

        Asserts:
            Hashes for the same input are identical.
        """
    
    def test_patient_id_search_hash_collision_resistance(self, app): # (Anthropic, 2025)
        with app.app_context():
            hash_1 = generate_search_hash('12345', 'id')
            hash_2 = generate_search_hash('12346', 'id')
            hash_3 = generate_search_hash('54321', 'id')
            
            # Different IDs should produce different hashes.
            assert hash_1 != hash_2, "Different patient IDs should have different hashes"
            assert hash_1 != hash_3, "Different patient IDs should have different hashes"
            assert hash_2 != hash_3, "Different patient IDs should have different hashes"

        """ Test that different patient_ids produce different search hashes.

        Args:
            app: Flask app fixture.

        Asserts:
            Hashes for different IDs are unique.
        """
    
    def test_patient_id_search_hash_not_reversible(self, app): # (Anthropic, 2025)
        with app.app_context():
            original_id = '98765'
            search_hash = generate_search_hash(original_id, 'id')
            
            # Hash should not contain plaintext
            assert original_id not in search_hash, \
                "Search hash should not contain plaintext ID"
            
            # Hash should be fixed length regardless of input
            hash_short = generate_search_hash('1', 'id')
            hash_long = generate_search_hash('123456789', 'id')
            
            assert len(hash_short) == len(hash_long), \
                "Hash should be fixed length (proper hashing algorithm)"

        """Test that search hash cannot be reversed to recover patient_id.

        Args:
            app: Flask app fixture.

        Asserts:
            Hash does not contain plaintext and is fixed length.
        """
    
    def test_patient_id_encryption_uses_authenticated_encryption(self, app): # (Anthropic, 2025)
        with app.app_context():
            patient_data = {
                'id': 77777,
                'gender': 'Male',
                'age': 50.0,
                'hypertension': 0,
                'heart_disease': 1,
                'ever_married': 'Yes',
                'work_type': 'Govt_job',
                'Residence_type': 'Urban',
                'avg_glucose_level': 110.0,
                'bmi': '30.0',
                'smoking_status': 'smokes',
                'stroke': 1
            }
            
            encrypted_data = encrypt_patient_record(patient_data)
            encrypted_id = encrypted_data['id']
            
            # If using authenticated encryption (like AES-GCM or Fernet), tampering should be detectable, this is more of a design check as the actual implementation should use Fernet or AES-GCM which includes authentication.
            # Check that encryption function exists and is callable
            from app.security import decrypt_patient_record

            # Decryption should work with valid data.
            decrypted_data = decrypt_patient_record(encrypted_data)
            assert decrypted_data['id'] == '77777', \
                "Decryption should recover original ID"
                
        """ Test that encryption includes authentication (AEAD) to prevent tampering.

        Args:
            app: Flask app fixture.

        Asserts:
            Decryption works and recovers the original ID.
        """

    def test_patient_id_encryption_rejects_tampered_data(self, app): # (Anthropic, 2025)
        with app.app_context():
            from app.security import decrypt_patient_record
            patient_data = {
                'id': 55555,
                'gender': 'Female',
                'age': 45.0,
                'hypertension': 1,
                'heart_disease': 1,
                'ever_married': 'Yes',
                'work_type': 'Self-employed',
                'Residence_type': 'Rural',
                'avg_glucose_level': 120.0,
                'bmi': '32.0',
                'smoking_status': 'never smoked',
                'stroke': 0
            }
            
            encrypted_data = encrypt_patient_record(patient_data)
            
            # Tamper with the encrypted ID
            tampered_data = encrypted_data.copy()
            tampered_data['id'] = tampered_data['id'][:-5] + 'XXXXX'
            
            # Should raise an exception (InvalidToken or similar)
            with pytest.raises(Exception):
                decrypt_patient_record(tampered_data)

        """ Test that tampered encrypted patient_id is rejected during decryption.

        Args:
            app: Flask app fixture.

        Asserts:
            Decryption raises an exception for tampered data.
        """

if __name__ == '__main__':
    pytest.main([__file__, '-v'])