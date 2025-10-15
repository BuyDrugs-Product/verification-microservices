# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a **monorepo** for PPB (Kenya Pharmacy and Poisons Board) verification microservices:

```
verify-ppb/                    # Parent folder for all PPB services
├── facilities/                # Facility license verification
├── pharmacists/              # (Future) Pharmacist license verification
└── pharmtechs/               # (Future) Pharmtech license verification
```

**Current Services:**
- **facilities**: Production-ready facility license verification microservice

## Common Commands

### PPB Facilities License Verification Service

**Development:**
```bash
cd verify-ppb/facilities
python -m src.app       # Run as module (recommended)
# OR
python run.py           # Simple entry point
```

**Testing:**
```bash
# Quick superintendent extraction validation (most critical component)
python tests/test_superintendent_fix.py

# Full service test without Flask
python tests/test_direct.py

# Complete API integration tests (requires server running)
python tests/test_verification.py
```

**Manual API Testing:**
```bash
# Verify a license
curl -X POST http://localhost:5000/verify \
  -H "Content-Type: application/json" \
  -d '{"ppb_number": "PPB/C/9222"}'

# Health check with cache stats
curl http://localhost:5000/health

# Cache statistics
curl http://localhost:5000/cache/stats

# Clear cache
curl -X DELETE http://localhost:5000/cache
```

**Production Deployment:**
```bash
# With Gunicorn (recommended)
gunicorn -c gunicorn.conf.py src.app:app

# With Docker
docker-compose up -d
```

## Architecture

### PPB Facilities License Verification Service (verify-ppb/facilities/)

This microservice performs automated facility license verification by scraping the PPB portal. Understanding the data flow is critical when making modifications.

#### Project Structure

```
facilities/
├── src/                              # Main application package
│   ├── core/                         # Config, logging, version
│   │   ├── config.py                 # Environment-based config
│   │   ├── logger.py                 # Structured logging (JSON/text)
│   │   └── version.py                # Version info
│   ├── api/                          # Flask routes & error handling
│   │   ├── routes.py                 # API endpoints (verify, health, cache)
│   │   └── errors.py                 # Centralized error handlers
│   ├── services/                     # Business logic
│   │   └── ppb_service.py           # PPB verification engine
│   ├── adapters/                     # External integrations
│   │   ├── http.py                   # HTTP client with retries
│   │   ├── cache_simple.py          # In-memory LRU cache
│   │   └── cache_redis.py           # Redis cache adapter
│   └── models/                       # Request/response schemas
│       └── schemas.py                # Pydantic models
├── tests/                            # Test files
│   ├── test_superintendent_fix.py
│   ├── test_direct.py
│   └── test_verification.py
├── requirements.txt                  # Production dependencies
├── requirements-dev.txt              # Development dependencies
├── Dockerfile                        # Production container
├── docker-compose.yml               # Local development
└── gunicorn.conf.py                 # Production WSGI config
```

#### Core Components

1. **PPBService (src/services/ppb_service.py)** - Main verification engine
2. **Flask API (src/app.py)** - Application factory with blueprints
3. **Cache Adapters (src/adapters/cache_*.py)** - Simple LRU or Redis
4. **Config (src/core/config.py)** - Environment-based configuration

#### Critical Two-Step Verification Workflow

The service must perform verification in exactly this sequence:

**STEP 1: Search for Facility**
- POST to `/ajax/public?fetch=facilities&search={ppb_number}`
- Uses `search_headers` with XMLHttpRequest headers
- Extract facility ID from response (base64-encoded string like "Mjc2ODk=")
- ID is found in column 4 of search results via regex: `rel='([^']+)'`

**STEP 2: Get Detailed Information**
- GET `/ajax/public?search_details=facility&id={facility_id}`
- **CRITICAL**: Must use `details_headers` (different from search headers)
- Must maintain session cookies from Step 1
- Rate limit: 1.5s delay between requests (prevents IP blocking)
- Returns HTML containing all facility details

**STEP 3: Parse HTML and Extract Data**
- Extract 10 basic fields using regex patterns
- Extract 3 superintendent fields from **HTML comments**

#### Superintendent Extraction - Most Complex Component

Superintendent data is stored in HTML comments in the response:
```html
<!--<a class="list-group-item text-boldest" >
    Superintendent : KELVIN KIPCHIRCHIR                     <br />
    Cadre: PHARMTECH                    <br />
    Enrollment Number: 10858                    </a>-->
```

The extraction uses a **three-tier fallback strategy** in `src/services/ppb_service.py`:

1. **Primary pattern**: Exact HTML comment structure match (most reliable)
2. **Fallback 1**: Flexible pattern matching anywhere in HTML (works without comments)
3. **Fallback 2**: Find comment section first, then extract individual fields

**When modifying superintendent extraction:**
- Test with `python tests/test_superintendent_fix.py` (must pass 4/4 tests)
- All three patterns must be maintained for reliability
- Never remove the multi-line regex flags (re.DOTALL | re.IGNORECASE)

#### Session Management

The service maintains a `requests.Session()` object that:
- Preserves cookies between the two-step workflow
- Is reused across all verification requests
- **Must not be recreated** between Step 1 and Step 2

#### Rate Limiting

