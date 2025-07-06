# MLflow Matrix Monitoring System

A comprehensive solution for extracting metrics from MLflow and sending them to multiple monitoring platforms including **Grafana** and **Pramathus**.

## 🚀 Features

- **Multi-Platform Export**: Send metrics to Grafana (via Prometheus) and Pramathus simultaneously
- **Real-Time Monitoring**: Continuous export of MLflow experiments and runs
- **Containerized Deployment**: Complete Docker Compose setup for easy deployment
- **Configurable**: Environment variables and YAML configuration support
- **Extensible**: Easy to add new monitoring endpoints
- **Production Ready**: Error handling, logging, and health checks included

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.9+ (if running locally)
- MLflow tracking server (or use the included one)

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd mlflow-monitoring
```

### 2. Configure Your Endpoints

Edit `config.yaml` to match your monitoring setup:

```yaml
# Update the Pramathus endpoint to your actual system
pramathus:
  endpoint: "https://your-pramathus-instance.com/api/metrics"
  api_key: "your-api-key"  # or set PRAMATHUS_API_KEY env var
  enabled: true
```

### 3. Deploy with Docker Compose

```bash
# Start the complete monitoring stack
docker-compose up -d

# Check that all services are running
docker-compose ps
```

### 4. Access the Services

- **MLflow UI**: http://localhost:5000
- **Grafana Dashboard**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Prometheus Pushgateway**: http://localhost:9091

### 5. Generate Sample Data

```bash
# Generate sample MLflow experiments for testing
docker-compose exec mlflow-exporter python mlflow_monitoring_exporter.py generate-sample
```

## 📊 What Gets Monitored

### MLflow Metrics Exported:
- **Experiment Metrics**: accuracy, loss, f1_score, precision, recall, etc.
- **Model Performance**: training and validation metrics over time
- **Run Metadata**: experiment names, run IDs, model stages
- **Custom Metrics**: Any metrics logged to MLflow

### Prometheus Labels:
- `run_id`: MLflow run identifier (shortened)
- `experiment_name`: Name of the MLflow experiment
- `model_stage`: Model stage (if specified)

### Pramathus Payload:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "source": "mlflow",
  "metrics": [
    {
      "name": "accuracy",
      "value": 0.95,
      "timestamp": "2024-01-15T10:29:45Z",
      "metadata": {
        "run_id": "abc123...",
        "experiment_name": "model_training",
        "step": 10,
        "tags": {...}
      }
    }
  ]
}
```

## ⚙️ Configuration

### Environment Variables

```bash
# MLflow Configuration
export MLFLOW_TRACKING_URI="http://localhost:5000"

# Prometheus Configuration  
export PROMETHEUS_GATEWAY="localhost:9091"
export PROMETHEUS_JOB_NAME="mlflow_metrics"

# Pramathus Configuration
export PRAMATHUS_ENDPOINT="https://your-pramathus.com/api/metrics"
export PRAMATHUS_API_KEY="your-secret-key"
export PRAMATHUS_ENABLED="true"

# Export Settings
export EXPORT_INTERVAL="60"  # seconds
export MAX_EXPERIMENTS="10"
```

### YAML Configuration

See `config.yaml` for detailed configuration options including:
- Endpoint URLs and authentication
- Export intervals and batch sizes
- Logging configuration
- Feature toggles

## 🐳 Docker Deployment

### Production Deployment

For production, update the `docker-compose.yml`:

1. **Use external MLflow**: Point to your existing MLflow server
2. **Configure persistent storage**: Update volume mounts
3. **Set resource limits**: Add memory and CPU constraints
4. **Enable SSL/TLS**: Configure secure connections
5. **Set up monitoring**: Add health checks and alerting

```yaml
# Example production overrides
mlflow-exporter:
  environment:
    - MLFLOW_TRACKING_URI=https://your-mlflow.company.com
    - PRAMATHUS_ENDPOINT=https://pramathus.company.com/api/v1/metrics
    - PRAMATHUS_API_KEY=${PRAMATHUS_API_KEY}
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '0.5'
```

### Scaling

To scale the exporter for high-volume environments:

```bash
# Scale the exporter service
docker-compose up -d --scale mlflow-exporter=3
```

## 📈 Grafana Dashboard Setup

### 1. Import Dashboard

1. Open Grafana at http://localhost:3000
2. Login with `admin` / `admin123`
3. Go to **Dashboards** → **Import**
4. Use the dashboard JSON from `grafana/dashboards/mlflow-dashboard.json`

### 2. Configure Data Source

Prometheus should be automatically configured. If not:

1. Go to **Configuration** → **Data Sources**
2. Add **Prometheus** data source
3. URL: `http://prometheus:9090`
4. Click **Save & Test**

### 3. Sample Queries

```promql
# Average accuracy across all experiments
avg(mlflow_accuracy)

# Model performance over time
rate(mlflow_accuracy[5m])

# Experiments by stage
count by (experiment_name) (mlflow_accuracy)
```

## 🔧 Local Development

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MLFLOW_TRACKING_URI="http://localhost:5000"
export PROMETHEUS_GATEWAY="localhost:9091"

# Run the exporter
python mlflow_monitoring_exporter.py continuous
```

### Testing

```bash
# Run one-time export
python mlflow_monitoring_exporter.py export-once

# Generate sample data
python mlflow_monitoring_exporter.py generate-sample

# Run in continuous mode
python mlflow_monitoring_exporter.py continuous
```

## 🔍 Troubleshooting

### Common Issues

**1. Pramathus Connection Failed**
```bash
# Check if endpoint is reachable
curl -X POST https://your-pramathus.com/api/metrics \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**2. No Metrics in Grafana**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check pushgateway metrics
curl http://localhost:9091/metrics
```

**3. MLflow Connection Issues**
```bash
# Verify MLflow is running
curl http://localhost:5000/api/2.0/mlflow/experiments/list
```

### Logs and Debugging

```bash
# View exporter logs
docker-compose logs -f mlflow-exporter

# Enable debug logging
docker-compose exec mlflow-exporter \
  python mlflow_monitoring_exporter.py export-once
```

## 📝 API Reference

### Pramathus Integration

If "Pramathus" is your custom monitoring system, ensure it accepts:

**Endpoint**: `POST /api/metrics`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer <api-key>
```

**Request Body**:
```json
{
  "timestamp": "ISO8601 timestamp",
  "source": "mlflow",
  "metrics": [
    {
      "name": "metric_name",
      "value": numeric_value,
      "timestamp": "ISO8601 timestamp",
      "metadata": {
        "run_id": "string",
        "experiment_name": "string",
        "step": number,
        "tags": {}
      }
    }
  ]
}
```

**Response**: 
- `200 OK` for success
- `4xx/5xx` for errors

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Issues**: Create a GitHub issue for bugs or feature requests
- **Documentation**: Check this README and inline code comments
- **Examples**: See the `examples/` directory for usage samples

## 🔮 Roadmap

- [ ] Advanced drift detection
- [ ] Model performance alerting
- [ ] Integration with more monitoring platforms
- [ ] Web UI for configuration
- [ ] Kubernetes Helm charts
- [ ] Advanced filtering and aggregation options

---

**Note**: Replace "Pramathus" configurations with your actual monitoring platform details. If Pramathus was a typo, update the configuration to point to your intended monitoring system (e.g., Datadog, New Relic, custom internal system, etc.).