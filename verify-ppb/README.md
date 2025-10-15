# PPB Verification Microservices

Monorepo for Kenya Pharmacy and Poisons Board (PPB) verification microservices.

## Services

### 🏥 Facilities (Production Ready)
**Status:** ✅ v1.0.0 Production

Verifies PPB facility licenses (pharmacies, hospitals, wholesalers, manufacturers).

- **Location:** `facilities/`
- **Docs:** [facilities/README.md](facilities/README.md)
- **Run:** `cd facilities && python -m src.app`

### 👨‍⚕️ Pharmacists (Planned)
**Status:** 🚧 Coming Soon

Will verify individual pharmacist licenses.

- **Location:** `pharmacists/` (to be created)

### 💊 Pharmaceutical Technologists (Planned)
**Status:** 🚧 Coming Soon

Will verify pharmaceutical technologist licenses.

- **Location:** `pharmtechs/` (to be created)

## Quick Start

```bash
# Navigate to a service
cd facilities

# Run the service
python -m src.app

# Or use Docker
docker-compose up -d
```

## Repository Structure

```
verify-ppb/                    # Monorepo root
├── facilities/                # ✅ Facility verification service
│   ├── src/                   # Application code
│   │   ├── core/              # Config, logging, version
│   │   ├── api/               # Flask routes & errors
│   │   ├── services/          # Business logic
│   │   ├── adapters/          # HTTP, caching
│   │   └── models/            # Schemas
│   ├── requirements.txt       # Dependencies
│   ├── Dockerfile            # Container config
│   └── README.md             # Service documentation
├── pharmacists/              # 🚧 (Future)
└── pharmtechs/               # 🚧 (Future)
```

## Why Monorepo?

✅ **Shared tooling** - Common CI/CD, linting, formatting  
✅ **Consistent structure** - All services follow the same pattern  
✅ **Easy navigation** - One repository for all PPB services  
✅ **Independent deployment** - Each service is self-contained  

## Development Guidelines

Each microservice follows this structure:

```
service-name/
├── src/                       # Main application package
│   ├── core/                  # Configuration & utilities
│   ├── api/                   # API endpoints
│   ├── services/              # Business logic
│   ├── adapters/              # External integrations
│   └── models/                # Data models
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── Dockerfile                # Container configuration
├── docker-compose.yml        # Local development
├── pytest.ini                # Test configuration
└── README.md                 # Service documentation
```

**Running a service:**
```bash
cd <service-name>
python -m src.app              # Run as module (recommended)
```

## Contributing

See [facilities/README.md](facilities/README.md) for detailed contribution guidelines.

## License

MIT License

---

**Current Version:** v1.0.0 (facilities only)

