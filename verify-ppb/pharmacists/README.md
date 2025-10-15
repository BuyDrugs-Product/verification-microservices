# PPB Pharmacist License Verification Microservice

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-blue)

A production-ready microservice for verifying Pharmacist licenses issued by the Kenya Pharmacy and Poisons Board (PPB). This service provides real-time verification of Pharmacist credentials by interfacing with the official PPB portal.

## Features

- **Real-time Verification**: Fetches current license information directly from the PPB portal
- **Complete Data Extraction**: Retrieves full name, license number, status, expiry date, and photo
- **Two-Step Workflow**: POST search followed by GET details for reliable data retrieval
- **Smart Caching**: In-memory LRU cache or Redis backend with configurable TTL
- **Rate Limiting**: Prevents IP blocking with configurable delays (default 1.5s)
- **Robust Error Handling**: Graceful handling of network issues, timeouts, and invalid licenses
- **Production Ready**: Docker support, health checks, structured logging, and monitoring

## Quick Start

### Prerequisites

- Python 3.10+
- pip
- (Optional) Redis for shared caching
- (Optional) Docker for containerized deployment

### Installation

```bash
# Clone the repository
cd verify-ppb/pharmacists

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # On GitBash: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env

# Edit .env with your settings
nano .env
```

### Running the Service

**Development Mode:**
```bash
# Method 1: Run as module (recommended)
python -m src.app

# Method 2: Simple entry point
python run.py
```

**Production Mode:**
```bash
# With Gunicorn
gunicorn -c gunicorn.conf.py src.app:app

# With Docker
docker-compose up -d
```

The service will be available at `http://localhost:5000`

## API Documentation

### Base URL
```
http://localhost:5000
```

### Endpoints

#### 1. Root Information
```http
GET /
```

Returns service information and available endpoints.

**Response:**
```json
{
  "service": "PPB Pharmacist License Verification Microservice",
  "version": "1.0.0",
  "description": "Verify Kenya PPB pharmacist licenses",
  "endpoints": {
    "info": "GET /",
    "health": "GET /health",
    "ready": "GET /ready",
    "verify": "POST /verify",
    "cache_stats": "GET /cache/stats",
    "cache_clear": "DELETE /cache"
  }
}
```

#### 2. Health Check
```http
GET /health
```

Returns service health status with cache statistics.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-10-15T12:00:00Z",
  "cache": {
    "cache_enabled": true,
    "backend": "simple",
    "size": 42,
    "hit_rate": 67.5
  }
}
```

#### 3. Verify Pharmacist License
```http
POST /verify
Content-Type: application/json
```

Verify a Pharmacist license number.

**Request:**
```json
{
  "license_number": "P2025D00463",
  "use_cache": true
}
```

**Successful Response (200):**
```json
{
  "success": true,
  "license_number": "P2025D00463",
  "message": "Pharmacist verification successful",
  "processing_time_ms": 920.50,
  "from_cache": false,
  "data": {
    "full_name": "Gesare Achei Beryl",
    "practice_license_number": "P2025D00463",
    "status": "Active",
    "valid_till": "2025-12-31",
    "photo_url": "http://rhris.pharmacyboardkenya.org/photos/931801f625947bc9eb0c05e85dad5a0d684893e320250117095315am.png",
    "verified_at": "2025-10-15T12:00:00Z"
  }
}
```

**Not Found Response (404):**
```json
{
  "success": false,
  "license_number": "P99999999",
  "message": "Pharmacist license 'P99999999' not found in registry",
  "processing_time_ms": 1200.50,
  "from_cache": false,
  "data": null
}
```

**Invalid Format Response (400):**
```json
{
  "success": false,
  "license_number": "INVALID123",
  "message": "Invalid license number format. Expected format: PYYYYXNNNNN",
  "processing_time_ms": 50.25,
  "from_cache": false,
  "data": null
}
```

#### 4. Cache Statistics
```http
GET /cache/stats
```

Returns cache performance metrics.

**Response:**
```json
{
  "cache_enabled": true,
  "backend": "simple",
  "size": 42,
  "max_size": 1000,
  "hits": 127,
  "misses": 53,
  "hit_rate": 70.56,
  "total_requests": 180
}
```

#### 5. Clear Cache
```http
DELETE /cache
```

Clears all cached verification results.

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared successfully"
}
```

## License Number Format

Pharmacist license numbers follow this format:
- **Prefix**: `P` (Pharmacist)
- **Year**: 4-digit year (2023-2029)
- **Category**: Single letter (A-Z)
- **Number**: 5 digits

