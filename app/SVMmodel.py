# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" SVM Model Training module for stroke prediction.

Implements Support Vector Machine classifier:
- Random Oversampling (ROS) for class imbalance
- GridSearchCV for hyperparameter tuning
- 10-fold cross-validation
- Comprehensive performance evaluation
"""

import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score, cross_validate
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score, 
                            confusion_matrix, classification_report, roc_auc_score, roc_curve)
from imblearn.over_sampling import RandomOverSampler
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import time
import sys
import os
import warnings
import hmac
import hashlib
warnings.filterwarnings('ignore')

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Support Vector Machine model for stroke prediction with comprehensive evaluation.
class StrokeSVMModel: # (Anthropic, 2025)
    def __init__(self, random_state=42): # (Anthropic, 2025)
        self.random_state = random_state
        self.model = None
        self.best_params = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.X_train_balanced = None
        self.y_train_balanced = None
        self.training_time = 0
        self.prediction_time = 0
        
        # Performance metrics storage
        self.metrics = {
            'before_balancing': {},
            'after_balancing': {},
            'cross_validation': {}
        }
        
        """ Initialize the SVM model trainer.
        
        Args:
            random_state (int): Random seed for reproducibility. Defaults to 42.
        """
        
    def prepare_data(self, X, y, test_size=0.35): # (Anthropic, 2025)
        print("="*70)
        print("Data Preparation")
        print("="*70)
        
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )
        
        print(f"Training set size: {len(self.X_train)} ({(1-test_size)*100:.0f}%)")
        print(f"Testing set size: {len(self.X_test)} ({test_size*100:.0f}%)")
        print(f"\nClass distribution in training set:")
        print(f"  No stroke (0): {(self.y_train == 0).sum()}")
        print(f"  Stroke (1): {(self.y_train == 1).sum()}")
        print(f"  Imbalance ratio: {(self.y_train == 0).sum() / (self.y_train == 1).sum():.2f}:1")
        
        return self.X_train, self.X_test, self.y_train, self.y_test
    
        """ Split data into training and testing sets.
        
        Uses stratified splitting to maintain class distribution in both sets.
        Reports class imbalance in training data.
        
        Args:
            X (pandas.DataFrame or numpy.ndarray): Feature matrix with shape
                (n_samples, n_features).
            y (pandas.Series or numpy.ndarray): Target vector with shape (n_samples,).
            test_size (float): Proportion of data for testing. Defaults to 0.35
        
        Returns:
            tuple: Four arrays (X_train, X_test, y_train, y_test) containing
                training and test data splits.
        
        Raises:
            ValueError: If X and y have incompatible shapes.
        """
    
    def apply_random_oversampling(self): # (Anthropic, 2025)
        print("\n" + "="*70)
        print("Applying Random Oversampling (ROS)")
        print("="*70)
        
        if self.X_train is None or self.y_train is None:
            raise ValueError("Training data not prepared. Call prepare_data() first.")
        
        ros = RandomOverSampler(random_state=self.random_state)
        self.X_train_balanced, self.y_train_balanced = ros.fit_resample(
            self.X_train, self.y_train
        )
        
        print(f"Original training set size: {len(self.X_train)}")
        print(f"Balanced training set size: {len(self.X_train_balanced)}")
        print(f"\nClass distribution after ROS:")
        print(f"  No stroke (0): {(self.y_train_balanced == 0).sum()}")
        print(f"  Stroke (1): {(self.y_train_balanced == 1).sum()}")
        print(f"  Balance achieved: {(self.y_train_balanced == 0).sum() / (self.y_train_balanced == 1).sum():.2f}:1")
        
        return self.X_train_balanced, self.y_train_balanced
    
        """ Apply Random Oversampling (ROS) to balance training data.
        
        Addresses severe class imbalance by duplicating minority class samples
        until balanced with majority class.
        
        Returns:
            tuple: Two arrays (X_train_balanced, y_train_balanced) containing
                balanced training data. Both classes have equal representation.
        
        Raises:
            ValueError: If prepare_data() has not been called yet.
        """
    
    def train_baseline_svm(self): # (Anthropic, 2025)
        print("\n" + "="*70)
        print("Training Baseline SVM (Before Optimization)")
        print("="*70)
        
        baseline_svm = SVC(kernel='rbf', random_state=self.random_state)
        
        start_time = time.time()
        baseline_svm.fit(self.X_train, self.y_train)
        train_time = time.time() - start_time
        
        start_time = time.time()
        y_pred = baseline_svm.predict(self.X_test)
        pred_time = time.time() - start_time
        
        # Calculate metrics
        metrics = {
            'accuracy': accuracy_score(self.y_test, y_pred),
            'precision': precision_score(self.y_test, y_pred, zero_division=0),
            'recall': recall_score(self.y_test, y_pred, zero_division=0),
            'f1_score': f1_score(self.y_test, y_pred, zero_division=0),
            'training_time': train_time,
            'prediction_time': pred_time
        }
        
        self.metrics['before_balancing'] = metrics
        
        print(f"Accuracy:  {metrics['accuracy']*100:.2f}%")
        print(f"Precision: {metrics['precision']*100:.2f}%")
        print(f"Recall:    {metrics['recall']*100:.2f}%")
        print(f"F1-Score:  {metrics['f1_score']*100:.2f}%")
        print(f"Training time: {train_time:.2f}s")
        print(f"Prediction time: {pred_time:.4f}s")
        
        return metrics
    
        """ Train baseline SVM without hyperparameter tuning for comparison.
        
        Establishes performance baseline using default RBF kernel SVM
        on imbalanced data. Used to demonstrate improvement from
        optimization techniques.
        
        Returns:
            dict: Performance metrics with keys 'accuracy', 'precision',
                'recall', 'f1_score', 'training_time', 'prediction_time'.
        
        Raises:
            ValueError: If prepare_data() has not been called yet.
        """
    
    def hyperparameter_tuning(self, use_balanced_data=True): # (Anthropic, 2025)
        print("\n" + "="*70)
        print("Hyperparameter Tuning with GridSearchCV")
        print("="*70)
        
        if use_balanced_data:
            if self.X_train_balanced is None:
                raise ValueError("Balanced data not available. Call apply_random_oversampling() first.")
            X_train_use = self.X_train_balanced
            y_train_use = self.y_train_balanced
            print("Using ROS-balanced training data")
        else:
            X_train_use = self.X_train
            y_train_use = self.y_train
            print("Using original imbalanced training data")
        
        # Parameter grid.
        param_grid = {
            'C': [1, 10, 100], # change these to alter performance, reference paper used: [0.1, 1, 10, 100, 1000])
            'gamma': ['scale', 0.1], # and: [‘scale’, ‘auto’, 0.01, 0.1, 1]), which is more appropriate for larger datasets.
            'kernel': ['rbf', 'linear'],
            'class_weight': [None, 'balanced']
        }
        
        print(f"\nParameter grid:")
        for param, values in param_grid.items():
            print(f"  {param}: {values}")
        
        total_combinations = np.prod([len(v) for v in param_grid.values()])
        total_fits = total_combinations * 10
        print(f"\nTotal combinations to evaluate: {total_combinations}")
        print(f"\nProgress tracking:")
        
        # Custom scoring function to track progress
        from sklearn.model_selection import cross_validate
        import sys
        
        # Create a custom scorer that prints progress
        fit_counter = {'count': 0}
        
        def progress_callback(estimator, X, y):
            fit_counter['count'] += 1
            progress_pct = (fit_counter['count'] / total_fits) * 100
            elapsed = time.time() - start_time
            if fit_counter['count'] > 0:
                eta = (elapsed / fit_counter['count']) * (total_fits - fit_counter['count'])
                print(f"\rProgress: {fit_counter['count']}/{total_fits} fits ({progress_pct:.1f}%) | "
                      f"Elapsed: {elapsed:.1f}s | ETA: {eta:.1f}s", end='', flush=True)
            return estimator.score(X, y)
        
        # GridSearchCV with enhanced verbosity
        grid_search = GridSearchCV(
            SVC(random_state=self.random_state),
            param_grid,
            cv=10,
            scoring='accuracy',
            n_jobs=-1,
            verbose=3,  # Maximum verbosity
            return_train_score=True
        )
        
        print("Starting grid search...")
        print("-" * 70)
        start_time = time.time()
        grid_search.fit(X_train_use, y_train_use)
        self.training_time = time.time() - start_time
        print()  # New line after progress
        
        self.best_params = grid_search.best_params_
        self.model = grid_search.best_estimator_
        
        print("-" * 70)
        print(f"\n✓ Grid search completed!")
        print(f"  Total time: {self.training_time:.2f}s ({self.training_time/60:.2f} minutes)")
        print(f"  Average time per fit: {self.training_time/total_fits:.3f}s")
        print(f"  Fits per second: {total_fits/self.training_time:.2f}")
        
        print(f"\nBest parameters found:")
        for param, value in self.best_params.items():
            print(f"  {param}: {value}")
        print(f"\nBest cross-validation score: {grid_search.best_score_*100:.4f}%")
        
        # Show detailed results
        print(f"\nTop 5 parameter combinations:")
        results_df = pd.DataFrame(grid_search.cv_results_)
        top_5 = results_df.nsmallest(5, 'rank_test_score')[
            ['params', 'mean_test_score', 'std_test_score', 'mean_fit_time', 'rank_test_score']
        ]
        for idx, row in top_5.iterrows():
            print(f"\n  Rank {int(row['rank_test_score'])}: {row['params']}")
            print(f"    Test Accuracy:  {row['mean_test_score']*100:.4f}% (±{row['std_test_score']*100:.4f}%)")
            print(f"    Avg Fit Time:   {row['mean_fit_time']:.3f}s")
        
        return self.best_params
    
        """ Perform hyperparameter tuning using GridSearchCV.
        
        Exhaustive search over parameter combinations using 10-fold
        cross-validation. Evaluates 24 combinations.
        
        Parameter grid:
        - C: Regularization [1, 10, 100]
        - gamma: Kernel coefficient ['scale', 0.1]
        - kernel: SVM kernel ['rbf', 'linear']
        - class_weight: Sample weighting [None, 'balanced']
        
        Args:
            use_balanced_data (bool): Whether to use ROS-balanced training
                data. Defaults to True (recommended). If False, uses
                imbalanced original data.
        
        Returns:
            dict: Best parameters found by GridSearchCV with keys
                'C', 'gamma', 'kernel', 'class_weight'.
        
        Raises:
            ValueError: If use_balanced_data=True but apply_random_oversampling()
                has not been called yet.
        """
    
    def evaluate_model(self, detailed=True): # (Anthropic, 2025)
        print("\n" + "="*70)
        print("Model Evaluation on Test Set")
        print("="*70)
        
        if self.model is None:
            raise ValueError("Model not trained. Call hyperparameter_tuning() first.")
        
        start_time = time.time()
        y_pred = self.model.predict(self.X_test)
        self.prediction_time = time.time() - start_time
        
        # Calculate comprehensive metrics
        metrics = {
            'accuracy': accuracy_score(self.y_test, y_pred),
            'precision': precision_score(self.y_test, y_pred, zero_division=0),
            'recall': recall_score(self.y_test, y_pred, zero_division=0),
            'f1_score': f1_score(self.y_test, y_pred, zero_division=0),
            'confusion_matrix': confusion_matrix(self.y_test, y_pred),
            'training_time': self.training_time,
            'prediction_time': self.prediction_time
        }
        
        # Calculate error rate
        cm = metrics['confusion_matrix']
        fp = cm[0, 1]
        fn = cm[1, 0]
        tp = cm[1, 1]
        tn = cm[0, 0]
        metrics['error_rate'] = (fp + fn) / (tp + tn + fp + fn)
        
        self.metrics['after_balancing'] = metrics
        
        print(f"Accuracy:  {metrics['accuracy']*100:.4f}%")
        print(f"Precision: {metrics['precision']*100:.4f}%")
        print(f"Recall:    {metrics['recall']*100:.4f}%")
        print(f"F1-Score:  {metrics['f1_score']*100:.4f}%")
        print(f"Error Rate: {metrics['error_rate']*100:.5f}%")
        print(f"Training time: {metrics['training_time']:.2f}s")
        print(f"Prediction time: {metrics['prediction_time']:.4f}s")
        
        if detailed:
            print("\nConfusion Matrix:")
            print(cm)
            print(f"  True Negatives (TN):  {tn}")
            print(f"  False Positives (FP): {fp}")
            print(f"  False Negatives (FN): {fn}")
            print(f"  True Positives (TP):  {tp}")
            
            print("\nDetailed Classification Report:")
            print(classification_report(self.y_test, y_pred, target_names=['No Stroke', 'Stroke']))
        
        return metrics
    
        """ Evaluate the trained model on test data.
        
        Calculates comprehensive performance metrics including accuracy,
        precision, recall, F1-score, confusion matrix, and error rate.
        
        Args:
            detailed (bool): Whether to print detailed classification report
                and confusion matrix breakdown. Defaults to True.
        
        Returns:
            dict: Comprehensive performance metrics with keys:
                - accuracy (float): Overall classification accuracy
                - precision (float): Positive predictive value
                - recall (float): True positive rate (sensitivity)
                - f1_score (float): Harmonic mean of precision and recall
                - confusion_matrix (ndarray): 2x2 confusion matrix
                - error_rate (float): Misclassification rate
                - training_time (float): Model training duration
                - prediction_time (float): Prediction duration
        
        Raises:
            ValueError: If hyperparameter_tuning() has not been called yet.
        """
    
    def cross_validation_evaluation(self, cv=10): # (Anthropic, 2025)
        print("\n" + "="*70)
        print(f"{cv}-Fold Cross-Validation")
        print("="*70)
        
        if self.model is None:
            raise ValueError("Model not trained. Call hyperparameter_tuning() first.")
        
        if self.X_train_balanced is None:
            X_use = self.X_train
            y_use = self.y_train
        else:
            X_use = self.X_train_balanced
            y_use = self.y_train_balanced
        
        scoring = ['accuracy', 'precision', 'recall', 'f1']
        
        print(f"Running {cv}-fold cross-validation...")
        cv_results = cross_validate(
            self.model, X_use, y_use, 
            cv=cv, 
            scoring=scoring,
            return_train_score=False,
            n_jobs=-1
        )
        
        cv_metrics = {
            'accuracy_mean': cv_results['test_accuracy'].mean(),
            'accuracy_std': cv_results['test_accuracy'].std(),
            'precision_mean': cv_results['test_precision'].mean(),
            'precision_std': cv_results['test_precision'].std(),
            'recall_mean': cv_results['test_recall'].mean(),
            'recall_std': cv_results['test_recall'].std(),
            'f1_mean': cv_results['test_f1'].mean(),
            'f1_std': cv_results['test_f1'].std(),
        }
        
        self.metrics['cross_validation'] = cv_metrics
        
        print(f"\nCross-Validation Results ({cv} folds):")
        print(f"Accuracy:  {cv_metrics['accuracy_mean']*100:.4f}% (±{cv_metrics['accuracy_std']*100:.4f}%)")
        print(f"Precision: {cv_metrics['precision_mean']*100:.4f}% (±{cv_metrics['precision_std']*100:.4f}%)")
        print(f"Recall:    {cv_metrics['recall_mean']*100:.4f}% (±{cv_metrics['recall_std']*100:.4f}%)")
        print(f"F1-Score:  {cv_metrics['f1_mean']*100:.4f}% (±{cv_metrics['f1_std']*100:.4f}%)")
        
        return cv_metrics
    
        """ Perform k-fold cross-validation.
        
        Evaluates model stability and generalization using stratified
        k-fold cross-validation. Reports mean and standard deviation
        for all metrics to assess variance.
        
        Args:
            cv (int): Number of folds.
        
        Returns:
            dict: Cross-validation scores with keys:
                - accuracy_mean (float): Mean CV accuracy
                - accuracy_std (float): Standard deviation of accuracy
                - precision_mean (float): Mean CV precision
                - precision_std (float): Standard deviation of precision
                - recall_mean (float): Mean CV recall
                - recall_std (float): Standard deviation of recall
                - f1_mean (float): Mean CV F1-score
                - f1_std (float): Standard deviation of F1-score
        
        Raises:
            ValueError: If hyperparameter_tuning() has not been called yet.
        """
    
    def plot_confusion_matrix(self, save_path=None): # (Anthropic, 2025)
        if 'confusion_matrix' not in self.metrics['after_balancing']:
            raise ValueError("Model not evaluated. Call evaluate_model() first.")
        
        cm = self.metrics['after_balancing']['confusion_matrix']
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                   xticklabels=['No Stroke', 'Stroke'],
                   yticklabels=['No Stroke', 'Stroke'])
        plt.title('Confusion Matrix - SVM Stroke Prediction')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Confusion matrix saved to: {save_path}")
        
        plt.tight_layout()
        plt.show()
        
        """ Plot confusion matrix heatmap.
        
        Generates publication-quality confusion matrix visualization
        showing true positives, false positives, true negatives, and
        false negatives.
        
        Args:
            save_path (str, optional): File path to save plot. If None,
                displays plot interactively. Supports .png, .jpg, .pdf.
        
        Raises:
            ValueError: If evaluate_model() has not been called yet.
            IOError: If save_path write fails.
        """
    
    def save_model(self, filepath='svm_stroke_model.pkl'): # (Anthropic, 2025)
        if self.model is None:
            raise ValueError("No trained model to save.")
        
        model_data = {
            'model': self.model,
            'best_params': self.best_params,
            'metrics': self.metrics,
            'random_state': self.random_state
        }
        # Serialize to bytes first so we can sign the exact payload written to disk
        data_bytes = pickle.dumps(model_data)
        with open(filepath, 'wb') as f:
            f.write(data_bytes)

        # Compute HMAC-SHA256 signature using SECRET_KEY to ensure model integrity/provenance
        secret = os.environ.get('SECRET_KEY', '')
        sig = hmac.new(secret.encode('utf-8'), data_bytes, hashlib.sha256).hexdigest()
        with open(f"{filepath}.sig", 'w') as sf:
            sf.write(sig)

        print(f"\nModel saved to: {filepath}")
        print(f"Signature saved to: {filepath}.sig")
        print(f"Model size: {len(data_bytes) / 1024:.2f} KB")
        """ Save trained model to pickle file.
        
        Serializes complete model package including trained SVM,
        hyperparameters, and performance metrics for deployment.
        
        Args:
            filepath (str): Path to save pickle file. Defaults to
                'svm_stroke_model.pkl' in current directory.
        
        Raises:
            ValueError: If hyperparameter_tuning() has not been called yet.
            IOError: If file write fails (permissions, disk space, etc.).
        """
    
    def load_model(self, filepath='svm_stroke_model.pkl'): # (Anthropic, 2025)
        sig_path = f"{filepath}.sig"
        if not os.path.exists(sig_path):
            raise FileNotFoundError(f"Model signature missing: {sig_path} (refuse to load unsigned model)")

        # Read bytes and verify signature before unpickling. This ensures that the model has not been tampered with, and only trusted models generated by this app are loaded.
        with open(filepath, 'rb') as f:
            data_bytes = f.read()
        with open(sig_path, 'r') as sf:
            expected_sig = sf.read().strip()

        secret = os.environ.get('SECRET_KEY', '')
        calc_sig = hmac.new(secret.encode('utf-8'), data_bytes, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc_sig, expected_sig):
            raise ValueError("Model signature mismatch; refusing to load model")

        # Safe to unpickle now (integrity & provenance enforced).
        model_data = pickle.loads(data_bytes)  # nosec: B301

        self.model = model_data['model']
        self.best_params = model_data['best_params']
        self.metrics = model_data['metrics']
        self.random_state = model_data['random_state']
        
        print(f"Model loaded from: {filepath} (signature verified)")
        
        """ Load trained model from pickle file.
        
        Deserializes saved model package, restoring trained SVM,
        hyperparameters, and performance metrics.
        
        Args:
            filepath (str): Path to pickle file. Defaults to
                'svm_stroke_model.pkl' in current directory.
        
        Raises:
            FileNotFoundError: If pickle file doesn't exist.
            pickle.UnpicklingError: If file is corrupted or incompatible.
        """
    
    def predict(self, X): # (Anthropic, 2025)
        if self.model is None:
            raise ValueError("Model not trained. Call hyperparameter_tuning() first.")
        
        return self.model.predict(X)
    
        """ Make predictions on new data.
        
        Applies trained SVM classifier to new patient data.
        
        Args:
            X (pandas.DataFrame or numpy.ndarray): Feature matrix with
                same shape as training data (n_samples, n_features).
        
        Returns:
            numpy.ndarray: Binary predictions (0=no stroke, 1=stroke)
                with shape (n_samples,).
        
        Raises:
            ValueError: If hyperparameter_tuning() has not been called yet.
        """
    
    def generate_performance_report(self): # (Anthropic, 2025)
        print("\n" + "="*70)
        print("COMPREHENSIVE PERFORMANCE REPORT")
        print("="*70)
        
        print("\n[1] Before Optimization (Imbalanced Data)")
        print("-" * 70)
        if self.metrics['before_balancing']:
            for metric, value in self.metrics['before_balancing'].items():
                if 'time' not in metric:
                    print(f"  {metric.capitalize()}: {value*100:.2f}%")
        
        print("\n[2] After Optimization (Balanced Data + GridSearchCV)")
        print("-" * 70)
        if self.metrics['after_balancing']:
            for metric, value in self.metrics['after_balancing'].items():
                if metric == 'confusion_matrix':
                    continue
                elif 'time' in metric:
                    print(f"  {metric.replace('_', ' ').title()}: {value:.4f}s")
                else:
                    print(f"  {metric.replace('_', ' ').title()}: {value*100:.4f}%")
        
        print("\n[3] Cross-Validation Results")
        print("-" * 70)
        if self.metrics['cross_validation']:
            for metric, value in self.metrics['cross_validation'].items():
                print(f"  {metric.replace('_', ' ').title()}: {value*100:.4f}%")
        
        print("\n" + "="*70)
        
        """ Generate comprehensive performance comparison report.
        
        Produces formatted report comparing baseline model (before optimization), 
        the optimized model (after ROS + GridSearchCV) and cross-validation results and 
        shows improvement from optimization techniques and model stability.
        
        Raises:
            No exceptions raised; prints available metrics only.
        """

def main(): # (Anthropic, 2025)
    print("="*70)
    print("SVM Stroke Prediction Model Training")
    print("="*70)
    
    try:
        # Step 1: Load and preprocess data
        print("\n[STEP 1/6] Data Loading and Preprocessing")
        print("-" * 70)
        
        # Try to import from app package, fallback to direct import
        try:
            from app.DataProcessing import StrokeDataProcessor
        except ImportError:
            # If app module not found, try importing from current directory
            from DataProcessing import StrokeDataProcessor
        
        processor = StrokeDataProcessor()
        processor.load_data()
        processed_df = processor.preprocess_data()
        X, y = processor.get_feature_target_split()
        
        # Step 2: Initialize SVM trainer
        print("\n[STEP 2/6] Initializing SVM Model Trainer")
        print("-" * 70)
        svm_trainer = StrokeSVMModel(random_state=42)
        
        # Step 3: Prepare data (65-35 split)
        print("\n[STEP 3/6] Data Splitting")
        print("-" * 70)
        svm_trainer.prepare_data(X, y, test_size=0.35)
        
        # Step 4: Train baseline model
        print("\n[STEP 4/6] Baseline SVM Training")
        print("-" * 70)
        svm_trainer.train_baseline_svm()
        
        # Step 5: Apply ROS and hyperparameter tuning
        print("\n[STEP 5/6] Random Oversampling + Hyperparameter Tuning")
        print("-" * 70)
        svm_trainer.apply_random_oversampling()
        svm_trainer.hyperparameter_tuning(use_balanced_data=True)
        
        # Step 6: Evaluate optimized model
        print("\n[STEP 6/6] Final Model Evaluation")
        print("-" * 70)
        svm_trainer.evaluate_model(detailed=True)
        svm_trainer.cross_validation_evaluation(cv=10)
        
        # Generate comprehensive report
        svm_trainer.generate_performance_report()
        
        # Save model
        print("\n[FINAL] Saving Model")
        print("-" * 70)
        svm_trainer.save_model('svm_stroke_model.pkl')
        
        # Plot confusion matrix
        try:
            svm_trainer.plot_confusion_matrix(save_path='confusion_matrix_svm.png')
        except Exception as e:
            print(f"Could not generate confusion matrix plot: {e}")
        
        processor.close_connection()
        
        print("\n" + "="*70)
        print("TRAINING COMPLETE!")
        print("="*70)
        print(f"\nFinal Model Performance:")
        print(f"  Accuracy: {svm_trainer.metrics['after_balancing']['accuracy']*100:.4f}%")
        
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"ERROR OCCURRED")
        print(f"{'='*70}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    """ Main training entry point.
    
    Executes:
    1. Fetch and decrypt the data from MongoDB.
    2. Preprocess it, handle missing values, encode categoricals, normalize.
    3. Data Split, 65% train, 35% test with stratification.
    4. Baseline, train default SVM on imbalanced data.
    5. Optimize by applying ROS and GridSearchCV hyperparameter tuning.
    6. Evaluate the model and test set metrics and 10-fold cross-validation.
    
    Saves trained model to 'svm_stroke_model.pkl' and confusion matrix
    plot to 'confusion_matrix_svm.png'.
    
    Raises:
        ConnectionError: If MongoDB connection fails.
        ValueError: If no data available for training.
        Exception: For other training errors.
    """

if __name__ == '__main__':
    main()
