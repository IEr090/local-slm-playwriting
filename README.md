# local-slm-playwriting

Local SLM-based multi-agent system for generating theatre plays.

## Requirements

Python 3.11 or newer.

## Run

From the repository root:

```sh
python3 backend/src/anton/main.py
```

Expected output:

```text
Anton initialized.
```

## Project structure

- `backend/src/anton/`: Python package and application entry point.
  - `api/`: HTTP layer (routers, DTOs, mappers, exception handlers).
  - `application/`: Business logic services.
  - `domain/`: Domain models, independent of FastAPI and Ollama.
  - `infrastructure/`: External integrations (config, SLM clients, prompts).
- `backend/tests/`: Unit and integration tests.
- `frontend/`: React frontend.

## Status

Minimal project setup. No external dependencies are required.
