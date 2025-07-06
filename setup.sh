#!/bin/bash

# MLflow Monitoring Stack Setup Script
# ====================================

set -e

echo "🚀 Setting up MLflow Monitoring Stack..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directory structure..."
mkdir -p grafana/dashboards grafana/datasources pramathus-mock/html

# Create Grafana datasource configuration
echo "📊 Setting up Grafana datasources..."
cat > grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Create a basic Grafana dashboard
echo "📈 Setting up Grafana dashboard..."
cat > grafana/dashboards/dashboard.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Create MLflow dashboard JSON
cat > grafana/dashboards/mlflow-dashboard.json << 'EOF'
{
  "annotations": {
    "list": []
  },
  "description": "MLflow Metrics Monitoring Dashboard",
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "vis": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "off"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          },
          "unit": "percent"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      },
      "targets": [
        {
          "expr": "mlflow_accuracy",
          "interval": "",
          "legendFormat": "{{experiment_name}} - {{run_id}}",
          "refId": "A"
        }
      ],
      "title": "Model Accuracy",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "vis": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "off"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          }
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      },
      "targets": [
        {
          "expr": "mlflow_loss",
          "interval": "",
          "legendFormat": "{{experiment_name}} - {{run_id}}",
          "refId": "A"
        }
      ],
      "title": "Model Loss",
      "type": "timeseries"
    }
  ],
  "refresh": "5s",
  "schemaVersion": 27,
  "style": "dark",
  "tags": ["mlflow", "monitoring"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "MLflow Metrics Dashboard",
  "uid": "mlflow-dashboard",
  "version": 1
}
EOF

# Create mock Pramathus service configuration
echo "🔧 Setting up mock Pramathus service..."
mkdir -p pramathus-mock/html
cat > pramathus-mock/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    server {
        listen 80;
        server_name localhost;
        
        location /api/metrics {
            add_header Content-Type application/json;
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "POST, GET, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization";
            
            if (\$request_method = 'OPTIONS') {
                return 204;
            }
            
            return 200 '{"status": "success", "message": "Metrics received"}';
        }
        
        location / {
            root /usr/share/nginx/html;
            index index.html;
        }
    }
}
EOF

cat > pramathus-mock/html/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Pramathus Mock Service</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { padding: 20px; background: #e7f5e7; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Pramathus Mock Service</h1>
        <div class="status">
            <h3>Service Status: ✅ Online</h3>
            <p>This is a mock service that simulates the Pramathus monitoring platform.</p>
            <p><strong>Endpoint:</strong> <code>POST /api/metrics</code></p>
            <p><strong>Response:</strong> Always returns <code>200 OK</code></p>
        </div>
        
        <h3>📊 Received Metrics</h3>
        <p>This mock service accepts all metric data and responds with success. 
           In production, replace this with your actual Pramathus endpoint.</p>
           
        <h3>🔧 Configuration</h3>
        <p>Update the <code>PRAMATHUS_ENDPOINT</code> environment variable to point to your real monitoring system.</p>
    </div>
</body>
</html>
EOF

# Set up environment file
echo "🔐 Creating environment configuration..."
cat > .env << EOF
# MLflow Configuration
MLFLOW_TRACKING_URI=http://mlflow:5000

# Prometheus Configuration
PROMETHEUS_GATEWAY=pushgateway:9091
PROMETHEUS_JOB_NAME=mlflow_metrics

# Pramathus Configuration (update with your real endpoint)
PRAMATHUS_ENDPOINT=http://pramathus-mock:80/api/metrics
PRAMATHUS_API_KEY=your-api-key-here
PRAMATHUS_ENABLED=true

# Export Configuration
EXPORT_INTERVAL=30
MAX_EXPERIMENTS=10
INCLUDE_SYSTEM_METRICS=true
EOF

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose build
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
services=("mlflow:5000" "grafana:3000" "prometheus:9090" "pushgateway:9091")
for service in "${services[@]}"; do
    if curl -sf "http://localhost:${service#*:}" > /dev/null 2>&1; then
        echo "✅ ${service%:*} is running"
    else
        echo "⚠️  ${service%:*} might not be ready yet"
    fi
done

# Generate sample data
echo "📊 Generating sample MLflow data..."
docker-compose exec -T mlflow-exporter python mlflow_monitoring_exporter.py generate-sample

# Export metrics once
echo "📤 Running initial metrics export..."
docker-compose exec -T mlflow-exporter python mlflow_monitoring_exporter.py export-once

echo ""
echo "🎉 Setup complete! Access your services:"
echo ""
echo "📈 MLflow UI:        http://localhost:5000"
echo "📊 Grafana:          http://localhost:3000 (admin/admin123)"
echo "🔍 Prometheus:       http://localhost:9090"
echo "📤 Push Gateway:     http://localhost:9091"
echo "🎯 Pramathus Mock:   http://localhost:8080"
echo ""
echo "📝 Logs: docker-compose logs -f mlflow-exporter"
echo "🛑 Stop: docker-compose down"
echo ""
echo "✨ Your MLflow monitoring stack is ready!"
EOF