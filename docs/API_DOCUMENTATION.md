# AI Agent 3D Print System - API Documentation

## Overview

The AI Agent 3D Print System provides a comprehensive REST API and WebSocket interface for converting natural language descriptions into 3D printed objects. The system orchestrates multiple AI agents to handle research, CAD modeling, slicing, and printing operations.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Authentication

Currently, the API supports optional authentication modes:

- **API Key**: Set `X-API-Key` header (configurable in production)
- **JWT**: Bearer token authentication (configurable in production)
- **Development**: No authentication required

## API Endpoints

### 1. Print Request Management

#### POST /api/print-request

Start a new 3D print workflow from natural language description.

**Request Body:**
```json
{
  "user_request": "Create a phone case for iPhone 14 with a dragon design",
  "user_id": "user123",
  "printer_profile": "ender3_pla",
  "quality_level": "standard",
  "metadata": {
    "priority": "normal",
    "email_notification": true
  }
}
```

**Response:**
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "pending",
  "progress_percentage": 0.0,
  "current_step": "Initializing workflow",
  "message": "Print request received and queued for processing",
  "created_at": "2025-06-11T10:30:00Z",
  "updated_at": "2025-06-11T10:30:00Z"
}
```

**Status Codes:**
- `201 Created`: Request accepted and workflow started
- `400 Bad Request`: Invalid request parameters
- `500 Internal Server Error`: System error

#### GET /api/status/{job_id}

Get current status and progress of a print job.

**Response:**
```json
{
  "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "running",
  "progress_percentage": 45.0,
  "current_step": "3D model creation",
  "message": "Generating CAD model from specifications",
  "created_at": "2025-06-11T10:30:00Z",
  "updated_at": "2025-06-11T10:35:00Z",
  "estimated_completion": "2025-06-11T11:00:00Z",
  "error_message": null,
  "output_files": {
    "stl": "/api/files/f47ac10b.stl"
  }
}
```

**Status Values:**
- `pending`: Workflow queued but not started
- `running`: Workflow actively processing
- `completed`: Workflow finished successfully
- `failed`: Workflow encountered an error
- `cancelled`: Workflow cancelled by user

#### GET /api/workflows

List all workflows with filtering and pagination.

**Query Parameters:**
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)
- `status_filter`: Filter by status (optional)

**Response:**
```json
[
  {
    "job_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "status": "completed",
    "progress_percentage": 100.0,
    "current_step": "Completed",
    "message": "Workflow completed successfully",
    "created_at": "2025-06-11T10:30:00Z",
    "updated_at": "2025-06-11T10:45:00Z"
  }
]
```

#### DELETE /api/workflows/{job_id}

Cancel a running workflow.

**Response:**
- `204 No Content`: Workflow cancelled successfully
- `400 Bad Request`: Cannot cancel workflow in current state
- `404 Not Found`: Workflow not found

### 2. System Health and Monitoring

#### GET /health

Get basic system health status and metrics.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600.0,
  "active_workflows": 2,
  "total_completed": 15,
  "agents_status": {
    "parent": "running",
    "research": "idle",
    "cad": "idle",
    "slicer": "idle",
    "printer": "idle"
  },
  "system_metrics": {
    "cpu_usage_percent": 25.5,
    "memory_usage_percent": 45.2,
    "disk_usage_percent": 12.8,
    "active_connections": 5,
    "load_average": 1.2,
    "active_threads": 12
  }
}
```

#### GET /health/detailed

Get comprehensive health information for all system components.

