# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Data Processing module for stroke prediction model.

Handles data collection from MongoDB, decryption, preprocessing, and feature engineering.
"""

import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from flask import current_app
import warnings
warnings.filterwarnings('ignore')

class StrokeDataProcessor:  # (Anthropic, 2025)
    
    """ Data processor for stroke prediction dataset with encryption handling.
    
    Manages the complete data pipeline from encrypted MongoDB storage through
    preprocessing and feature engineering. Handles decryption, missing values,
    categorical encoding, and feature normalization.
    
    Attributes:
        mongodb_uri (str): MongoDB connection string
        db_name (str): Database name
        client (MongoClient or None): Active MongoDB connection
        db (Database or None): MongoDB database instance
        collection (Collection or None): Patient records collection
        raw_data (DataFrame or None): Decrypted raw data
        processed_data (DataFrame or None): Preprocessed data
        label_encoders (dict): Fitted LabelEncoder instances for categorical features
        scaler (StandardScaler or None): Fitted scaler for numeric features
        feature_columns (list): Names of feature columns
        target_column (str): Name of target column ('stroke')
    """
    
    def __init__(self, mongodb_uri=None, db_name='SecureAppDB'):  # (Anthropic, 2025)
        self.mongodb_uri = mongodb_uri or 'mongodb+srv://leedstrinityhazelltu_db_user:OtEtnVn5lGBzDbYb@secureappdb.wgoupdf.mongodb.net/?appName=SecureAppDB'
        self.db_name = db_name
        self.client = None
        self.db = None
        self.collection = None
        self.raw_data = None
        self.processed_data = None
        self.label_encoders = {}
        self.scaler = None
        
        # Feature names from the dataset
        self.feature_columns = [
            'gender', 'age', 'hypertension', 'heart_disease', 'ever_married',
            'work_type', 'Residence_type', 'avg_glucose_level', 'bmi', 'smoking_status'
        ]
        self.target_column = 'stroke'
        
        """ Initialize the data processor with MongoDB connection.
        
        Args:
            mongodb_uri (str, optional): MongoDB connection string. Uses
                default cloud URI if None.
            db_name (str): Database name. Defaults to 'SecureAppDB'.
        """
        
    def connect_to_mongodb(self):  # (Anthropic, 2025)
        try:
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            self.collection = self.db.patient_records
            
            # Test connection
            self.client.server_info()
            print(f"Successfully connected to MongoDB: {self.db_name}")
            print(f"Total records in collection: {self.collection.count_documents({})}")
            return True
            
        except Exception as e:
            print(f"MongoDB connection failed: {e}")
            return False
        
        """ Establish connection to MongoDB database.
        
        Tests the connection by calling server_info() and counts documents
        in the patient_records collection.
        
        Returns:
            bool: True if connection successful and collection accessible,
                False if connection failed.
        
        Raises:
            No exceptions raised; connection errors caught and logged.
        """
    
    def fetch_encrypted_records(self):  # (Anthropic, 2025)
        if self.collection is None:
            raise ConnectionError("Not connected to MongoDB. Call connect_to_mongodb() first.")
        
        try:
            records = list(self.collection.find({}))
            print(f"Fetched {len(records)} encrypted records from database")
            return records
            
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []
        
        """ Fetch all encrypted patient records from MongoDB.
        
        Retrieves complete patient dataset including all encrypted fields
        and MongoDB metadata (_id, search hashes).
        
        Returns:
            list: List of dictionaries, each representing an encrypted
                patient record. Returns empty list if fetch fails.
        
        Raises:
            ConnectionError: If not connected to MongoDB (must call
                connect_to_mongodb() first).
        """
    
    def decrypt_records(self, encrypted_records):  # (Anthropic, 2025)
        from app.security import decrypt_patient_records_batch
        
        try:
            print("Decrypting patient records...")
            decrypted_records = decrypt_patient_records_batch(encrypted_records)
            
            # Remove MongoDB _id field and convert to DataFrame
            for record in decrypted_records:
                if '_id' in record:
                    del record['_id']
                # Remove search hash fields
                keys_to_remove = [key for key in record.keys() if key.endswith('_search')]
                for key in keys_to_remove:
                    del record[key]
            
            df = pd.DataFrame(decrypted_records)
            print(f"Successfully decrypted {len(df)} records")
            print(f"Columns: {df.columns.tolist()}")
            return df
            
        except Exception as e:
            print(f"Decryption error: {e}")
            raise
        
        """ Decrypt patient records using the app's security module.
        
        Batch decrypts all patient records and removes MongoDB-specific
        fields (_id, search hashes) to prepare data for analysis. Uses
        the application's Fernet cipher for secure decryption.
        
        Args:
            encrypted_records (list): List of encrypted record dictionaries
                from MongoDB.
        
        Returns:
            pandas.DataFrame: Decrypted patient data with one row per
                patient and columns for each data field.
        
        Raises:
            Exception: Re-raises decryption errors after logging. Common
                causes include missing/invalid encryption key or corrupted data.
        """
        
    def load_data(self):  # (Anthropic, 2025)
        if not self.connect_to_mongodb():
            raise ConnectionError("Failed to connect to MongoDB")
        
        encrypted_records = self.fetch_encrypted_records()
        if not encrypted_records:
            raise ValueError("No records found in database")
        
        self.raw_data = self.decrypt_records(encrypted_records)
        return self.raw_data
    
        """ Main method to load and decrypt data from MongoDB.
        
        Complete data loading pipeline: connects to MongoDB, fetches
        encrypted records, and decrypts them into a pandas DataFrame.
        
        Returns:
            pandas.DataFrame: Decrypted patient data ready for preprocessing.
        
        Raises:
            ConnectionError: If MongoDB connection fails.
            ValueError: If no records found in database.
            Exception: If decryption fails.
        """
    
    def handle_missing_values(self, df):  # (Anthropic, 2025)
        print("\nHandling missing values...")
        df = df.copy()
        
        # Convert BMI 'N/A' strings to NaN
        if 'bmi' in df.columns:
            df['bmi'] = df['bmi'].replace('N/A', np.nan)
            df['bmi'] = pd.to_numeric(df['bmi'], errors='coerce')
        
        # Print missing value statistics
        missing_counts = df.isnull().sum()
        if missing_counts.any():
            print("Missing values before imputation:")
            print(missing_counts[missing_counts > 0])
        
        # Numeric imputation (median)
        numeric_columns = ['age', 'avg_glucose_level', 'bmi']
        for col in numeric_columns:
            if col in df.columns and df[col].isnull().any():
                imputer = SimpleImputer(strategy='median')
                df[col] = imputer.fit_transform(df[[col]])
                print(f"  Imputed {col} using median")
        
        # Categorical imputation (mode)
        categorical_columns = ['gender', 'ever_married', 'work_type', 'Residence_type', 'smoking_status']
        for col in categorical_columns:
            if col in df.columns and df[col].isnull().any():
                imputer = SimpleImputer(strategy='most_frequent')
                df[col] = imputer.fit_transform(df[[col]]).ravel()
                print(f"  Imputed {col} using mode")
        
        print(f"Missing values after imputation: {df.isnull().sum().sum()}")
        return df
    
        """ Handle missing values in the dataset.
        
        Numeric columns (age, glucose, BMI): Median imputation,
        categorical columns (gender, smoking, etc.): Mode imputation,
        converts BMI 'N/A' strings to numeric NaN before imputation.
        
        Args:
            df (pandas.DataFrame): Input DataFrame with potential missing values.
        
        Returns:
            pandas.DataFrame: DataFrame with all missing values imputed.
                Returned as a copy; original df not modified.
        
        Raises:
            No exceptions raised; assumes valid DataFrame input.
        """
    
    def encode_categorical_features(self, df):  # (Anthropic, 2025)
        print("\nEncoding categorical features...")
        df = df.copy()
        
        # Manual encoding for gender (binary with Other category)
        if 'gender' in df.columns:
            gender_map = {'Male': 1, 'Female': 0, 'Other': 2}
            df['gender'] = df['gender'].map(gender_map)
            print(f"  Encoded gender: {gender_map}")
        
        # Manual encoding for ever_married (binary)
        if 'ever_married' in df.columns:
            married_map = {'Yes': 1, 'No': 0}
            df['ever_married'] = df['ever_married'].map(married_map)
            print(f"  Encoded ever_married: {married_map}")
        
        # Manual encoding for residence_type (binary)
        if 'Residence_type' in df.columns:
            residence_map = {'Urban': 1, 'Rural': 0}
            df['Residence_type'] = df['Residence_type'].map(residence_map)
            print(f"  Encoded Residence_type: {residence_map}")
        
        # Label encoding for work_type (multi-class)
        if 'work_type' in df.columns:
            le_work = LabelEncoder()
            df['work_type'] = le_work.fit_transform(df['work_type'])
            self.label_encoders['work_type'] = le_work
            print(f"  Encoded work_type: {dict(zip(le_work.classes_, le_work.transform(le_work.classes_)))}")
        
        # Label encoding for smoking_status (multi-class)
        if 'smoking_status' in df.columns:
            le_smoking = LabelEncoder()
            df['smoking_status'] = le_smoking.fit_transform(df['smoking_status'])
            self.label_encoders['smoking_status'] = le_smoking
            print(f"  Encoded smoking_status: {dict(zip(le_smoking.classes_, le_smoking.transform(le_smoking.classes_)))}")
        
        return df
    
        """ Encode categorical features using Label Encoding.
        
        Transforms categorical variables to numeric codes,
        gender: Male=1, Female=0, Other=2, ever_married: Yes=1, No=0, 
        Residence_type: Urban=1, Rural=0, work_type: Label encoded 0-4 (stored in self.label_encoders), 
        smoking_status: Label encoded 0-3 (stored in self.label_encoders).
        
        Args:
            df (pandas.DataFrame): Input DataFrame with categorical columns.
        
        Returns:
            pandas.DataFrame: DataFrame with categorical columns replaced
                by numeric codes. Returned as a copy; original df not modified.
        
        Raises:
            No exceptions raised; missing categorical values should be
                handled by handle_missing_values() first.
        """
    
    def normalize_features(self, df):  # (Anthropic, 2025)
        print("\nNormalizing numeric features...")
        df = df.copy()
        
        # Features to normalize (continuous numeric only)
        normalize_cols = ['age', 'avg_glucose_level', 'bmi']
        normalize_cols = [col for col in normalize_cols if col in df.columns]
        
        if normalize_cols:
            self.scaler = StandardScaler()
            df[normalize_cols] = self.scaler.fit_transform(df[normalize_cols])
            print(f"  Normalized columns: {normalize_cols}")
            print(f"  Scaler means: {dict(zip(normalize_cols, self.scaler.mean_))}")
            print(f"  Scaler stds: {dict(zip(normalize_cols, self.scaler.scale_))}")
        
        return df
    
        """ Normalize numeric features using StandardScaler.
        
        Applies z-score normalization (mean=0, std=1) to continuous numeric
        features. Binary features (0/1) are
        preserved as-is. Fitted scaler stored in self.scaler for later use.
        
        Args:
            df (pandas.DataFrame): Input DataFrame with encoded features.
        
        Returns:
            pandas.DataFrame: DataFrame with normalized continuous features
                (age, avg_glucose_level, bmi). Binary features unchanged.
                Returned as a copy; original df not modified.
        
        Raises:
            No exceptions raised; assumes numeric columns exist.
        """
    
    def balance_check(self, df):  # (Anthropic, 2025)
        if self.target_column not in df.columns:
            print("Warning: Target column 'stroke' not found for balance check")
            return {}
        
        print("\nClass distribution:")
        class_counts = df[self.target_column].value_counts()
        class_percentages = df[self.target_column].value_counts(normalize=True) * 100
        
        print(f"  No stroke (0): {class_counts.get(0, 0)} ({class_percentages.get(0, 0):.2f}%)")
        print(f"  Stroke (1): {class_counts.get(1, 0)} ({class_percentages.get(1, 0):.2f}%)")
        
        imbalance_ratio = class_counts.max() / class_counts.min() if len(class_counts) > 1 else 1
        print(f"  Imbalance ratio: {imbalance_ratio:.2f}:1")
        
        if imbalance_ratio > 10:
            print("  ⚠ Warning: Severe class imbalance detected. Consider SMOTE or class weights for model training.")
        
        return {
            'class_0': int(class_counts.get(0, 0)),
            'class_1': int(class_counts.get(1, 0)),
            'class_0_pct': float(class_percentages.get(0, 0)),
            'class_1_pct': float(class_percentages.get(1, 0)),
            'imbalance_ratio': float(imbalance_ratio)
        }
        
        """ Check and report class balance in the dataset.
        
        Analyzes target variable distribution to detect class imbalance.
        Severe imbalance (>10:1 ratio) triggers warning to use SMOTE or
        class weights during model training.
        
        Args:
            df (pandas.DataFrame): Input DataFrame with target column.
        
        Returns:
            dict: Class distribution statistics with keys:
                - class_0 (int): Count of non-stroke patients
                - class_1 (int): Count of stroke patients
                - class_0_pct (float): Percentage non-stroke
                - class_1_pct (float): Percentage stroke
                - imbalance_ratio (float): Ratio of majority to minority class
                Returns empty dict if target column missing.
        
        Raises:
            No exceptions raised.
        """
    
    def preprocess_data(self, df=None):  # (Anthropic, 2025)
        if df is None:
            if self.raw_data is None:
                raise ValueError("No data loaded. Call load_data() first.")
            df = self.raw_data.copy()
        else:
            df = df.copy()
        
        print("="*70)
        print("Starting data preprocessing pipeline...")
        print("="*70)
        
        # Step 1: Handle missing values
        df = self.handle_missing_values(df)
        
        # Step 2: Encode categorical features
        df = self.encode_categorical_features(df)
        
        # Step 3: Normalize numeric features
        df = self.normalize_features(df)
        
        # Step 4: Check class balance
        balance_stats = self.balance_check(df)
        
        self.processed_data = df
        
        print("\n" + "="*70)
        print("Preprocessing complete!")
        print("="*70)
        print(f"Final dataset shape: {df.shape}")
        print(f"Features: {[col for col in df.columns if col != self.target_column]}")
        print(f"Target: {self.target_column}")
        
        return df
    
        """ Complete preprocessing pipeline for stroke prediction data.
        
        1. Handle missing values
        2. Encode categorical features
        3. Normalize numeric features
        4. Check class balance
        
        Args:
            df: Input DataFrame (uses self.raw_data if None)
            
        Returns:
            pandas.DataFrame: Fully preprocessed data ready for modeling
        """
    
    def get_feature_target_split(self):  # (Anthropic, 2025)
        if self.processed_data is None:
            raise ValueError("No processed data available. Run preprocess_data() first.")
        
        # Exclude 'id' if present
        feature_cols = [col for col in self.processed_data.columns 
                       if col not in [self.target_column, 'id']]
        
        X = self.processed_data[feature_cols]
        y = self.processed_data[self.target_column]
        
        print(f"\nFeature matrix (X) shape: {X.shape}")
        print(f"Target vector (y) shape: {y.shape}")
        print(f"Feature columns: {X.columns.tolist()}")
        
        return X, y
    
        """ Split processed data into features (X) and target (y).
        
        Returns:
            tuple: (X, y) where X is feature DataFrame and y is target Series
        """
    
    def get_data_summary(self):  # (Anthropic, 2025)
        if self.processed_data is None:
            raise ValueError("No processed data available. Run preprocess_data() first.")
        
        summary = {
            'total_records': len(self.processed_data),
            'total_features': len(self.processed_data.columns) - 1,  # Excluding target
            'features': [col for col in self.processed_data.columns if col != self.target_column],
            'target': self.target_column,
            'data_types': self.processed_data.dtypes.to_dict(),
            'descriptive_stats': self.processed_data.describe().to_dict(),
            'missing_values': self.processed_data.isnull().sum().to_dict(),
            'class_balance': self.balance_check(self.processed_data)
        }
        
        return summary
    
        """ Generate comprehensive summary of processed data.
        
        Compiles descriptive statistics, data types, missing value counts,
        and class balance information for data quality assessment.
        
        Returns:
            dict: Summary statistics with keys:
                - total_records (int): Number of patients
                - total_features (int): Number of feature columns
                - features (list): Feature column names
                - target (str): Target column name
                - data_types (dict): Column data types
                - descriptive_stats (dict): Statistical summaries
                - missing_values (dict): Missing value counts per column
                - class_balance (dict): Class distribution statistics
        
        Raises:
            ValueError: If preprocess_data() has not been called yet.
        """
    
    def save_processed_data(self, filepath='processed_stroke_data.csv'):  # (Anthropic, 2025)
        if self.processed_data is None:
            raise ValueError("No processed data to save. Run preprocess_data() first.")
        
        self.processed_data.to_csv(filepath, index=False)
        print(f"\nProcessed data saved to: {filepath}")
        
        """ Save processed data to CSV file.
        
        Exports the preprocessed DataFrame for external analysis or
        model training outside this pipeline.
        
        Args:
            filepath (str): Output file path. Defaults to
                'processed_stroke_data.csv' in current directory.
        
        Raises:
            ValueError: If preprocess_data() has not been called yet.
            IOError: If file write fails (permissions, disk space, etc.).
        """
    
    def close_connection(self):  # (Anthropic, 2025)
        if self.client:
            self.client.close()
            print("MongoDB connection closed")
            
        """ Close MongoDB connection.
        
        Cleanly terminates the MongoDB connection. Should be called when
        data processing is complete to free resources.
        
        Raises:
            No exceptions raised.
        """

def main():  # (Anthropic, 2025)
    print("="*70)
    print("Stroke Prediction Data Processing Pipeline")
    print("="*70)
    
    # Initialize processor
    processor = StrokeDataProcessor()
    
    try:
        # Load and decrypt data from MongoDB
        print("\n[1/3] Loading encrypted data from MongoDB...")
        processor.load_data()
        print(f"Raw data shape: {processor.raw_data.shape}")
        
        # Preprocess data
        print("\n[2/3] Preprocessing data...")
        processed_df = processor.preprocess_data()
        
        # Get feature-target split
        print("\n[3/3] Preparing feature-target split...")
        X, y = processor.get_feature_target_split()
        
        # Generate summary
        print("\n" + "="*70)
        print("Data Processing Summary")
        print("="*70)
        summary = processor.get_data_summary()
        print(f"Total records: {summary['total_records']}")
        print(f"Total features: {summary['total_features']}")
        print(f"Class distribution:")
        print(f"  No stroke: {summary['class_balance']['class_0']} ({summary['class_balance']['class_0_pct']:.2f}%)")
        print(f"  Stroke: {summary['class_balance']['class_1']} ({summary['class_balance']['class_1_pct']:.2f}%)")
        
        # Optionally save processed data
        processor.save_processed_data('processed_stroke_data.csv')
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        raise
    
    finally:
        processor.close_connection()
    
    print("\n" + "="*70)
    print("Data processing complete!")
    print("="*70)
    
    """ Example usage of StrokeDataProcessor.
    
    Demonstrates the complete data processing pipeline from MongoDB
    through preprocessing and feature extraction. Saves processed
    data to CSV for inspection.
    
    Raises:
        ConnectionError: If MongoDB connection fails.
        ValueError: If no records found in database.
        Exception: For other processing errors.
    """

if __name__ == '__main__':
    main()
