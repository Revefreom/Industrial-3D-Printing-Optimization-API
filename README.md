#  Industrial 3D Printing Resource & Cost Optimization Engine

This project is a high-performance **FastAPI-based microservice** designed to calculate and optimize production costs for industrial 3D printing (Additive Manufacturing). It bridges the gap between **mathematical modeling** and **industrial production readiness**.

## The Mathematical Model

As a Mathematics MSc student, I developed this engine to move beyond simple arithmetic. The core of the system is based on a dynamic cost function:

$$C_{total} = \sum_{i=1}^{n} (M_i \cdot P_i) + E_{usage} + \frac{D_{machine}}{L_{life}} + \text{Risk}(\alpha)$$

Where:
- **$M_i \cdot P_i$**: Material mass and unit price.
- **$E_{usage}$**: Energy consumption based on print duration.
- **$\text{Risk}(\alpha)$**: A stochastic risk factor representing the learning curve and potential print failures.

## Tech Stack & Architecture

- **Backend:** Python 3.11 with **FastAPI** (Asynchronous API).
- **Architecture:** Modular design with separation of concerns (`logic.py` for calculations, `schemas.py` for data validation).
- **Deployment:** Fully **Dockerized** for seamless industrial integration (Edge or Cloud).
- **Data Integrity:** Pydantic for strict type checking and validation.

## How to Run (Docker)

To run this engine in any industrial environment, simply use:

```bash
docker build -t industrial-opt-engine .
docker run -p 8000:8000 industrial-opt-engine