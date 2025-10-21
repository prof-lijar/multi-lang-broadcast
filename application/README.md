# Multi-Language Broadcast API

A FastAPI application for live translation and multi-language broadcasting.

## Features

- **Health Check Endpoints**: Monitor application status
- **CORS Support**: Cross-origin resource sharing enabled
- **Auto Documentation**: Interactive API docs at `/docs`
- **Environment Configuration**: Configurable via environment variables
- **Scalable Architecture**: Ready for production deployment

## Quick Start

### 1. Install Dependencies

```bash
cd application
pip install -r requirements.txt
```

### 2. Run the Application

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test the API

The application will be available at `http://localhost:8000`

- **Root endpoint**: `GET /`
- **Health check**: `GET /health`
- **Detailed health**: `GET /health/detailed`
- **API Documentation**: `GET /docs`

## API Endpoints

### Health Endpoints

#### `GET /`
Returns basic API information and status.

**Response:**
```json
{
  "message": "Multi-Language Broadcast API",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "docs": "/docs"
}
```

#### `GET /health`
Simple health check for monitoring and load balancers.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "service": "multi-lang-broadcast",
  "version": "1.0.0"
}
```

#### `GET /health/detailed`
Detailed health check with system information.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "service": "multi-lang-broadcast",
  "version": "1.0.0",
  "environment": "development",
  "python_version": "3.11.0",
  "uptime": "N/A"
}
```

## Configuration

The application can be configured using environment variables:

```bash
# Server configuration
export HOST=0.0.0.0
export PORT=8000
export DEBUG=true

# Environment
export ENVIRONMENT=development
```

## Development

### Project Structure

```
application/
├── main.py              # FastAPI application entry point
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Adding New Endpoints

1. Import your router in `main.py`
2. Include the router with `app.include_router()`
3. Follow FastAPI best practices for route organization

## Production Deployment

### Using Docker (Recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Monitoring

The health endpoints are designed for:
- Load balancer health checks
- Kubernetes liveness/readiness probes
- Application monitoring systems
- CI/CD pipeline health verification

## Next Steps

This is a minimal setup. Future enhancements could include:

- Authentication and authorization
- Database integration
- Redis caching
- WebSocket support for real-time features
- Comprehensive logging
- Metrics and monitoring
- API rate limiting
- Input validation schemas