**Response:**
```json
{
  "overall_status": "healthy",
  "timestamp": "2025-06-11T10:30:00Z",
  "system_metrics": {
    "cpu_usage_percent": 25.5,
    "memory_usage_percent": 45.2,
    "disk_usage_percent": 12.8,
    "load_average": 1.2,
    "uptime_seconds": 3600.0,
    "network_connections": 10,
    "active_threads": 12
  },
  "components": {
    "api": {
      "name": "api",
      "status": "healthy",
      "last_check": "2025-06-11T10:30:00Z",
      "response_time_ms": 5.2,
      "error_message": null,
      "metrics": null
    },
    "database": {
      "name": "database",
      "status": "healthy",
      "last_check": "2025-06-11T10:30:00Z",
      "response_time_ms": 12.1,
      "error_message": null,
      "metrics": null
    }
  }
}
```

#### GET /health/components/{component_name}

Get health status for a specific component.

**Component Names:**
- `api`: API server health
- `database`: Database connectivity
- `redis`: Redis cache (if enabled)
- `file_system`: File system and disk space
- `research_agent`: Research agent health
- `cad_agent`: CAD agent health
- `slicer_agent`: Slicer agent health
- `printer_agent`: Printer agent health

**Response:**
```json
{
  "component": "research_agent",
  "status": "healthy",
  "last_check": "2025-06-11T10:30:00Z",
  "response_time_ms": 15.3,
  "error_message": null,
  "metrics": {
    "requests_processed": 45,
    "average_response_time": 12.5,
    "cache_hit_rate": 0.85
  }
}
```

### 3. File Management

#### GET /api/files/{filename}

Download generated files (STL, G-code, etc.).

**Response:**
- File content with appropriate MIME type
- `404 Not Found`: File not found

## WebSocket API

### /ws/progress

Real-time progress updates for workflows.

**Connection URL:**
- General updates: `ws://localhost:8000/ws/progress`
- Specific job: `ws://localhost:8000/ws/progress?job_id={job_id}`

**Message Types:**

#### Status Update
```json
{
  "type": "status_update",
  "workflow_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "status": "running",
  "message": "Starting CAD model generation",
  "timestamp": "2025-06-11T10:32:00Z"
}
```

#### Progress Update
```json
{
  "type": "progress_update",
  "workflow_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "progress_percentage": 35.0,
  "current_step": "3D model creation",
  "message": "Generating geometry for phone case...",
  "timestamp": "2025-06-11T10:33:00Z"
}
```

#### Error Notification
```json
{
  "type": "error",
  "workflow_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "error_message": "CAD generation failed: Invalid geometry",
  "timestamp": "2025-06-11T10:35:00Z"
}
```

#### Client Messages

**Ping/Pong (Keep-alive):**
```json
{
  "type": "ping"
}
```

Response:
```json
{
  "type": "pong",
  "timestamp": "2025-06-11T10:30:00Z"
}
```

## Error Responses

All API endpoints return structured error responses:

```json
{
  "error": "validation_error",
  "message": "user_request field is required",
  "details": {
    "field": "user_request",
    "code": "missing"
  }
}
```

**Error Types:**
- `validation_error`: Request validation failed
- `agent_execution_error`: Agent processing error
- `workflow_error`: Workflow orchestration error
- `printer_error`: Printer communication error
- `internal_server_error`: Unexpected system error

## Rate Limiting

The API implements rate limiting based on configuration:

- **Development**: 60 requests per minute
- **Production**: 100 requests per minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when window resets

## Configuration

### Environment Variables

Production deployments should use environment variables:

```bash
# Application
APP_ENVIRONMENT=production
APP_DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql://user:pass@localhost/ai_3d_print

# Cache
REDIS_URL=redis://localhost:6379/0

# Security
JWT_SECRET=your-jwt-secret-key
API_KEY=your-api-key

# Hardware
PRINTER_PORT=/dev/ttyUSB0
SLICER_PATH=/usr/bin/prusa-slicer

# Monitoring
PROMETHEUS_ENABLED=true
ALERT_WEBHOOK_URL=https://hooks.slack.com/your-webhook
```

### Printer Profiles

Available printer profiles:

- `ender3_pla`: Ender 3 with PLA filament
- `prusa_mk3_petg`: Prusa MK3S with PETG filament
- `generic_abs`: Generic printer with ABS filament