**Examples:**
- `P2025D00463` - Valid
- `P2025D01204` - Valid
- `P2025D00268` - Valid

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Flask Configuration
FLASK_ENV=production
DEBUG=False
HOST=0.0.0.0
PORT=5000

# Request Configuration
REQUEST_TIMEOUT=15
MAX_RETRIES=2
RETRY_BACKOFF=0.3

# Rate Limiting (CRITICAL - prevents IP blocking)
RATE_LIMIT_DELAY=1.5

# Caching
CACHE_ENABLED=True
CACHE_BACKEND=simple  # 'simple' or 'redis'
CACHE_TTL=3600        # 1 hour
CACHE_MAX_SIZE=1000
REDIS_URL=redis://localhost:6379/1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # 'json' or 'text'
```

### Configuration Profiles

The service supports three configuration profiles:

1. **Development** (`FLASK_ENV=development`)
   - Debug mode enabled
   - Text logging format
   - 5-minute cache TTL
   - Verbose logging

2. **Production** (`FLASK_ENV=production`)
   - Debug mode disabled
   - JSON logging format
   - 2-hour cache TTL
   - Optimized for performance

3. **Testing** (`FLASK_ENV=testing`)
   - Cache disabled
   - Rate limiting disabled
   - Minimal logging

## Architecture

### Two-Step Verification Workflow

The service implements a reliable two-step verification process:

```
Client Request
     ↓
[STEP 1] POST Search
     ├─ Endpoint: /ajax/public
     ├─ Payload: {search_register: 1, cadre_id: 2, search_text: "P2025D00463"}
     └─ Extract: Encoded ID from HTML
     ↓
[Rate Limit] Wait 1.5s
     ↓
[STEP 2] GET Details
     ├─ Endpoint: /ajax/public?search_details=get&id={encoded_id}
     ├─ Headers: XMLHttpRequest, proper referer
     └─ Extract: Full name, status, photo, expiry
     ↓
[Parse & Cache]
     ↓
Return JSON Response
```

### Project Structure

```
pharmacists/
├── src/
│   ├── core/                 # Configuration, logging, versioning
│   │   ├── config.py
│   │   ├── logger.py
│   │   └── version.py
│   ├── adapters/             # External integrations
│   │   ├── http.py           # HTTP client with retries
│   │   ├── cache_simple.py   # In-memory LRU cache
│   │   └── cache_redis.py    # Redis cache adapter
│   ├── services/             # Business logic
│   │   └── ppb_service.py    # Pharmacist verification engine
│   ├── models/               # Request/response schemas
│   │   └── schemas.py
│   ├── api/                  # Flask routes & error handling
│   │   ├── routes.py
│   │   └── errors.py
│   └── app.py                # Application factory
├── tests/                    # Test files
│   ├── conftest.py           # Test configuration and fixtures
│   └── test_direct.py        # Main test runner
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── gunicorn.conf.py
└── README.md
```

## Testing

### Quick Start Testing

Ensure you are in the correct directory and virtual environment is activated:

```bash
.venv\Scripts\activate
cd verify-ppb/pharmacists
```
Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the complete test suite with one command:

```bash
python tests/test_direct.py
```

Expected output:
```
🧪 PHARMACIST VERIFICATION TEST SUITE
======================================================================

1. TESTING VALID LICENSE VERIFICATION
======================================================================
   ✅ Gesare Achei Beryl - Active license with photo: PASSED (920.50ms)
   ℹ️  Name: Gesare Achei Beryl
   ℹ️  Status: Active until 2025-12-31
   ✅ Ismael Zubeidah Rashid - Active license with photo: PASSED (1026.97ms)
   ℹ️  Name: Ismael Zubeidah Rashid
   ℹ️  Status: Active until 2025-12-31
   ✅ Otieno Winston Churchill - Active license with photo: PASSED (1113.67ms)
   ℹ️  Name: Otieno Winston Churchill
   ℹ️  Status: Active until 2025-12-31

2. TESTING ERROR HANDLING
======================================================================
   ✅ Non-existent license number: Correctly handled
   ✅ Malformed license - invalid format: Correctly handled
   ✅ Malformed license - too short: Correctly handled
   ✅ Malformed license - invalid year: Correctly handled

3. TESTING PERFORMANCE
======================================================================
   ℹ️  Performance threshold: 3.0s per request
   ✅ All requests completed within threshold

4. TESTING CACHE FUNCTIONALITY
======================================================================
   ✅ First request (uncached): 675.52ms
   ✅ Second request (cached): 0.00ms (0.0x faster)
   ℹ️  Cache size: 1
   ℹ️  Cache hit rate: 50.0%

