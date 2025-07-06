#!/usr/bin/env python3
"""
Example MLflow Training Pipeline with Monitoring
===============================================

This script demonstrates how to:
1. Train a machine learning model
2. Log metrics to MLflow
3. Use the monitoring system to export metrics to Grafana and Pramathus

Run this after setting up the monitoring stack with setup.sh
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.datasets import make_classification
import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
import time


def generate_sample_dataset():
    """Generate a sample classification dataset"""
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        n_classes=2,
        random_state=42
    )
    
    # Create feature names
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    
    # Convert to DataFrame for easier handling
    df = pd.DataFrame(X, columns=feature_names)
    df['target'] = y
    
    return df


def train_model(model_type="random_forest", experiment_name="ml_monitoring_demo"):
    """Train a model and log metrics to MLflow"""
    
    # Set up MLflow
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment(experiment_name)
    
    # Generate or load data
    print("📊 Generating sample dataset...")
    df = generate_sample_dataset()
    
    # Prepare data
    X = df.drop('target', axis=1)
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Start MLflow run
    with mlflow.start_run(run_name=f"{model_type}_training"):
        print(f"🤖 Training {model_type} model...")
        
        # Log dataset information
        mlflow.log_param("dataset_size", len(df))
        mlflow.log_param("n_features", X.shape[1])
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("test_size", len(X_test))
        
        # Select and configure model
        if model_type == "random_forest":
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            mlflow.log_params({
                "model_type": "RandomForest",
                "n_estimators": 100,
                "max_depth": 10
            })
        elif model_type == "logistic_regression":
            model = LogisticRegression(random_state=42, max_iter=1000)
            mlflow.log_params({
                "model_type": "LogisticRegression",
                "max_iter": 1000
            })
        elif model_type == "svm":
            model = SVC(random_state=42, probability=True)
            mlflow.log_params({
                "model_type": "SVM",
                "kernel": "rbf"
            })
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Train model
        start_time = time.time()
        model.fit(X_train, y_train)
        training_time = time.time() - start_time
        
        # Make predictions
        y_pred_train = model.predict(X_train)
        y_pred_test = model.predict(X_test)
        
        # Calculate metrics
        train_accuracy = accuracy_score(y_train, y_pred_train)
        test_accuracy = accuracy_score(y_test, y_pred_test)
        test_precision = precision_score(y_test, y_pred_test, average='weighted')
        test_recall = recall_score(y_test, y_pred_test, average='weighted')
        test_f1 = f1_score(y_test, y_pred_test, average='weighted')
        
        # Log metrics to MLflow
        mlflow.log_metric("train_accuracy", train_accuracy)
        mlflow.log_metric("test_accuracy", test_accuracy)
        mlflow.log_metric("accuracy", test_accuracy)  # Primary metric for monitoring
        mlflow.log_metric("precision", test_precision)
        mlflow.log_metric("recall", test_recall)
        mlflow.log_metric("f1_score", test_f1)
        mlflow.log_metric("training_time", training_time)
        
        # Calculate and log loss (for monitoring)
        train_loss = 1 - train_accuracy
        test_loss = 1 - test_accuracy
        mlflow.log_metric("train_loss", train_loss)
        mlflow.log_metric("test_loss", test_loss)
        mlflow.log_metric("loss", test_loss)  # Primary loss metric for monitoring
        
        # Log model
        mlflow.sklearn.log_model(
            model, 
            "model",
            registered_model_name=f"{experiment_name}_{model_type}"
        )
        
        # Add tags
        mlflow.set_tags({
            "environment": "development",
            "version": "1.0.0",
            "model_family": model_type,
            "data_version": "v1.0"
        })
        
        print(f"✅ Model trained successfully!")
        print(f"   - Train Accuracy: {train_accuracy:.4f}")
        print(f"   - Test Accuracy: {test_accuracy:.4f}")
        print(f"   - F1 Score: {test_f1:.4f}")
        print(f"   - Training Time: {training_time:.2f}s")
        
        return mlflow.active_run().info.run_id


def simulate_training_over_time():
    """Simulate multiple training runs over time with different data drift scenarios"""
    
    experiment_name = "drift_simulation"
    model_types = ["random_forest", "logistic_regression", "svm"]
    
    print("🔄 Simulating model training over time...")
    
    for iteration in range(5):
        print(f"\n📅 Training iteration {iteration + 1}/5")
        
        for model_type in model_types:
            try:
                # Add some variability to simulate real-world scenarios
                time.sleep(2)  # Simulate time between experiments
                
                run_id = train_model(
                    model_type=model_type, 
                    experiment_name=experiment_name
                )
                
                print(f"   ✅ {model_type} completed (Run ID: {run_id[:8]})")
                
            except Exception as e:
                print(f"   ❌ {model_type} failed: {e}")
        
        # Wait between iterations
        if iteration < 4:  # Don't wait after the last iteration
            print("   ⏳ Waiting before next iteration...")
            time.sleep(5)
    
    print("🎉 Simulation completed!")


def check_monitoring_setup():
    """Check if the monitoring system is properly set up"""
    
    print("🔍 Checking monitoring system setup...")
    
    # Check MLflow
    try:
        mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        client = MlflowClient(tracking_uri=mlflow_uri)
        experiments = client.search_experiments()
        print(f"✅ MLflow connected ({len(experiments)} experiments found)")
    except Exception as e:
        print(f"❌ MLflow connection failed: {e}")
        return False
    
    # Check if monitoring exporter environment is set
    prometheus_gateway = os.getenv("PROMETHEUS_GATEWAY", "localhost:9091")
    pramathus_endpoint = os.getenv("PRAMATHUS_ENDPOINT", "http://localhost:8080/api/metrics")
    
    print(f"📊 Prometheus Gateway: {prometheus_gateway}")
    print(f"🎯 Pramathus Endpoint: {pramathus_endpoint}")
    
    print("✅ Monitoring setup looks good!")
    return True


def main():
    """Main function to demonstrate the monitoring system"""
    
    print("🚀 MLflow Monitoring Demo")
    print("=" * 50)
    
    # Check setup
    if not check_monitoring_setup():
        print("\n❌ Monitoring setup check failed!")
        print("💡 Make sure to run './setup.sh' first")
        return
    
    print("\n🎯 Choose an option:")
    print("1. Train a single model")
    print("2. Simulate training over time (multiple models)")
    print("3. Generate continuous data for monitoring")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            model_type = input("Enter model type (random_forest/logistic_regression/svm): ").strip()
            if model_type not in ["random_forest", "logistic_regression", "svm"]:
                model_type = "random_forest"
            
            run_id = train_model(model_type=model_type)
            
            print(f"\n🎉 Training completed!")
            print(f"📊 Run ID: {run_id}")
            print("🔗 View in MLflow UI: http://localhost:5000")
            
        elif choice == "2":
            simulate_training_over_time()
            
            print(f"\n🎉 Simulation completed!")
            print("📊 Check metrics in:")
            print("   - MLflow UI: http://localhost:5000")
            print("   - Grafana: http://localhost:3000 (admin/admin123)")
            print("   - Prometheus: http://localhost:9090")
            
        elif choice == "3":
            print("🔄 Starting continuous training simulation...")
            print("   (Press Ctrl+C to stop)")
            
            iteration = 1
            while True:
                try:
                    print(f"\n🔄 Continuous iteration {iteration}")
                    
                    # Train a random model type
                    model_type = np.random.choice(["random_forest", "logistic_regression", "svm"])
                    train_model(model_type=model_type, experiment_name="continuous_monitoring")
                    
                    iteration += 1
                    time.sleep(30)  # Wait 30 seconds between runs
                    
                except KeyboardInterrupt:
                    print("\n⏹️  Stopping continuous simulation...")
                    break
                except Exception as e:
                    print(f"❌ Error in iteration {iteration}: {e}")
                    time.sleep(10)
            
        else:
            print("❌ Invalid choice. Please run the script again.")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")


if __name__ == "__main__":
    main()