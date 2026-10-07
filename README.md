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

## Configuration

Settings are read from `ANTON_*` environment variables or from `backend/.env` (not committed):

| Variable | Default | Meaning |
|---|---|---|
| `ANTON_OLLAMA_MODEL` | `qwen3:4b` | Ollama model |
| `ANTON_OLLAMA_NUM_CTX` | `16384` | context window in tokens |
| `ANTON_THINKING` | `true` | `false` switches model thinking off for every request (faster, for testing) |

```sh
ANTON_THINKING=false uv run fastapi dev src/anton/main.py
```

## Tests

From the `backend/` directory:

```sh
uv run python -m unittest discover -s tests/unit -t .         # fast, no model needed
uv run python -m unittest discover -s tests/integration -t .  # needs Ollama; thinking is always off
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

Backend skeleton: FastAPI app with stubbed character endpoints.
