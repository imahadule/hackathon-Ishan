"""
MLflow Metrics Exporter for Multiple Monitoring Platforms
=========================================================

This module extracts metrics from MLflow experiments and sends them to:
1. Grafana (via Prometheus)
2. Pramathus (configurable monitoring endpoint)
3. Other custom monitoring systems

Author: AI Assistant
License: MIT
"""

import os
import json
import logging
import requests
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pandas as pd

import mlflow
import mlflow.tracking
from mlflow.tracking import MlflowClient
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway, generate_latest
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Data class for storing metric information"""
    name: str
    value: float
    timestamp: datetime
    run_id: str
    experiment_name: str
    tags: Dict[str, str]
    step: Optional[int] = None


@dataclass
class MonitoringConfig:
    """Configuration for monitoring endpoints"""
    # MLflow settings
    mlflow_tracking_uri: str = "http://localhost:5000"
    
    # Prometheus/Grafana settings
    prometheus_gateway: str = "localhost:9091"
    prometheus_job_name: str = "mlflow_metrics"
    
    # Pramathus settings (configurable monitoring endpoint)
    pramathus_endpoint: str = "http://localhost:8080/api/metrics"
    pramathus_api_key: Optional[str] = None
    pramathus_enabled: bool = True
    
    # General settings
    export_interval: int = 60  # seconds
    max_experiments: int = 10
    include_system_metrics: bool = True


class MLflowMetricsExtractor:
    """Extracts metrics and metadata from MLflow experiments"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.client = MlflowClient(tracking_uri=config.mlflow_tracking_uri)
        
    def get_experiments(self) -> List[mlflow.entities.Experiment]:
        """Get list of MLflow experiments"""
        try:
            experiments = self.client.search_experiments(
                max_results=self.config.max_experiments
            )
            logger.info(f"Found {len(experiments)} experiments")
            return experiments
        except Exception as e:
            logger.error(f"Error fetching experiments: {e}")
            return []
    
    def get_runs_for_experiment(self, experiment_id: str) -> List[mlflow.entities.Run]:
        """Get runs for a specific experiment"""
        try:
            runs = self.client.search_runs(
                experiment_ids=[experiment_id],
                max_results=100
            )
            return runs
        except Exception as e:
            logger.error(f"Error fetching runs for experiment {experiment_id}: {e}")
            return []
    
    def extract_metrics_from_run(self, run: mlflow.entities.Run, experiment_name: str) -> List[MetricData]:
        """Extract all metrics from a single run"""
        metrics = []
        
        try:
            # Get all metric keys for this run
            metric_keys = list(run.data.metrics.keys())
            
            for metric_key in metric_keys:
                # Get metric history
                metric_history = self.client.get_metric_history(run.info.run_id, metric_key)
                
                for metric in metric_history:
                    metric_data = MetricData(
                        name=metric_key,
                        value=metric.value,
                        timestamp=datetime.fromtimestamp(metric.timestamp / 1000, tz=timezone.utc),
                        run_id=run.info.run_id,
                        experiment_name=experiment_name,
                        tags=run.data.tags,
                        step=metric.step
                    )
                    metrics.append(metric_data)
                    
        except Exception as e:
            logger.error(f"Error extracting metrics from run {run.info.run_id}: {e}")
            
        return metrics
    
    def extract_all_metrics(self) -> List[MetricData]:
        """Extract metrics from all experiments"""
        all_metrics = []
        
        experiments = self.get_experiments()
        
        for experiment in experiments:
            logger.info(f"Processing experiment: {experiment.name}")
            runs = self.get_runs_for_experiment(experiment.experiment_id)
            
            for run in runs:
                run_metrics = self.extract_metrics_from_run(run, experiment.name)
                all_metrics.extend(run_metrics)
                
        logger.info(f"Extracted {len(all_metrics)} metrics total")
        return all_metrics


