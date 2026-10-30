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

All endpoints are under `/api`. Steps that are not possible yet (for example writing the text before every scene is approved) are rejected with `409` and a `message` that says what to do first. Long generations stop when the client cancels the request.

### Characters

| Method | Path | Body | Answer |
|---|---|---|---|
| `POST` | `/characters/generate` | `{premise}` | the cast; also starts a new Story Bible from the premise |
| `GET` | `/characters` | | the cast with cards and the characters' histories |
| `POST` | `/characters` | character profile | the new character with its card |
| `PUT` | `/characters/{id}` | character profile | the edited character; its history is kept |
| `POST` | `/characters/{id}/revise` | `{message, character}` | `{reply, character}`; nothing is saved |
| `GET` | `/characters/{id}/revise` | | chat history |

### Story Bible: outline and acts

| Method | Path | Body | Answer |
|---|---|---|---|
| `GET` | `/story` | | the Story Bible with its warning flags |
| `POST` | `/story/outline/generate` | | the Story Bible with the outline; again only until the acts exist |
| `PUT` | `/story/outline` | outline | the Story Bible |
| `POST` | `/story/outline/revise` | `{message, outline}` | `{reply, outline}`; nothing is saved |
| `GET` | `/story/outline/revise` | | chat history |
| `POST` | `/story/acts/generate` | | the Story Bible with the acts; not after they are approved |
| `PUT` | `/story/acts/{n}` | `{summary, dramatic_function}` | the Story Bible |
| `POST` | `/story/acts/revise` | `{message, acts}` | `{reply, acts}`; nothing is saved |
| `GET` | `/story/acts/revise` | | chat history |
| `POST` | `/story/acts/approve` | | the Story Bible |

### Story Bible: one act page

An act can be built once the acts are approved and the text of the act before it is approved. Once its text is approved, the act is final: its scenes can no longer be planned, changed, approved or reopened.

| Method | Path | Body | Answer |
|---|---|---|---|
| `GET` / `POST` | `/story/places` | place (for `POST`) | all places / the new place |
| `POST` | `/story/acts/{n}/structure/generate` | | the Story Bible with the proposed scenes and new places |
| `PUT` | `/story/acts/{n}/scenes` | scenes in their new order | the Story Bible; only while the structure is a draft |
| `POST` | `/story/acts/{n}/structure/revise` | `{message, scenes}` | `{reply, scenes, places}`; only new places are saved |
| `POST` | `/story/acts/{n}/structure/approve` | | the Story Bible |
| `POST` | `/story/acts/{n}/scenes/{no}/plan` | | the Story Bible; scene `no - 1` must be approved |
| `PUT` | `/story/acts/{n}/scenes/{no}` | scene plan | the Story Bible; the scene becomes a draft again |
| `POST` | `/story/acts/{n}/scenes/revise` | `{message, scenes}` | `{reply, scenes, places}`; only new places are saved |
| `POST` | `/story/acts/{n}/scenes/{no}/approve` | | the Story Bible; the last one approves the act's scenes |
| `POST` | `/story/acts/{n}/scenes/{no}/reopen` | | the Story Bible |
| `POST` | `/story/acts/{n}/text/generate` | | the Story Bible with the text, written scene by scene; starts the act page's chat anew |
| `PUT` | `/story/acts/{n}/text` | scene texts | the Story Bible |
| `POST` | `/story/acts/{n}/text/revise` | `{message, scene_texts}` | `{reply, scene_texts}`; nothing is saved |
| `POST` | `/story/acts/{n}/text/approve` | | the Story Bible; appends the act's changes to the characters' histories |
| `GET` | `/story/acts/{n}/chat` | | chat history of the act page |

### Warning flags

The Story Bible says when something was changed after later steps were built from it; nothing is rewritten automatically:

- `outline_changed`: the outline differs from the one the acts were built from;
- `summary_changed` (per act): the act summary differs from the one its scenes were built from;
- `outdated_plans` (per act): scenes whose plan was written before an earlier scene changed;
- `scenes_changed` (per act): the scenes differ from the ones the text was written from.

### Chats

Every page has its own agent built from one LangGraph graph (`application/agents/chat_edit_agent.py`): the agent proposes a change, applies it once the user agrees and returns the changed data, which the frontend puts into its fields and saves. The agent answers in the language of the user's messages and keeps the edited text in its own language. A short "yes" to a proposal applies it; when an edit changes nothing, the agent says so instead of claiming it was applied. The text agent changes single lines, so the rest of a scene always stays as it is. The chats are saved to `backend/data/chats/` and survive a restart of the backend.

### Generation

Every generation is written in the language of the user's idea, which the backend names in the input of each prompt. A small model often ignores parts of its prompt, so the backend checks the answers that matter most and asks once more when they fail: an act structure has two to eight scenes with at least two characters each; a scene plan must be several sentences, must not copy its instructions or examples and must not repeat an earlier scene; a scene text must be at least 20 lines in which only the characters on stage speak, no line repeats an earlier one and no character retells the plan. Acts are put in the order of their dramatic functions, and lines that still repeat are dropped from the text.

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