### Quality Levels

- `draft`: Fast printing, lower quality
- `standard`: Balanced speed and quality
- `fine`: High quality, slower printing
- `ultra`: Maximum quality, very slow

## SDK Examples

### Python

```python
import asyncio
import aiohttp
import json

class AI3DPrintClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    async def start_print(self, user_request, printer_profile="ender3_pla"):
        async with aiohttp.ClientSession() as session:
            data = {
                "user_request": user_request,
                "printer_profile": printer_profile,
                "quality_level": "standard"
            }
            async with session.post(f"{self.base_url}/api/print-request", 
                                  json=data) as response:
                return await response.json()
    
    async def get_status(self, job_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/status/{job_id}") as response:
                return await response.json()

# Usage
client = AI3DPrintClient()
result = await client.start_print("Create a small vase with spiral pattern")
print(f"Job ID: {result['job_id']}")
```

### JavaScript

```javascript
class AI3DPrintClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async startPrint(userRequest, printerProfile = 'ender3_pla') {
        const response = await fetch(`${this.baseUrl}/api/print-request`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_request: userRequest,
                printer_profile: printerProfile,
                quality_level: 'standard'
            })
        });
        return await response.json();
    }
    
    async getStatus(jobId) {
        const response = await fetch(`${this.baseUrl}/api/status/${jobId}`);
        return await response.json();
    }
    
    connectWebSocket(jobId, onMessage) {
        const ws = new WebSocket(`ws://localhost:8000/ws/progress?job_id=${jobId}`);
        ws.onmessage = (event) => onMessage(JSON.parse(event.data));
        return ws;
    }
}

// Usage
const client = new AI3DPrintClient();
const result = await client.startPrint("Create a smartphone stand");
console.log(`Job ID: ${result.job_id}`);

// Connect to WebSocket for real-time updates
const ws = client.connectWebSocket(result.job_id, (message) => {
    console.log('Progress update:', message);
});
```

## Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "start_api_production.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-3d-print-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-3d-print-api
  template:
    metadata:
      labels:
        app: ai-3d-print-api
    spec:
      containers:
      - name: api
        image: ai-3d-print:latest
        ports:
        - containerPort: 8000
        env:
        - name: APP_ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
```

### Load Balancer Configuration

```nginx
upstream ai_3d_print {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name api.your-domain.com;
    
    location / {
        proxy_pass http://ai_3d_print;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws/ {
        proxy_pass http://ai_3d_print;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Monitoring and Alerting

### Prometheus Metrics

When enabled, the system exposes metrics at `/metrics`:

- `api_requests_total`: Total API requests
- `workflow_duration_seconds`: Workflow execution time
- `agent_execution_duration_seconds`: Individual agent execution time
- `system_cpu_usage`: CPU usage percentage
- `system_memory_usage`: Memory usage percentage
- `active_workflows`: Number of active workflows

### Health Check Integration

Health endpoints can be integrated with monitoring systems:

```bash
# Kubernetes liveness probe
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Kubernetes readiness probe
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

## Support and Troubleshooting

### Common Issues

1. **Agent Initialization Failure**
   - Check system dependencies (FreeCAD, PrusaSlicer)
   - Verify configuration files
   - Check log files in `/logs` directory

2. **WebSocket Connection Issues**
   - Verify CORS configuration
   - Check firewall settings
   - Enable WebSocket debugging

3. **Performance Issues**
   - Monitor system metrics via `/health/detailed`
   - Check disk space and memory usage
   - Consider scaling workers

### Log Analysis

Log files are structured JSON for easy parsing:

```bash
# Filter errors
grep '"level":"ERROR"' logs/api.log

# Monitor workflow progress
grep '"workflow_id":"f47ac10b"' logs/api.log

# Agent-specific logs
tail -f logs/cad_agent.log
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
export APP_DEBUG=true
export LOG_LEVEL=DEBUG
python start_api_server.py
```
