# Industrial 3D Printing Resource & Cost Optimization Engine

This project is a high-performance **FastAPI-based microservice** designed to calculate and optimize production costs for industrial 3D printing (Additive Manufacturing). It bridges the gap between **mathematical modeling** and **industrial production readiness**.

## The Mathematical Model

As a Mathematics MSc student, I developed this engine to move beyond simple arithmetic. The core of the system is based on a dynamic cost function:

$$C_{total} = \sum_{i=1}^{n} (M_i \cdot P_i) + E_{usage} + \frac{D_{machine}}{L_{life}} + \text{Risk}(\alpha)$$

Where:
- **$M_i \cdot P_i$**: Material mass and unit price.
- **$E_{usage}$**: Energy consumption based on print duration.
- **$\text{Risk}(\alpha)$**: A stochastic risk factor representing the learning curve and potential print failures.

## Tech Stack & Architecture

- **Backend:** Python 3.11 with **FastAPI** (Asynchronous API)
- **Architecture:** Modular design with separation of concerns (`logic.py` for calculations, `schemas.py` for data validation)
- **Database:** SQLite with context manager pattern for safe transactions
- **Export:** PDF and Word invoice generation with ReportLab and python-docx
- **Deployment:** Fully **Dockerized** with healthcheck and non-root user
- **Data Integrity:** Pydantic for strict type checking and validation
- **Logging:** Centralized logging with configurable log levels

## Features

- ✅ Material, energy, and depreciation cost calculation
- ✅ Printer component lifetime tracking (nozzle, heater, motor)
- ✅ Customer and invoice management
- ✅ PDF/Word invoice export
- ✅ RESTful API with Swagger documentation
- ✅ Docker compatible (headless)

## Quick Start

### Local Development

```bash
# Clone and setup
cd 3D-printer-cost
pip install -r requirements.txt

# Run the server
python main.py

# Or with uvicorn
uvicorn main:app --reload
```

### Docker

```bash
docker build -t industrial-opt-engine .
docker run -p 8000:8000 industrial-opt-engine
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_FILE` | `printer_cost.db` | Database file path |
| `SETTINGS_FILE` | `settings.json` | Settings file path |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DEBUG` | `false` | Debug mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/calculate-cost` | Calculate printing cost |
| GET/POST/PUT/DELETE | `/printers/{id}` | Printer CRUD operations |
| GET/POST/PUT/DELETE | `/customers/{id}` | Customer CRUD operations |
| GET/POST | `/materials` | Material management |
| GET/POST | `/invoices` | Invoice operations |
| GET | `/invoices/{id}/export/pdf` | Export invoice as PDF |
| GET | `/invoices/{id}/export/word` | Export invoice as Word |
| GET | `/health` | Health check |

## Running Tests

```bash
# Install test dependencies
pip install pytest httpx

# Run tests
pytest test_api.py -v
```

## Project Structure

```
3D-printer-cost/
├── main.py           # FastAPI application and endpoints
├── logic.py          # Cost calculation business logic
├── database.py       # SQLite database operations
├── schemas.py        # Pydantic models for validation
├── export.py         # PDF/Word export functionality
├── config.py         # Configuration and logging
├── settings.json     # Application settings
├── test_api.py       # API tests
├── Dockerfile        # Docker configuration
├── requirements.txt  # Python dependencies
└── README.md         # Documentation
```

## License

This project is for educational and industrial use.