📊 TEST SUMMARY
======================================================================

   Tests Passed: 11
   Tests Failed: 0
   Total Tests:  11
   Total Time:   6.84s
   Average Time: 919.23ms

🎉 ALL TESTS PASSED!
```

### Test Data

The test suite uses **real Pharmacist licenses** from the PPB portal:

| License Number | Name | Status | Photo |
|----------------|------|--------|-------|
| P2025D00463 | Gesare Achei Beryl | Active | ✅ |
| P2025D01204 | Ismael Zubeidah Rashid | Active | ✅ |
| P2025D00268 | Otieno Winston Churchill | Active | ✅ |

### Test Categories

The test suite includes:

#### 1. Valid License Verification
- Complete data extraction (name, license, status, expiry, photo)
- Multiple real license examples
- Data type validation
- Date format validation
- Photo URL accessibility

#### 2. Error Handling
- Non-existent license numbers
- Invalid format detection
- Empty/None inputs
- License format validation
- Proper error messages

#### 3. Performance Tests
- Response time benchmarks (< 3 seconds uncached)
- Average response time tracking
- Consecutive request handling

#### 4. Cache Functionality
- Cache hit/miss tracking
- Cache statistics accuracy
- Cache speed improvements
- Data integrity

### Performance

- **Uncached verification**: 0.9-1.2 seconds
- **Cached verification**: < 1ms (instant from memory)
- **Expected cache hit rate**: > 50% with repeated requests
- **Success rate**: 100% for valid licenses

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t ppb-pharmacist-verification:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f ppb-pharmacist-verification

# Stop services
docker-compose down
```

### Production Considerations

1. **Environment Variables**: Set all required environment variables
2. **Redis**: Use Redis for shared caching across multiple workers
3. **Reverse Proxy**: Deploy behind nginx or similar for SSL/TLS
4. **Monitoring**: Enable structured JSON logging for log aggregation
5. **Health Checks**: Use `/health` and `/ready` endpoints for orchestration
6. **Rate Limiting**: Keep default 1.5s delay to prevent IP blocking

## Troubleshooting

### Common Issues

**1. "Pharmacist license not found"**
- Verify the license number format (PYYYYXNNNNN)
- Check if the license exists in the PPB registry
- Ensure the PPB portal is accessible

**2. Slow response times**
- Check cache hit rate: `curl http://localhost:5000/cache/stats`
- Verify network connectivity to PPB portal
- Consider enabling Redis for faster caching

**3. Rate limiting / IP blocking**
- Ensure `RATE_LIMIT_DELAY` is set to at least 1.5 seconds
- Don't make rapid sequential requests
- Use caching to reduce PPB portal requests

**4. Connection timeouts**
- Increase `REQUEST_TIMEOUT` if needed
- Check PPB portal availability
- Review network/firewall settings

## API Usage Examples

### cURL

```bash
# Verify a license
curl -X POST http://localhost:5000/verify \
  -H "Content-Type: application/json" \
  -d '{"license_number": "P2025D00463"}'

# Health check
curl http://localhost:5000/health

# Cache statistics
curl http://localhost:5000/cache/stats

# Clear cache
curl -X DELETE http://localhost:5000/cache
```

### Python

```python
import requests

# Verify a Pharmacist license
response = requests.post(
    "http://localhost:5000/verify",
    json={"license_number": "P2025D00463"}
)

if response.status_code == 200:
    data = response.json()
    if data["success"]:
        print(f"Pharmacist: {data['data']['full_name']}")
        print(f"Status: {data['data']['status']}")
        print(f"Valid Until: {data['data']['valid_till']}")
    else:
        print(f"Error: {data['message']}")
```

### JavaScript

```javascript
// Verify a Pharmacist license
fetch('http://localhost:5000/verify', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ license_number: 'P2025D00463' })
})
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      console.log(`Pharmacist: ${data.data.full_name}`);
      console.log(`Status: ${data.data.status}`);
    } else {
      console.log(`Error: ${data.message}`);
    }
  });
```

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue in the repository
- Contact the development team
- Review the parent CLAUDE.md file for detailed technical documentation

## Changelog

### Version 1.0.0 (2025-10-15)
- Initial release
- Two-step verification workflow (POST search + GET details)
- Complete data extraction (name, license, status, expiry, photo)
- Smart caching (LRU or Redis)
- Rate limiting to prevent IP blocking
- Docker support
- Comprehensive test suite with real pharmacist data
- Production-ready deployment configuration
