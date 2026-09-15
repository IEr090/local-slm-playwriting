# local-slm-playwriting — Technology Stack


| Layer | Technology | Purpose |
|---|---|---|
| Core language | Python | AI logic, agents, workflow and backend |
| Data models | Pydantic | Structured models such as Character, Scene and StoryBible; validation of agent outputs |
| Agent workflow | LangGraph | Agent sequence, branching, shared workflow state and revision loops |
| Local SLM runtime | Ollama | Single local model backend; model switching and generation settings |
| Persistence | JSON | Project and Story Bible saving |
| Backend API | FastAPI | Interface between the frontend and Python AI logic |
| Frontend | React + TypeScript | Main application interface |
| Frontend build | Vite | Development server and frontend build tooling |
| Styling | Tailwind CSS | Flexible styling for a polished interface |
| UI components | shadcn/ui | Reusable modern interface components |
| Animations | Motion for React | Transitions, animated cards, panels and workflow feedback |
| Desktop packaging | Tauri | Optional final packaging as a native-like desktop application |
| Repository | GitHub | Source code, documentation and architecture diagrams |
| Python dependency management | uv + pyproject.toml + uv.lock | Dependency management and reproducible Python environment |