# PPB Facilities License Verification

Production-ready microservice for verifying Kenya Pharmacy and Poisons Board (PPB) **facility licenses**.

[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](CHANGELOG.md)

## Quick Start

```bash
# Docker (recommended)
docker-compose up -d

# Local development
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # On GitBash: source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Run the service (choose one):
python -m src.app     # Recommended: Run as module
python run.py         # Alternative: Simple entry point
```

Service: http://localhost:5000

## What It Does

Verifies **PPB facility licenses** (pharmacies, hospitals, wholesalers, manufacturers) by extracting:

- ✅ **10 facility fields**: name, license number, status, location, ownership, type, establishment year, etc.
- ✅ **3 superintendent fields**: name, professional cadre, enrollment number
- ✅ **100% data completeness** with <100ms response (cached), 2-4s (uncached)
- ✅ Production-grade: Auto-retries, connection pooling, structured logging
- ✅ Docker & Kubernetes ready

**Scope:** This service handles **facility licenses only**. 

For other PPB verifications, use:
- `verify-ppb-pharmacists` - For pharmacist license verification
- `verify-ppb-pharmtechs` - For pharmaceutical technologist verification

## API

### Verify Facility License
```bash
curl -X POST http://localhost:5000/verify \
  -H "Content-Type: application/json" \
  -d '{"ppb_number":"PPB/C/9222"}'
```

**Response:**
```json
{
  "success": true,
  "ppb_number": "PPB/C/9222",
  "processing_time_ms": 3200.45,
  "data": {
    "facility_name": "CARING-WAY PHARMA (Kiambu)",
    "license_number": "BU202511914",
    "license_status": "VALID",
    "license_type": "RETAIL",
    "superintendent": {
      "name": "KIVUVA",
      "cadre": "PHARMTECH",
      "enrollment_number": "12832"
    }
  }
}
```

### Other Endpoints
- `GET /health` - Health check
- `GET /ready` - Readiness probe  
- `GET /cache/stats` - Cache statistics
- `DELETE /cache` - Clear cache

## Development

### Setup
```bash
make setup              # Complete setup
python -m src.app       # Run server (or: python run.py)
```

### Testing
```bash
python tests/test_superintendent_fix.py  # Critical test (must pass)
python tests/test_direct.py              # Full test
pytest                                  # All tests
```

### Commands
```bash
make dev         # Development server
make test        # Run tests
make lint        # Run linters  
make format      # Format code
make docker-up   # Start Docker
```

## Configuration

Edit `.env`:
```bash
FLASK_ENV=production
CACHE_BACKEND=redis              # or 'simple'
REDIS_URL=redis://localhost:6379/0
LOG_FORMAT=json
RATE_LIMIT_DELAY=1.5             # CRITICAL: prevents IP blocking
```

## Deployment

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ppb-facilities-verification
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: ppb-facilities
        image: ppb-facilities-verification:1.0.0
        ports:
        - containerPort: 5000
        env:
        - name: FLASK_ENV
          value: "production"
        - name: CACHE_BACKEND
          value: "redis"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
```

### Gunicorn
```bash
gunicorn -c gunicorn.conf.py src.app:app
```

## Project Structure

```
src/                            # Main application package
├── core/                       # Config, logging, version
├── api/                        # Routes, errors, blueprints
├── services/                   # Business logic (PPB service)
├── adapters/                   # HTTP client, caching
└── models/                     # Request/response schemas
```

## Critical Implementation Notes

⚠️ **Do Not Modify Without Testing:**

1. **Rate Limiting (1.5s)**: Tested value that prevents IP blocking from PPB portal
2. **HTTP Headers**: PPB portal validates these strictly - breaking changes will fail requests
3. **Superintendent Extraction**: Complex 3-tier regex - always test with `python tests/test_superintendent_fix.py`
4. **Session Management**: Cookies must persist between the two-step verification workflow

See [CLAUDE.md](CLAUDE.md) for detailed architecture and critical implementation paths.

## Contributing

```bash
# 1. Setup
make setup

# 2. Create branch
git checkout -b feature/name

# 3. Make changes & test
make format && make lint && make test

# 4. Commit & push
git commit -m "feat: description"
git push origin feature/name
```

**Code Style:**
- Format: Black (100 chars)
- Imports: isort
- Linting: flake8, mypy
- Tests: pytest (>80% coverage)

## Troubleshooting

**Tests failing:**
```bash
pip install -r requirements.txt -r requirements-dev.txt
python tests/test_superintendent_fix.py
```

**Import errors:**
```bash
source venv/bin/activate
pip install -e .
```

**Docker issues:**
```bash
docker-compose down -v
docker-compose up -d --build
```

## Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Data Complete | 100% | ✅ 13/13 |
| Response (cached) | <100ms | ✅ |
| Response (uncached) | <5s | ✅ 2.5-4.5s |
| Success Rate | >95% | ✅ |

## Documentation

- **README.md** - This file (complete guide)
- **[CHANGELOG.md](CHANGELOG.md)** - Version history & migration
- **[CLAUDE.md](CLAUDE.md)** - Architecture & critical implementation details

## License

MIT License

---

**v1.0.0** | Facilities Verification Only | Python 3.11+
