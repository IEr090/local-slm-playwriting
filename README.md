# local-slm-playwriting

Local SLM-based multi-agent system for generating theatre plays.

## Requirements

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/) for every generation (characters and the Story Bible)

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

The integration tests generate a cast and then the whole first act (outline, acts, scenes, text and character histories), so they take several minutes. Run one of them with, for example, `uv run python -m unittest tests.integration.test_story_generation`.

## API

Full API documentation: http://localhost:8000/docs

## Project structure

- `backend/src/anton/`: Python package and application entry point.
  - `api/`: HTTP layer (routers, DTOs, mappers, exception handlers).
  - `application/`: Business logic services.
  - `domain/`: Domain models, independent of FastAPI and Ollama.
  - `infrastructure/`: External integrations (config, SLM clients, prompts, storage).
- `backend/tests/`: Unit and integration tests.
- `frontend/`: React frontend.

## Storage

The cast is saved to `backend/data/cast.json` after every generation, creation and edit, so it survives a backend restart. A new generation replaces the saved cast and starts a new Story Bible. The Story Bible (outline, acts with scenes and text, places) is saved to `backend/data/story_bible.json`; the characters' histories are part of `cast.json`; the chats are saved to `backend/data/chats/`. Set `ANTON_DATA_DIR` to store the data in another folder.

## Status

Backend: characters and the Story Bible from the outline to the approved text of every act with the characters' histories. A critic that checks the whole play is not built yet.
