# local-slm-playwriting

Local SLM-based multi-agent system for generating theatre plays.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) for character generation

## Run

From the `backend/` directory:

```sh
uv sync
uv run fastapi dev src/anton/main.py
```

The API is served at `http://127.0.0.1:8000/api`, interactive docs at `http://127.0.0.1:8000/docs`.

## Project structure

- `backend/src/anton/`: Python package and application entry point.
  - `api/`: HTTP layer (routers, DTOs, mappers, exception handlers).
  - `application/`: Business logic services.
  - `domain/`: Domain models, independent of FastAPI and Ollama.
  - `infrastructure/`: External integrations (config, SLM clients, prompts).
- `backend/tests/`: Unit and integration tests.
- `frontend/`: React frontend.

## Status

Backend skeleton: FastAPI app with stubbed character endpoints.
