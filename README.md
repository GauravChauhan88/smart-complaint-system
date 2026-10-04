# Smart Customer Complaint Triage & Routing System

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red?logo=pytorch)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-19-cyan?logo=react)
![TailwindCSS](https://img.shields.io/badge/Tailwind-CSS-38B2AC?logo=tailwind-css)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?logo=nginx)
![Build](https://img.shields.io/badge/Tests-5%2F5%20Passing-brightgreen)

An enterprise-ready, containerized complaint management system featuring a **Multi-Task Deep Learning NLP Pipeline** coupled with **Deterministic Safety Guardrails**, designed to automate customer support triage, severity escalation, entity extraction, and status resolution in real time.

---

## Architecture Overview

The system follows a multi-tier decoupled microservice architecture:
```
[ Client Browser ]
│
▼ (Port 3000)
┌────────────────────────────────────────────────────────┐
│ public-facing-tier (Docker Bridge)                     │
│                                                        │
│  [ complaint_react_ui ]                                │
│    ├── Nginx Reverse Proxy (Port 80)                   │
│    └── React 19 Production SPA Assets                  │
└───────────────────────────┬────────────────────────────┘
│ /api/* proxy_pass
▼ (Port 8000)
┌────────────────────────────────────────────────────────┐
│ internal-secure-tier (Air-Gapped Bridge, internal: true)│
│                                                        │
│  [ complaint_ai_backend ]                              │
│    ├── FastAPI REST Engine                             │
│    ├── Multi-Task DistilBERT Model (PyTorch)           │
│    ├── Hybrid Guardrail & Regex Entity Parser          │
│    └── SQLite / SQLAlchemy Engine (Auto-Seeded)        │
└────────────────────────────────────────────────────────┘
```

---

## Academic & Engineering Alignment

| Subject Domain | Implementation Details | Project Location |
| :--- | :--- | :--- |
| **Machine Learning using Python** | Fine-tuned `distilbert-base-uncased` with dual task heads (`Category` & `Urgency`), AdamW optimizer, and joint Cross-Entropy loss | `ml-pipeline/train_multitask.py`<br>`ml-pipeline/saved_model/` |
| **Advanced Web Technologies** | React 19 SPA with Tailwind CSS, custom inline SVG icons, Axios HTTP state handling, and FastAPI async REST API with SQLAlchemy ORM | `frontend/src/App.jsx`<br>`backend/main.py` |
| **Cloud Infrastructure & Services** | Multi-stage Docker builds (Alpine Linux, Node 20 builder, Nginx runtime) and automated orchestration via Docker Compose | `backend/Dockerfile`<br>`frontend/Dockerfile`<br>`docker-compose.yml` |
| **Connecting Networks** | Multi-tier network segmentation (`public-facing-tier` vs. `internal-secure-tier`), container port binding, and Nginx reverse proxy routing | `docker-compose.yml`<br>`frontend/nginx.conf` |
| **Software Testing & Reliability** | Pytest unit and integration test suite (100% pass) and multi-threaded concurrent load benchmarking | `test_suite.py`<br>`load_test.py` |

---

## Key Features

1. **Multi-Task Transformer Inference:** A single forward pass predicts both the functional category and urgency level, reducing computational overhead compared to running separate models.
2. **Hybrid Triage Guardrails:** Uses regex boundary assertions (`\b`) to detect critical triggers (e.g., fraud, attorney, unauthorized charges) and force escalation to `Critical` severity, preventing compliance failures.
3. **Automated Entity Extraction:** Identifies transaction reference IDs (`Ref#TXN-9901`) and financial amounts (`$1,240.00`) directly from raw text.
4. **Resilient Auto-Seeding:** Automatically seeds realistic demo complaints on container startup if the database is unpopulated.
5. **Interactive Dashboard:** Live KPI metrics, urgency color badges, manual review flags, and one-click ticket resolution.

---

## Reliability & Performance Benchmarks

* **Automated Test Suite:** 5/5 passed (100% test coverage for triage logic, entity parsing, health checks, and ticket lifecycle).
* **Load Test Results (Concurrent Stress Test):**
  * Concurrency: 4 workers
  * Requests: 40 requests
  * Success Rate: **100.0%**
  * Average Latency: **266.39 ms**
  * 95th Percentile Latency: **2400.12 ms**
  * Throughput: **~15.01 req/sec** (CPU-only execution)

---

## Quick Start (Docker Deployment)

### Prerequisites
* Docker Desktop installed and running.
* Git and Git LFS.

### 1. Clone the Repository
```bash
git clone [https://github.com/GauravChauhan88/smart-complaint-system.git](https://github.com/GauravChauhan88/smart-complaint-system.git)
cd smart-complaint-system
git lfs pull
```
### 2. Launch with Docker Compose
```Bash
docker compose up --build -d
```
### 3. Access Services
* Frontend Portal: http://localhost:3000

* Backend API Docs (Swagger UI): http://localhost:8000/docs

* Health Endpoint: http://localhost:8000/api/health

### Running Verification Tests Locally
Activate your virtual environment and execute the test suites:

```Bash
# Run Unit & Integration Tests
pytest test_suite.py -v

# Run Concurrent Load Benchmark
python load_test.py
```
"@)


---

### Step 2: Commit and Push the README to GitHub

Run:

```powershell
git add README.md
git commit -m "docs: add comprehensive architecture, benchmark, and setup guide"
git push origin main