Implements a `RateLimiter` class with 1.5s delay:
- Prevents IP blocking by the PPB portal
- Applied before each request to PPB
- **Critical**: Increasing delay reduces blocking risk; decreasing increases blocking risk

#### Headers

Two distinct header sets are required:

**search_headers**: For facility search (Step 1)
- Accept: `application/json, text/javascript, */*`
- X-Requested-With: XMLHttpRequest

**details_headers**: For facility details (Step 2)
- Accept: `text/html, */*`
- X-Requested-With: XMLHttpRequest
- Additional security headers (sec-ch-ua, Sec-Fetch-*)

**Never modify headers without testing** - PPB portal is strict about request format.

#### Caching Strategy

- Thread-safe LRU cache with TTL expiration
- Cache key format: `detailed:{ppb_number}`
- Default TTL: 3600s (dev), 7200s (prod)
- Tracks hits/misses/evictions
- Cache can be bypassed via `use_cache: false` in API request

### Data Flow Diagram

```
Client → POST /verify {"ppb_number": "PPB/C/9222"}
         ↓
    [Check Cache] → HIT? Return cached (< 100ms)
         ↓ MISS
    [STEP 1] Search PPB Portal
         ├─ GET /ajax/public?fetch=facilities&search=PPB/C/9222
         └─ Extract facility_id from response
         ↓
    [Rate Limit Wait] 1.5s delay
         ↓
    [STEP 2] Get Details
         ├─ GET /ajax/public?search_details=facility&id={facility_id}
         ├─ Use details_headers (critical!)
         └─ Maintain session cookies
         ↓
    [STEP 3] Parse HTML
         ├─ Extract 10 basic fields via regex
         ├─ Extract superintendent from HTML comments (3-tier fallback)
         └─ Validate completeness
         ↓
    [Cache Result] Store for TTL duration
         ↓
    Return JSON (2.5-4.5s total)
```

## Configuration

The service uses environment-based configuration:

**Environment Selection:**
- `FLASK_ENV=development` → DevelopmentConfig
- `FLASK_ENV=production` → ProductionConfig
- `FLASK_ENV=testing` → TestingConfig

**Key Environment Variables:**
```bash
FLASK_ENV=production
DEBUG=False
HOST=0.0.0.0
PORT=5000

# Cache settings
CACHE_ENABLED=True
CACHE_TTL=7200              # 2 hours for production
CACHE_MAX_SIZE=1000

# Request settings
REQUEST_TIMEOUT=15
MAX_RETRIES=2
```

**Configuration Differences:**
- Development: Cache TTL 300s, DEBUG=True
- Production: Cache TTL 7200s, DEBUG=False, rate limiting enabled
- Testing: Cache disabled, rate limiting disabled

## Common Development Tasks

### Adding New Verification Fields

1. Identify the field in PPB portal HTML response
2. Add regex pattern to `parse_detailed_html()` in `src/services/ppb_service.py`
3. Update test expectations in `tests/test_direct.py` and `tests/test_verification.py`
4. Test extraction with real PPB numbers
5. Update README.md documentation

### Modifying Rate Limiting

1. Edit `RateLimiter.delay` in `src/services/ppb_service.py` (default: 1.5s)
2. Or set via config: `src/core/config.py`
3. Test with multiple sequential requests
4. Monitor for timeouts (indicates IP blocking)

### Debugging Verification Failures

**Missing superintendent data:**
```bash
python tests/test_superintendent_fix.py  # Should show 4/4 passing
```

**Slow response times:**
- Check cache hit rate: `curl http://localhost:5000/cache/stats`
- Expected: >60% hit rate in production
- Enable caching if disabled

**"Facility not found" errors:**
- Verify PPB number format (e.g., "PPB/C/9222")
- Check PPB portal availability
- Review search response in logs

### Performance Targets

- Uncached verification: 2.5-4.5 seconds
- Cached verification: < 100ms
- Cache hit rate: > 60%
- Success rate: > 95% for valid PPB numbers
- Data completeness: 100% (13/13 fields)

## Important Notes

### Critical Files - Handle with Care

**src/services/ppb_service.py** (Superintendent extraction)
- Contains three-tier fallback logic for extracting superintendent from HTML comments
- Must pass `tests/test_superintendent_fix.py` after any changes
- Regex patterns are fragile - test thoroughly
- PPB portal validates HTTP headers strictly - changing headers can break Step 2

**src/core/config.py** (Configuration)
- Environment-based config (development, production, testing)
- Controls caching, rate limiting, logging format
- Modify carefully - affects all services

### Testing Requirements

Before any commit:
1. Run `python tests/test_superintendent_fix.py` → Must pass 4/4
2. Run `python tests/test_direct.py` → Must extract all 13 fields
3. Test with at least 3 different PPB numbers
4. Verify cache functionality

### Known Limitations

- PPB portal may change HTML structure (monitor for extraction failures)
- Rate limiting at 1.5s prevents high-throughput scenarios
- No authentication on API endpoints (add in production)
- Single-threaded Flask development server (use Gunicorn in production)

### Error Handling

The service returns structured JSON for all errors:

**404 - Not Found**: PPB number doesn't exist in registry
**400 - Bad Request**: Invalid request format or missing ppb_number
**500 - Internal Server Error**: Unexpected errors (connection failures, parsing errors)

All responses include `processing_time_ms` for performance monitoring.
