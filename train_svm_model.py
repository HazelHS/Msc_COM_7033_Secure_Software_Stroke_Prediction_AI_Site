# AI declaration:
# Github copilot was used for portions of the planning, research, feedback and editing of the software artefact. Mostly utilised for syntax, logic and error checking with ChatGPT and Claude Sonnet 4.5 used as the models.

""" Standalone script to train the SVM stroke prediction model.

Run this from the project root directory:
    python train_svm_model.py
"""

import sys
import os

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up Flask app context for database access
os.environ['FLASK_ENV'] = 'development'

def main(): # (Anthropic, 2025)
    from app import create_app
    from app.SVMmodel import StrokeSVMModel
    from app.DataProcessing import StrokeDataProcessor
    
    print("="*70)
    print("SVM Stroke Prediction Model Training")
    print("="*70)
    
    # Create Flask app context
    app = create_app('development')
    
    with app.app_context():
        try:
            # Step 1: Load and preprocess data
            print("\n[STEP 1/6] Data Loading and Preprocessing")
            print("-" * 70)
            
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
            print("Training Complete!")
            print("="*70)
            print(f"\nFinal Model Performance:")
            print(f"  Accuracy: {svm_trainer.metrics['after_balancing']['accuracy']*100:.4f}%")
            
        except Exception as e:
            print(f"\n{'='*70}")
            print(f"Error Occurred")
            print(f"{'='*70}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    """ Runs the SVM model training.
    
    This creates Flask context to access the encrypted database and security modules. 
    
    The process includes:
    1. Fetch and decrypt the data from MongoDB.
    2. Preprocess it, handle missing values, encode categoricals, normalize.
    3. Data Split, 65% train, 35% test with stratification.
    4. Baseline, train default SVM on imbalanced data.
    5. Optimize by applying ROS and GridSearchCV hyperparameter tuning.
    6. Evaluate the model and test set metrics and 10-fold cross-validation.
    
    Output files:
    - svm_stroke_model.pkl: Serialized trained model
    - confusion_matrix_svm.png: Confusion matrix visualization
    
    Usage:
        python train_svm_model.py
    
    Raises:
        ConnectionError: If MongoDB connection fails.
        ValueError: If no training data available.
        Exception: For other training/evaluation errors.
    """

if __name__ == '__main__':
    main()