class PrometheusExporter:
    """Exports metrics to Prometheus/Grafana"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.registry = CollectorRegistry()
        self.gauges = {}
        
    def _get_or_create_gauge(self, metric_name: str, labels: List[str]) -> Gauge:
        """Get or create a Prometheus gauge for the metric"""
        gauge_key = f"{metric_name}_{hash(tuple(labels))}"
        
        if gauge_key not in self.gauges:
            # Sanitize metric name for Prometheus
            safe_metric_name = metric_name.replace("-", "_").replace(".", "_")
            
            self.gauges[gauge_key] = Gauge(
                name=f"mlflow_{safe_metric_name}",
                documentation=f"MLflow metric: {metric_name}",
                labelnames=labels,
                registry=self.registry
            )
            
        return self.gauges[gauge_key]
    
    def export_metrics(self, metrics: List[MetricData]) -> bool:
        """Export metrics to Prometheus"""
        try:
            # Group metrics by name for processing
            metrics_by_name = {}
            for metric in metrics:
                if metric.name not in metrics_by_name:
                    metrics_by_name[metric.name] = []
                metrics_by_name[metric.name].append(metric)
            
            # Create gauges and set values
            for metric_name, metric_list in metrics_by_name.items():
                # Use latest value for each unique combination of labels
                latest_metrics = {}
                
                for metric in metric_list:
                    label_key = (metric.run_id, metric.experiment_name)
                    if label_key not in latest_metrics or metric.timestamp > latest_metrics[label_key].timestamp:
                        latest_metrics[label_key] = metric
                
                # Create gauge with appropriate labels
                labels = ['run_id', 'experiment_name', 'model_stage']
                gauge = self._get_or_create_gauge(metric_name, labels)
                
                # Set values for each unique label combination
                for metric in latest_metrics.values():
                    model_stage = metric.tags.get('mlflow.model.stage', 'None')
                    gauge.labels(
                        run_id=metric.run_id[:8],  # Shortened for readability
                        experiment_name=metric.experiment_name,
                        model_stage=model_stage
                    ).set(metric.value)
            
            # Push to Prometheus gateway
            if self.config.prometheus_gateway:
                push_to_gateway(
                    gateway=self.config.prometheus_gateway,
                    job=self.config.prometheus_job_name,
                    registry=self.registry
                )
                logger.info("Successfully pushed metrics to Prometheus gateway")
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting metrics to Prometheus: {e}")
            return False


class PramathusExporter:
    """Exports metrics to Pramathus monitoring platform"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.session = requests.Session()
        
        # Set up authentication if API key is provided
        if config.pramathus_api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {config.pramathus_api_key}',
                'Content-Type': 'application/json'
            })
    
    def _format_metrics_for_pramathus(self, metrics: List[MetricData]) -> Dict[str, Any]:
        """Format metrics for Pramathus API"""
        formatted_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "mlflow",
            "metrics": []
        }
        
        for metric in metrics:
            metric_entry = {
                "name": metric.name,
                "value": metric.value,
                "timestamp": metric.timestamp.isoformat(),
                "metadata": {
                    "run_id": metric.run_id,
                    "experiment_name": metric.experiment_name,
                    "step": metric.step,
                    "tags": metric.tags
                }
            }
            formatted_data["metrics"].append(metric_entry)
            
        return formatted_data
    
    def export_metrics(self, metrics: List[MetricData]) -> bool:
        """Export metrics to Pramathus"""
        if not self.config.pramathus_enabled:
            logger.info("Pramathus export is disabled")
            return True
            
        try:
            # Format metrics for the API
            payload = self._format_metrics_for_pramathus(metrics)
            
            # Send to Pramathus endpoint
            response = self.session.post(
                self.config.pramathus_endpoint,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent {len(metrics)} metrics to Pramathus")
                return True
            else:
                logger.error(f"Pramathus API error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending metrics to Pramathus: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in Pramathus export: {e}")
            return False


class MLflowMonitoringOrchestrator:
    """Main orchestrator for MLflow monitoring"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.extractor = MLflowMetricsExtractor(config)
        self.prometheus_exporter = PrometheusExporter(config)
        self.pramathus_exporter = PramathusExporter(config)
        
    def export_metrics_once(self) -> bool:
        """Extract and export metrics once"""
        logger.info("Starting metrics extraction and export")
        
        # Extract metrics from MLflow
        metrics = self.extractor.extract_all_metrics()
        
        if not metrics:
            logger.warning("No metrics found to export")
            return False
        
        # Export to Prometheus/Grafana
        prometheus_success = self.prometheus_exporter.export_metrics(metrics)
        
        # Export to Pramathus
        pramathus_success = self.pramathus_exporter.export_metrics(metrics)
        
        success = prometheus_success and pramathus_success
        
        if success:
            logger.info("Successfully exported metrics to all configured endpoints")
        else:
            logger.warning("Some exports failed")
            
        return success
    
    def run_continuous_export(self):
        """Run continuous metrics export"""
        logger.info(f"Starting continuous export with {self.config.export_interval}s interval")
        
        while True:
            try:
                self.export_metrics_once()
            except Exception as e:
                logger.error(f"Error in export cycle: {e}")
            
            time.sleep(self.config.export_interval)
    
    def generate_sample_data(self):
        """Generate sample MLflow data for testing"""
        logger.info("Generating sample MLflow data...")
        
        with mlflow.start_run():
            # Log some sample metrics
            for i in range(10):
                mlflow.log_metric("accuracy", 0.8 + 0.02 * i, step=i)
                mlflow.log_metric("loss", 0.5 - 0.03 * i, step=i)
                mlflow.log_metric("f1_score", 0.75 + 0.025 * i, step=i)
            
            # Log parameters
            mlflow.log_param("learning_rate", 0.01)
            mlflow.log_param("batch_size", 32)
            mlflow.log_param("model_type", "RandomForest")
            
            # Log tags
            mlflow.set_tag("environment", "production")
            mlflow.set_tag("version", "1.0.0")
            
        logger.info("Sample data generation completed")


def load_config_from_env() -> MonitoringConfig:
    """Load configuration from environment variables"""
    return MonitoringConfig(
        mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"),
        prometheus_gateway=os.getenv("PROMETHEUS_GATEWAY", "localhost:9091"),
        prometheus_job_name=os.getenv("PROMETHEUS_JOB_NAME", "mlflow_metrics"),
        pramathus_endpoint=os.getenv("PRAMATHUS_ENDPOINT", "http://localhost:8080/api/metrics"),
        pramathus_api_key=os.getenv("PRAMATHUS_API_KEY"),
        pramathus_enabled=os.getenv("PRAMATHUS_ENABLED", "true").lower() == "true",
        export_interval=int(os.getenv("EXPORT_INTERVAL", "60")),
        max_experiments=int(os.getenv("MAX_EXPERIMENTS", "10")),
        include_system_metrics=os.getenv("INCLUDE_SYSTEM_METRICS", "true").lower() == "true"
    )


if __name__ == "__main__":
    # Load configuration
    config = load_config_from_env()
    
    # Create orchestrator
    orchestrator = MLflowMonitoringOrchestrator(config)
    
    # Check command line arguments
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "generate-sample":
            orchestrator.generate_sample_data()
        elif sys.argv[1] == "export-once":
            orchestrator.export_metrics_once()
        elif sys.argv[1] == "continuous":
            orchestrator.run_continuous_export()
        else:
            print("Usage: python mlflow_monitoring_exporter.py [generate-sample|export-once|continuous]")
    else:
        # Default to one-time export
        orchestrator.export_metrics_once()